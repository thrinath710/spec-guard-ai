import logging
import re
import zipfile
from pathlib import Path

from docx import Document as DocxDocument
from fastapi import UploadFile
from pypdf import PdfReader

from backend.app.core.config import Settings, get_settings
from backend.app.models import DocumentRecord

logger = logging.getLogger(__name__)

SUPPORTED_TYPES = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".md": "md",
    ".markdown": "md",
}

# Detected from the file's own bytes rather than its extension. python-magic would need the
# native libmagic library installed on every host; these four formats have unambiguous
# signatures, so checking them directly keeps the app dependency-free and portable.
PDF_SIGNATURE = b"%PDF-"
ZIP_SIGNATURE = b"PK\x03\x04"


class DocumentValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def detect_file_type(content: bytes) -> str | None:
    """Best-effort content sniffing. Returns 'pdf', 'docx', 'text', or None if unrecognised."""
    if content.startswith(PDF_SIGNATURE):
        return "pdf"
    if content.startswith(ZIP_SIGNATURE):
        # DOCX is a ZIP container; distinguish it from any other archive by its parts.
        return "docx"
    # Null bytes are the clearest signal of an binary file masquerading as text.
    sample = content[:4096]
    if b"\x00" in sample:
        return None
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        # A multi-byte character split by the sample boundary is not a failure.
        try:
            sample.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            if not _mostly_printable(sample):
                return None
    return "text"


def _mostly_printable(sample: bytes) -> bool:
    if not sample:
        return False
    printable = sum(1 for byte in sample if 9 <= byte <= 13 or 32 <= byte <= 126 or byte >= 128)
    return printable / len(sample) > 0.85


class DocumentProcessor:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def save_upload(self, upload: UploadFile) -> DocumentRecord:
        filename = Path(upload.filename or "").name
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_TYPES:
            raise DocumentValidationError(
                "UNSUPPORTED_FILE_TYPE",
                "Supported document formats are PDF, DOCX, TXT, and Markdown.",
            )

        content = await upload.read()
        if not content:
            raise DocumentValidationError("INVALID_DOCUMENT", "The uploaded document is empty.")
        if len(content) > self.settings.max_upload_bytes:
            raise DocumentValidationError(
                "FILE_TOO_LARGE",
                f"Uploaded documents must be {self.settings.max_upload_mb} MB or smaller.",
            )

        declared = SUPPORTED_TYPES[suffix]
        self._verify_content_matches_extension(content, declared, suffix)

        document = DocumentRecord(
            filename=filename,
            file_type=declared,
            file_size=len(content),
            storage_path="",
        )
        storage_path = self.settings.uploads_dir / f"{document.id}{suffix}"
        storage_path.write_bytes(content)
        document.storage_path = str(storage_path)

        try:
            document.extracted_text = self.extract_text(storage_path, document.file_type)
        except DocumentValidationError:
            storage_path.unlink(missing_ok=True)
            raise
        except Exception as exc:  # noqa: BLE001
            # A malformed but correctly-signed file only fails once parsing starts.
            storage_path.unlink(missing_ok=True)
            logger.warning("Failed to parse %s: %s", filename, exc)
            raise DocumentValidationError(
                "CORRUPT_DOCUMENT",
                f"This {declared.upper()} file could not be read. It may be corrupted or password protected.",
            ) from exc

        if not document.extracted_text.strip():
            storage_path.unlink(missing_ok=True)
            hint = (
                " Scanned or image-only PDFs are not supported because they contain no selectable text."
                if declared == "pdf"
                else ""
            )
            raise DocumentValidationError(
                "NO_TEXT_FOUND",
                f"No readable text could be extracted from this document.{hint}",
            )
        return document

    def _verify_content_matches_extension(self, content: bytes, declared: str, suffix: str) -> None:
        """Reject files whose bytes disagree with their extension.

        Without this a renamed binary reaches the parser and surfaces as an opaque crash
        rather than a clear message.
        """
        detected = detect_file_type(content)
        if detected is None:
            raise DocumentValidationError(
                "INVALID_DOCUMENT",
                f"This file does not look like a readable {declared.upper()} document.",
            )

        expected = {"pdf": "pdf", "docx": "docx", "txt": "text", "md": "text"}[declared]
        if detected != expected:
            raise DocumentValidationError(
                "FILE_TYPE_MISMATCH",
                f"The file is named '{suffix}' but its contents are "
                f"{'a PDF' if detected == 'pdf' else 'a ZIP/DOCX archive' if detected == 'docx' else 'plain text'}. "
                "Rename it to the correct extension and try again.",
            )

        if declared == "docx" and not self._is_docx_archive(content):
            raise DocumentValidationError(
                "FILE_TYPE_MISMATCH",
                "This ZIP archive is not a Word document.",
            )

    @staticmethod
    def _is_docx_archive(content: bytes) -> bool:
        import io

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                return "word/document.xml" in archive.namelist()
        except zipfile.BadZipFile:
            return False

    def extract_text(self, path: Path, file_type: str) -> str:
        if file_type in {"txt", "md"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if file_type == "pdf":
            return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        if file_type == "docx":
            document = DocxDocument(str(path))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
        return ""

    def chunk_text(self, text: str, max_chars: int = 1200) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 2 <= max_chars:
                current = f"{current}\n\n{paragraph}".strip()
            else:
                if current:
                    chunks.append(current)
                current = paragraph
        if current:
            chunks.append(current)
        return chunks
