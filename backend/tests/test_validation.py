from pathlib import Path

import pymupdf

from app.services.document_validation_service import validate_document


def test_valid_pdf(tmp_path):
    file_path = tmp_path / "valid.pdf"

    document = pymupdf.open()
    document.new_page()
    document.save(file_path)
    document.close()

    result = validate_document(str(file_path))

    assert result["status"] == "PASS"
    assert result["is_supported"] is True
    assert result["is_readable"] is True
    assert result["page_count"] == 1


def test_corrupted_pdf(tmp_path):
    file_path = tmp_path / "corrupt.pdf"
    file_path.write_bytes(b"This is not a real PDF")

    result = validate_document(str(file_path))

    assert result["status"] == "FAILED"
    assert result["is_readable"] is False


def test_unsupported_file(tmp_path):
    file_path = tmp_path / "document.txt"
    file_path.write_text("test")

    result = validate_document(str(file_path))

    assert result["status"] == "FAILED"
    assert result["is_supported"] is False


def test_empty_file(tmp_path):
    file_path = tmp_path / "empty.pdf"
    file_path.write_bytes(b"")

    result = validate_document(str(file_path))

    assert result["status"] == "FAILED"


def test_pdf_over_three_pages(tmp_path):
    file_path = tmp_path / "large.pdf"

    document = pymupdf.open()

    for _ in range(4):
        document.new_page()

    document.save(file_path)
    document.close()

    result = validate_document(str(file_path))

    assert result["status"] == "FAILED"
    assert result["page_count"] == 4