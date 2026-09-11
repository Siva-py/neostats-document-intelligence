import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from app.schemas.extraction import ExtractedDocument
from app.core.logging import get_logger

logger = get_logger(__name__)

load_dotenv()


class ExtractionService:

    def __init__(self):
        self.api_keys = [
        os.getenv("GEMINI_API_KEY_1"),
        os.getenv("GEMINI_API_KEY_2"),
        os.getenv("GEMINI_API_KEY_3"),
        os.getenv("GEMINI_API_KEY_4"),
        ]

        self.api_keys = [
            key for key in self.api_keys
            if key
        ]
       

        if not self.api_keys:
            raise RuntimeError(
                "No GEMINI_API_KEY_* keys are configured."
            )

        self.current_key_index = 0

        self.client = genai.Client(
            api_key=self.api_keys[self.current_key_index],
            http_options=types.HttpOptions(
                timeout=120000
            ),
        )
    def _call_gemini(
        self,
        prompt: str,
        uploaded_file=None,
        file_path: str | None = None,
    ) -> str:

        last_error = None

        for attempt in range(len(self.api_keys)):

            try:

                # ---------------------------------
                # If this is a retry after key
                # rotation, upload the PDF using
                # the new Gemini client.
                # ---------------------------------

                if attempt > 0 and file_path is not None:

                    logger.info(
                        "Re-uploading original document using the new Gemini API key."
                    )

                    uploaded_file = self.client.files.upload(
                        file=file_path
                    )

                    logger.info("Document re-uploaded successfully.")

                contents = [prompt]

                if uploaded_file is not None:
                    contents.insert(0, uploaded_file)

                response = self.client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=contents,
                )

                response_text = response.text

                if not response_text:
                    raise RuntimeError(
                        "Gemini returned an empty response."
                    )

                return response_text.strip()

            except Exception as exc:

                last_error = exc

                error_text = str(exc)

                is_quota_error = (
                    "429" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text
                    or "quota" in error_text.lower()
                )

                is_service_unavailable = (
                    "503" in error_text
                    or "UNAVAILABLE" in error_text
                    or "Service Unavailable" in error_text
                )

                if is_service_unavailable:
                    raise RuntimeError(
                        "Gemini service is temporarily unavailable."
                    ) from exc

                if not is_quota_error:
                    raise

                if attempt == len(self.api_keys) - 1:
                    break

                self.current_key_index += 1

                logger.warning(
                "Gemini API key %s quota exhausted.",
                attempt + 1,
                )

                logger.info(
                "Switching to Gemini API key %s.",
                self.current_key_index + 1,
                )

                self.client = genai.Client(
                    api_key=self.api_keys[
                        self.current_key_index
                    ],
                    http_options=types.HttpOptions(
                        timeout=120000
                    ),
                )

        raise RuntimeError(
            "All configured Gemini API keys are "
            "exhausted or unavailable."
        ) from last_error

    def _clean_json_response(
        self,
        response_text: str,
    ) -> str:

        cleaned_text = response_text.strip()

        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]

        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]

        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]

        return cleaned_text.strip()

    def _parse_and_validate(
        self,
        response_text: str,
    ) -> dict:

        cleaned_text = self._clean_json_response(
            response_text
        )

        try:
            extracted_json = json.loads(
                cleaned_text
            )
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Gemini returned invalid JSON."
            ) from exc

        try:
            validated_document = (
                ExtractedDocument.model_validate(
                    extracted_json
                )
            )
        except Exception as exc:
            raise RuntimeError(
                "Gemini response does not match "
                "the required extraction schema."
            ) from exc

        return validated_document.model_dump()

    def _build_initial_prompt(
    self,
    ocr_text: str,
    document_type: str,
) -> str:

        schema = ExtractedDocument.model_json_schema()

        return f"""
    You are a financial document extraction system.

    Document type: {document_type}

    You have TWO sources:

    1. The ORIGINAL PDF/DOCUMENT attached to this request.
    2. OCR text provided below.

    IMPORTANT SOURCE PRIORITY:

    - The ORIGINAL PDF/DOCUMENT is the authoritative source.
    - Use the original document to understand visual layout,
    row/column alignment, section headings, table structure,
    parentheses,
    and relationships between labels and values.
    - OCR text is supplementary and may contain row-alignment
    or formatting errors.
    - If OCR text conflicts with the original document,
    follow the original document.

    Extract ALL meaningful visible information from the document.

    STRICT EXTRACTION RULES:

    1. Do not invent values.

    2. Do not infer values that are not supported by the document.

    3. Do not calculate values for the purpose of extraction.

    4. Do not modify extracted values.

    5. Preserve numeric values exactly as they appear in the
    original document.

    6. Preserve all comparative periods.

    7. Associate every value with the correct period.

    8. Preserve every visible financial statement section.

    9. Extract EVERY meaningful visible row and line item.

    10. NEVER skip a visible line item merely because it is
        unusual, additional, newly introduced, or appears
        between other standard accounting rows.

    11. For financial tables, inspect the ORIGINAL DOCUMENT
        row-by-row from top to bottom before producing JSON.

    12. Pay close attention to horizontal alignment between
        row labels and numeric columns.

    13. NEVER shift a numeric value to an adjacent row.

    14. A section heading is not a line item unless the document
        explicitly shows values belonging to that heading.

    15. If a section heading has no values beside it, do not
        assign nearby values to that heading.

    16. Every extracted numeric row MUST have the corresponding
        visible row label from the original document.

    17. NEVER return an empty string for "line_item" when the
        original document contains a visible label for that row.

    18. If a numeric row appears visually aligned with a label,
        associate the value with that label even if OCR text
        places the value on a different line.

    19. Preserve ALL rows appearing before and after totals.

    20. Do not omit subtotal rows.

    21. Do not omit total rows.

    22. Do not omit additional rows simply because they are
        uncommon or appear outside a standard financial
        statement template.

    23. Preserve table structure using arrays and objects.

    24. Preserve schedule references when present.

    25. Financial statement numbers enclosed in parentheses
        are negative values. Preserve the parentheses exactly
        as shown.

    26. Never convert a parenthesized financial value into a
        positive value.

    27. Do not move a subtotal or total into another section.

    28. A row belongs to the section determined by its position
        and the section heading in the ORIGINAL DOCUMENT.

    29. For cash flow statements, explicitly distinguish:
        - operating activities
        - investing activities
        - financing activities
        - cash and cash equivalents reconciliation/movement,
        where present.

    30. A "Net cash..." subtotal belongs to the activity section
        immediately preceding it unless the original document
        clearly indicates otherwise.

    31. Before returning JSON, verify that every subtotal and
        total is assigned to the correct section.

    32. For cash flow statements, numerical relationships may be
        used ONLY as a consistency check for row/section
        association.

    33. Do not change any extracted value to make a calculation
        work.

    34. If arithmetic conflicts with the visible document,
        preserve the document values and labels.

    35. Preserve meaningful information outside the main table.

    36. If information is genuinely missing or unreadable,
        use null where the schema allows it.

    37. Do not omit meaningful visible information.

    38. Before returning JSON, internally verify:

        a. Every meaningful visible row has a line_items entry.

        b. Every numeric row has a non-empty line_item label
        when a visible label exists in the original document.

        c. No numeric row has been accidentally assigned to a
        section heading.

        d. No numeric value has been shifted to an adjacent row.

        e. All comparative-period values are associated with
        the correct period.

        f. Parenthesized values remain negative.

    39. Do not summarize the document.

    40. Return ONLY valid JSON.

    41. Do not return Markdown.

    42. Follow the required schema exactly.

    REQUIRED JSON SCHEMA:

    {json.dumps(schema, indent=2)}

    OCR TEXT:
    {ocr_text}
    """

    def _build_retry_prompt(
            self,
            ocr_text: str,
            document_type: str,
            previous_response: str,
            validation_error: str,
        ) -> str:

            schema = ExtractedDocument.model_json_schema()

            return f"""
    Your previous extraction response was rejected.

    You MUST redo the extraction.

    Document type: {document_type}

    REASON THE PREVIOUS RESPONSE WAS REJECTED:

    {validation_error}

    PREVIOUS RESPONSE:

    {previous_response}

            STRICT CORRECTION RULES:

            1. Return ONLY valid JSON.
            2. The JSON MUST conform exactly to the
            required schema below.
            3. Do not return Markdown or code fences.
            4. Do not explain your answer.
            5. Do not summarize the document.
            6. Do not omit meaningful visible information.
            7. Extract EVERY meaningful visible row and line item.
            8. NEVER skip a visible line item because it is
            unusual, additional, newly introduced, or appears
            between standard accounting rows.
            9. Process financial tables row-by-row from top to bottom.
            10. Include all rows appearing before and after totals.
            11. Preserve all comparative periods.
            12. Preserve the correct period for every value.
            13. Preserve all financial statement sections.
            14. Preserve all meaningful line items.
            15. Preserve schedules and references when present.
            16. Use null only when information is genuinely
                missing or unreadable.
            17. Do not invent values.
            18. Do not infer values.
            19. Do not calculate values.
            20. Do not modify numeric values.
            21. Preserve evidence for every extracted line item
                whenever available.
            22. Before returning the JSON, internally verify that
                every meaningful visible table row has a
                corresponding line_items entry.
            23. Keep the exact field names required by the schema.
            24. Keep the exact nesting and data types required
                by the schema.

    REQUIRED JSON SCHEMA:

    {json.dumps(schema, indent=2)}

    OCR TEXT:

    {ocr_text}

    Return ONLY the corrected JSON.
    """

    def _calculate_confidence(
        self,
        document: dict,
    ) -> dict:

        financial_statement = document.get(
            "financial_statement",
            {}
        )

        sections = financial_statement.get(
            "sections",
            []
        )

        for section in sections:

            line_items = section.get(
                "line_items",
                []
            )

            for item in line_items:

                evidence = item.get(
                    "evidence"
                )

                values = item.get(
                    "values",
                    {}
                )

                # No evidence available
                if not isinstance(evidence, dict):

                    item["confidence"] = 0.0
                    continue

                source_text = str(
                    evidence.get(
                        "source_text",
                        ""
                    )
                ).strip()

                page_number = evidence.get(
                    "page_number"
                )

                if not source_text:

                    item["confidence"] = 0.0
                    continue

                score = 0.0

                # Evidence text exists
                score += 0.30

                # Page number exists
                if isinstance(
                    page_number,
                    int,
                ) and page_number > 0:

                    score += 0.20

                # Check extracted values against evidence
                valid_values = 0
                total_values = 0

                if isinstance(values, dict):

                    for value in values.values():

                        if value is None:
                            continue

                        total_values += 1

                        normalized_value = (
                            str(value)
                            .replace(",", "")
                            .replace(" ", "")
                            .strip()
                        )

                        normalized_source = (
                            source_text
                            .replace(",", "")
                            .replace(" ", "")
                        )

                        if normalized_value in normalized_source:
                            valid_values += 1

                if total_values > 0:

                    evidence_ratio = (
                        valid_values / total_values
                    )

                    score += (
                        0.50 * evidence_ratio
                    )

                else:
                    # No numeric/value content to verify
                    score += 0.50

                item["confidence"] = round(
                    min(score, 1.0),
                    2,
                )

        return document    
    
    def extract(
    self,
    ocr_text: str,
    document_type: str,
    file_path: str | None = None,
):

    # -----------------------------
    # UPLOAD ORIGINAL DOCUMENT
    # -----------------------------

        uploaded_file = None

        if file_path is not None:

            print("📄 Uploading original document to Gemini...")

            uploaded_file = self.client.files.upload(
                file=file_path
            )

            print("✅ Original document uploaded.")

        # -----------------------------
        # ATTEMPT 1
        # -----------------------------

        initial_prompt = self._build_initial_prompt(
            ocr_text=ocr_text,
            document_type=document_type,
        )

        first_response = self._call_gemini(
        initial_prompt,
        uploaded_file=uploaded_file,
        file_path=file_path,
)

        try:

            result = self._parse_and_validate(
                first_response
            )

            return self._calculate_confidence(
                result
            )

        except RuntimeError as first_error:

            print("\n⚠️ Gemini Attempt 1 failed.")
            print("Reason:", first_error)
            print("🔄 Triggering Gemini Attempt 2...\n")

            # -----------------------------
            # ATTEMPT 2
            # -----------------------------

            retry_prompt = self._build_retry_prompt(
                ocr_text=ocr_text,
                document_type=document_type,
                previous_response=first_response,
                validation_error=str(first_error),
            )

            print("🚀 Gemini Attempt 2 started...")

            second_response = self._call_gemini(
                retry_prompt,
                uploaded_file=uploaded_file,
                file_path=file_path,
            )

            try:

                result = self._parse_and_validate(
                    second_response
                )

                return self._calculate_confidence(
                    result
                )

            except RuntimeError as second_error:

                raise RuntimeError(
                    "Document extraction failed after "
                    "2 Gemini attempts. "
                    f"Final error: {second_error}"
                ) from second_error