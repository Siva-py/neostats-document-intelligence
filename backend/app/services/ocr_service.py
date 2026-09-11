import os

import requests
from dotenv import load_dotenv


load_dotenv()


OCR_API_URL = "https://api.ocr.space/parse/image"


def extract_text_with_ocr(file_path: str) -> dict:

    api_key = os.getenv("OCR_SPACE_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OCR_SPACE_API_KEY is not configured."
        )

    data = {
        "language": "eng",
        "OCREngine": "3",
        "isTable": "true",
        "isOverlayRequired": "false",
    }

    with open(file_path, "rb") as file:

        response = requests.post(
            OCR_API_URL,
            headers={
                "apikey": api_key
            },
            data=data,
            files={
                "file": file
            },
            timeout=120,
        )

    response.raise_for_status()

    result = response.json()

    if result.get("IsErroredOnProcessing"):

        error_message = (
            result.get("ErrorMessage")
            or "OCR processing failed."
        )

        raise RuntimeError(error_message)

    parsed_results = (
        result.get("ParsedResults")
        or []
    )

    if not parsed_results:
        raise RuntimeError(
            "OCR returned no parsed results."
        )

    page_results = []

    text_parts = []

    for page_number, item in enumerate(
        parsed_results,
        start=1,
    ):

        page_text = (
            item.get("ParsedText")
            or ""
        ).strip()

        if page_text:

            page_results.append(
                {
                    "page_number": page_number,
                    "text": page_text,
                }
            )

            text_parts.append(
                f"--- PAGE {page_number} ---\n"
                f"{page_text}"
            )

    extracted_text = (
        "\n\n".join(text_parts)
    ).strip()

    if not extracted_text:
        raise RuntimeError(
            "OCR returned empty text."
        )

    return {
        "text": extracted_text,
        "pages": page_results,
        "page_count": len(page_results),
        "engine": "ocr_space_engine_3",
        "processing_time_ms": (
            result.get(
                "ProcessingTimeInMilliseconds"
            )
        ),
    }