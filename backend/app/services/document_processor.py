import re
from pathlib import Path

from docx import Document as DocxDocument
from fastapi import UploadFile
from pypdf import PdfReader

from backend.app.core.config import Settings, get_settings
from backend.app.models import DocumentRecord

SUPPORTED_TYPES = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".md": "md",
    ".markdown": "md",
}


class DocumentValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


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

        document = DocumentRecord(
            filename=filename,
            file_type=SUPPORTED_TYPES[suffix],
            file_size=len(content),
            storage_path="",
        )
        storage_path = self.settings.uploads_dir / f"{document.id}{suffix}"
        storage_path.write_bytes(content)
        document.storage_path = str(storage_path)
        document.extracted_text = self.extract_text(storage_path, document.file_type)
        if not document.extracted_text.strip():
            raise DocumentValidationError(
                "INVALID_DOCUMENT",
                "No readable text could be extracted from the document.",
            )
        return document

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
