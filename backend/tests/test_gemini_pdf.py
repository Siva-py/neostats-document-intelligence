from app.services.extraction_service import ExtractionService

import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


file_path = (
    r"C:\DM_Drive\Projects\NeoStats_project_root"
    r"\datasets&ProblemDocument\New Dataset 1"
    r"\Cash Flows\Consolidated Cash Flow Statement 2018.pdf"
)


api_key = os.getenv("GEMINI_API_KEY_2")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY_2 is not configured.")


client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(
        timeout=120000
    ),
)


print("Uploading PDF to Gemini...")


upload_start = time.perf_counter()

uploaded_file = client.files.upload(
    file=file_path
)

upload_time = time.perf_counter() - upload_start

print(f"UPLOAD TIME: {upload_time:.2f} seconds")
print("PDF uploaded successfully.")


prompt = """
Analyze this financial document carefully.

This is a Consolidated Cash Flow Statement.

I want you to inspect the ORIGINAL PDF visually and extract the following
specific portion exactly as it appears.

Focus especially on:

1. Direct taxes paid (net of refunds)
2. Net cash from operating activities
3. Cash flows used in investing activities
4. Purchase of fixed assets
5. Proceeds from sale of fixed assets
6. Investment in subsidiaries and/or joint ventures
7. Net cash used in investing activities

For each row, give me:

- Exact row label
- 31-Mar-2018 value
- 31-Mar-2017 value

IMPORTANT:
- Use the visual layout of the PDF.
- Pay attention to which numbers are horizontally aligned with each row.
- Do NOT shift values between adjacent rows.
- Parentheses mean negative values.
- Do not calculate or infer values.
- Do not correct values using arithmetic.
- If a section heading has no numbers beside it, report its values as null.

Return ONLY a simple table.
"""


print("Starting Gemini PDF analysis...")

gemini_start = time.perf_counter()

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=[
        uploaded_file,
        prompt,
    ],
)

gemini_time = time.perf_counter() - gemini_start

print(f"GEMINI TIME: {gemini_time:.2f} seconds")

print("\n========== GEMINI PDF RESULT ==========\n")
print(response.text)
print("\n========== END RESULT ==========\n")