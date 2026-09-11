from pathlib import Path

import pymupdf
from PIL import Image


ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_PAGES = 3


def validate_document(file_path: str) -> dict:
    """
    Validate a document before OCR / AI extraction.

    Checks:
    - File exists
    - File is not empty
    - File type is supported
    - File is readable / not corrupted
    - PDF page count does not exceed 3 pages
    """

    path = Path(file_path)

    # 1. File existence
    if not path.exists():
        return _failed("File does not exist.")

    # 2. Empty file
    if path.stat().st_size == 0:
        return _failed("File is empty.")

    # 3. Supported extension
    extension = path.suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return _failed(
            f"Unsupported file type: {extension or 'unknown'}."
        )

    # 4. PDF validation
    if extension == ".pdf":
        return _validate_pdf(path)

    # 5. Image validation
    return _validate_image(path)


def _validate_pdf(path: Path) -> dict:
    """Validate PDF readability and page limit."""

    try:
        document = pymupdf.open(path)

        page_count = len(document)

        if page_count == 0:
            document.close()
            return _failed("PDF contains no pages.")

        if page_count > MAX_PAGES:
            document.close()

            return {
                "file_type": "application/pdf",
                "is_supported": True,
                "is_readable": True,
                "page_count": page_count,
                "status": "FAILED",
                "error": (
                    f"Document exceeds the maximum allowed "
                    f"page limit of {MAX_PAGES} pages."
                ),
            }

        document.close()

        return {
            "file_type": "application/pdf",
            "is_supported": True,
            "is_readable": True,
            "page_count": page_count,
            "status": "PASS",
        }

    except Exception:
        return _failed("PDF is corrupted or unreadable.")


def _validate_image(path: Path) -> dict:
    """Validate JPG/PNG readability."""

    try:
        with Image.open(path) as image:
            image.verify()

        mime_type = _get_image_mime_type(path)

        return {
            "file_type": mime_type,
            "is_supported": True,
            "is_readable": True,
            "page_count": 1,
            "status": "PASS",
        }

    except Exception:
        return _failed("Image is corrupted or unreadable.")


def _get_image_mime_type(path: Path) -> str:
    """Return MIME type for supported image formats."""

    extension = path.suffix.lower()

    if extension in {".jpg", ".jpeg"}:
        return "image/jpeg"

    if extension == ".png":
        return "image/png"

    return "application/octet-stream"


def _failed(error_message: str) -> dict:
    """Create a consistent failed validation response."""

    return {
        "is_supported": False,
        "is_readable": False,
        "page_count": None,
        "status": "FAILED",
        "error": error_message,
    }