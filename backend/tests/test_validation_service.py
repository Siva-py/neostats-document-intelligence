from app.services.extraction_service import ExtractionService
from app.services.ocr_service import extract_text_with_ocr
from app.services.financial_validation_service import validate_document


file_path = (
    r"C:\DM_Drive\Projects\NeoStats_project_root"
    r"\datasets&ProblemDocument\New Dataset 1"
    r"\Invoices\X51005663293.jpg"
)


print("Starting OCR...")

ocr_result = extract_text_with_ocr(file_path)
print("\n========== OCR TEXT ==========\n")
print(ocr_result["text"])
print("\n========== END OCR TEXT ==========\n")
print("OCR completed.")
print("Starting Gemini extraction...")


service = ExtractionService()

result = service.extract(
    ocr_text=ocr_result["text"],
    document_type="invoice",
    file_path=file_path,
)

print("Gemini extraction completed.")

print("\nEXTRACTED STRUCTURE:")
print(result["financial_statement"])

print("\nRunning financial validation...")

validation = validate_document(
    document_type="invoice",
    extracted_data=result,
)

print("\nVALIDATION RESULT:")
print(validation)