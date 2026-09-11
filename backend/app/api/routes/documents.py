from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.document_service import DocumentService


router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Documents"],
)


service = DocumentService()


@router.post("/process")
async def process_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
):
    """
    Process an uploaded financial document.
    """

    filename = file.filename or ""

    try:
        file_content = await file.read()

        result = service.process_document(
            file_content=file_content,
            filename=filename,
            document_type=document_type,
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid document request.",
                "message": str(exc),
            },
        ) from exc

    except RuntimeError as exc:
        error_message = str(exc)

        if (
            "All configured Gemini API keys" in error_message
            or "503" in error_message
            or "UNAVAILABLE" in error_message
            or "Service Unavailable" in error_message
        ):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "AI processing unavailable.",
                    "message": "The AI processing service is temporarily unavailable. Please try again shortly.",
                },
            ) from exc

        if (
            "504" in error_message
            or "DEADLINE_EXCEEDED" in error_message
        ):
            raise HTTPException(
                status_code=504,
                detail={
                    "error": "AI processing timeout.",
                    "message": "AI processing took too long to complete. Please try again.",
                },
            ) from exc
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "AI processing unavailable.",
                    "message": (
                        "The AI processing service is temporarily "
                        "unavailable. Please try again shortly."
                    ),
                },
            ) from exc

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Document processing failed.",
                "message": error_message,
            },
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Document processing failed.",
                "message": str(exc),
            },
        ) from exc

@router.get("")
def get_all_documents():
    """
    Retrieve all persisted documents.
    """

    try:
        return service.repository.get_all_documents()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve documents.",
                "message": str(exc),
            },
        ) from exc

@router.get("/{document_name}")
def get_document(document_name: str):
    """
    Retrieve the latest persisted result for a document.
    """

    try:
        result = service.repository.get_document(
            document_name
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Document not found.",
                    "document_name": document_name,
                },
            )

        return result

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve document.",
                "message": str(exc),
            },
        ) from exc