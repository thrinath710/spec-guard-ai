import io
import zipfile

import pytest
from fastapi import UploadFile

from backend.app.services.document_processor import (
    DocumentProcessor,
    DocumentValidationError,
    detect_file_type,
)


def _upload(name: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(data))


def test_detects_formats_from_bytes():
    assert detect_file_type(b"%PDF-1.7\n...") == "pdf"
    assert detect_file_type(b"PK\x03\x04rest-of-archive") == "docx"
    assert detect_file_type(b"Users can upload files.") == "text"
    # Executable-style binary content must not pass as text.
    assert detect_file_type(b"\x7fELF\x02\x01\x00\x00" + b"\x00" * 64) is None


@pytest.mark.asyncio
async def test_rejects_binary_renamed_as_txt():
    processor = DocumentProcessor()
    with pytest.raises(DocumentValidationError) as excinfo:
        await processor.save_upload(_upload("payload.txt", b"\x00\x01\x02\x03" * 64))
    assert excinfo.value.code == "INVALID_DOCUMENT"


@pytest.mark.asyncio
async def test_rejects_pdf_that_is_actually_text():
    """The previous behaviour was an opaque parser crash rather than a usable message."""
    processor = DocumentProcessor()
    with pytest.raises(DocumentValidationError) as excinfo:
        await processor.save_upload(_upload("spec.pdf", b"This is plainly not a PDF."))
    assert excinfo.value.code == "FILE_TYPE_MISMATCH"


@pytest.mark.asyncio
async def test_rejects_zip_that_is_not_a_word_document():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("notes.txt", "not a word document")
    processor = DocumentProcessor()
    with pytest.raises(DocumentValidationError) as excinfo:
        await processor.save_upload(_upload("spec.docx", buffer.getvalue()))
    assert excinfo.value.code == "FILE_TYPE_MISMATCH"


@pytest.mark.asyncio
async def test_rejects_corrupt_pdf_with_clear_message():
    processor = DocumentProcessor()
    with pytest.raises(DocumentValidationError) as excinfo:
        await processor.save_upload(_upload("broken.pdf", b"%PDF-1.7\nnot really a pdf body"))
    assert excinfo.value.code in {"CORRUPT_DOCUMENT", "NO_TEXT_FOUND"}


@pytest.mark.asyncio
async def test_accepts_valid_text_document(tmp_path):
    processor = DocumentProcessor()
    document = await processor.save_upload(
        _upload("spec.txt", b"Users can cancel an order at any time.")
    )
    assert document.file_type == "txt"
    assert "cancel an order" in document.extracted_text
    from pathlib import Path

    Path(document.storage_path).unlink(missing_ok=True)
