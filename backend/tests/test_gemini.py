from app.services.extraction_service import ExtractionService

from app.services.ocr_service import extract_text_with_ocr

from app.schemas.extraction import ExtractedDocument

import time
from app.services.financial_validation_service import validate_document


file_path = (
    r"C:\DM_Drive\Projects\NeoStats_project_root"
    r"\datasets&ProblemDocument\New Dataset 1"
    r"\Cash Flows\Consolidated Cash Flow Statement 2018.pdf"
)


print("Starting OCR...")

ocr_start = time.perf_counter()

ocr_result = extract_text_with_ocr(
    file_path
)

ocr_time = time.perf_counter() - ocr_start

print(f"OCR TIME: {ocr_time:.2f} seconds")


print("\nStarting Gemini extraction...")

service = ExtractionService()

gemini_start = time.perf_counter()

result = service.extract(
    ocr_text=ocr_result["text"],
    document_type="cash_flow_statement",
    file_path=file_path,
)

gemini_time = time.perf_counter() - gemini_start

print(f"GEMINI TIME: {gemini_time:.2f} seconds")


validated_result = ExtractedDocument.model_validate(
    result
)
print("\nStarting financial validation...")

validation = validate_document(
    document_type="cash_flow_statement",
    extracted_data=result,
)

print("\n========== FINANCIAL VALIDATION ==========\n")

print(validation)

print("\n==========================================")

print("\n========== EXTRACTION RESULT ==========\n")

print("Document type:")
print(validated_result.document_type)

print("\nComparative periods:")
print(validated_result.comparative_periods)

print("\nFinancial statement:")

for section in validated_result.financial_statement.sections:

    print(f"\n--- {section.section_name} ---")

    for item in section.line_items:

        print(
            item.line_item,
            "=>",
            item.values
        )


print("\n========================================")

print("\nEXTRACTION SUCCESS")
print("Schema validation: PASS")