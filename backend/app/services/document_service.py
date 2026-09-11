from pathlib import Path
from tempfile import NamedTemporaryFile
from app.repositories.document_repository import DocumentRepository
from app.services.document_validation_service import validate_document
from app.services.ocr_service import extract_text_with_ocr
from app.services.extraction_service import ExtractionService
from app.services.financial_validation_service import (
    validate_document as validate_financial_document,
)
from app.core.logging import get_logger
logger = get_logger(__name__)


ALLOWED_DOCUMENT_TYPES = {
    "invoice",
    "balance_sheet",
    "profit_and_loss",
    "cash_flow_statement",
}

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
}
MAX_FILE_SIZE = 1 * 1024 * 1024


class DocumentService:
    def __init__(self):
        self.repository = DocumentRepository()

    def process_document(
        self,
        file_content: bytes,
        filename: str,
        document_type: str,
    ) -> dict:

        logger.info(
        "Document processing started: %s (%s)",
        filename,
        document_type,
        )
        if document_type not in ALLOWED_DOCUMENT_TYPES:
            raise ValueError(
                "Unsupported document type."
            )

        extension = Path(filename).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(
                "Unsupported file type."
            )

        if not file_content:
            raise ValueError(
                "Uploaded file is empty."
            )
        if len(file_content) > MAX_FILE_SIZE:
            raise ValueError(
                "Uploaded file exceeds the maximum allowed size of 1 MB."
            )

        temporary_path = None

        try:
            with NamedTemporaryFile(
                delete=False,
                suffix=extension,
            ) as temporary_file:

                temporary_file.write(file_content)
                temporary_path = temporary_file.name

            # 1. File validation
            file_validation = validate_document(
                temporary_path
            )
            logger.info(
            "Document validation passed: %s",
            filename,
            )

            if file_validation["status"] != "PASS":
                return {
                    "document_name": filename,
                    "document_type": document_type,
                    "status": "FAILED",
                    "file_validation": file_validation,
                }

            # 2. OCR
            ocr_result = extract_text_with_ocr(
                temporary_path
            )
            logger.info(
            "OCR completed successfully: %s",
            filename,
            )

            # 3. Gemini extraction
            logger.info(
            "AI extraction started: %s",
            filename,

            )
            extraction_service = ExtractionService()

            extraction_result = extraction_service.extract(
                ocr_text=ocr_result["text"],
                document_type=document_type,
                file_path=temporary_path,
            )
            logger.info(
                "AI extraction completed successfully: %s",
                filename,
            )

            # 4. Financial validation

            financial_validation = (
                validate_financial_document(
                    document_type=document_type,
                    extracted_data=extraction_result,
                )
            )
            
            status = financial_validation.get(
                "overall_status",
                financial_validation.get("status", "FAILED"),
            )
            logger.info(
                            "Financial validation completed: %s | status=%s",
                            filename,
                            status,
                        )
            
            result = {
                    "document_name": filename,
                    "document_type": document_type,
                    "status": status,
                    "file_validation": file_validation,
                    "extraction": extraction_result,
                    "financial_validation": financial_validation,
                    "metadata": {
                        "ocr_engine": ocr_result.get(
                            "engine"
                        ),
                        "ocr_page_count": ocr_result.get(
                            "page_count"
                        ),
                        "ocr_processing_time_ms": (
                            ocr_result.get(
                                "processing_time_ms"
                            )
                        ),
                    },
                }
            self.repository.save_document(
            document_name=filename,
            document_type=document_type,
            status=result["status"],
            result=result,
            )
            logger.info(
                "Document result persisted: %s | status=%s",
                filename,
                status,
            )
            return result

        finally:
            if temporary_path is not None:
                try:
                    Path(temporary_path).unlink(
                        missing_ok=True
                    )
                except Exception:
                    pass