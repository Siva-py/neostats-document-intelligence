# NeoStats -- Document Intelligence

AI-powered financial document extraction, validation, persistence, and
REST API platform.

## Solution Overview

NeoStats Document Intelligence is an end-to-end prototype for processing
financial documents in PDF, JPG, and PNG formats.

The platform validates uploads, performs OCR for scanned/image
documents, uses Gemini 3.6 Flash for structured extraction, performs
deterministic financial validation, stores results in SQLite, and
exposes a web dashboard plus REST APIs.

Supported document types:

- Invoice
- Balance Sheet
- Profit & Loss
- Cash Flow Statement

Automated document-type classification is intentionally not implemented;
the document type is selected in the frontend and supplied as request
metadata.

## Architecture

```text
Frontend Dashboard
       |
       v
FastAPI REST API
       |
       v
Document Validation
       |
       +------> OCR.Space
       |        OCR / table extraction
       |
       v
Gemini 3.6 Flash
AI field & table extraction
       |
       v
Structured Pydantic / JSON data
       |
       v
Financial Validation
PASS / FAIL / NOT_APPLICABLE
       |
       v
SQLite Persistence
       |
       +------> Dashboard
       +------> REST JSON
```

See `docs/architecture.png` for the visual architecture diagram.

## Technology Stack

---

  Component               Technology              Reason

---

  Backend                 Python + FastAPI        Lightweight REST API
                                                  with automatic
                                                  Swagger/OpenAPI

  Frontend                HTML + CSS + JavaScript Simple and sufficient
                                                  for the assessment

  OCR                     OCR.Space               Free-tier OCR with
                                                  PDF/image and table
                                                  support

  AI extraction           Gemini 3.6 Flash        Structured extraction
                                                  of financial fields and
                                                  tables

  Validation              Python service layer    Deterministic
                                                  calculations
                                                  independent of the LLM

  Data models             Pydantic                Structured
                                                  machine-readable output

  Persistence             SQLite                  Simple persistent
                                                  database for the
                                                  prototype

  PDF processing          PyMuPDF                 PDF validation and page
                                                  counting

  Image processing        Pillow                  Image validation

Testing                 Pytest                  Automated validation
                                                  and API tests
---------------------------------------------------------------

## Input Validation

Supported formats:

- PDF
- JPG / JPEG
- PNG
- Native and scanned/image-based documents
- Maximum 3 pages

Validation occurs before OCR or AI extraction and checks file type,
emptiness, readability, corruption, page count, and basic integrity.

## Extraction

OCR.Space is used for OCR and table-oriented text extraction,
particularly for scanned/image documents.

Gemini 3.6 Flash receives the original document together with
supplementary OCR information and produces structured extraction.

The output represents statement metadata, periods, currencies/units,
sections, financial line items, invoice line items, values, evidence,
page numbers, notes, signatures, and footer information where present.

Missing values are returned as `null`. The application does not
intentionally invent unsupported values.

## Evidence

Extracted line items can contain source text and page number:

```json
{
  "line_item": "Total Assets",
  "values": {
    "2026": "123456.78"
  },
  "evidence": {
    "source_text": "Total Assets 123,456.78",
    "page_number": 1
  }
}
```

Confidence scoring is optional and is not used as an arbitrary
LLM-generated score.

## Financial Validation

Validation is deterministic and based on fields actually present in the
source document.

### Invoice

- Quantity × Unit Price ≈ Line Total
- Line totals reconcile with reported subtotal/total where applicable
- Taxable Amount + Tax + applicable rounding ≈ Total
- Cash Paid − Total ≈ Change
- GST/tax-included totals are handled according to available source
  fields

### Balance Sheet

For each period:

- Capital & Liabilities ≈ Assets
- Asset component totals are checked where sufficient
- Capital/liability component totals are checked where sufficient

### Profit & Loss

For each comparative period:

- Interest Earned + Other Income ≈ Total Income
- Interest Expended + Operating Expenses + Provisions & Contingencies
  ≈ Total Expenditure
- Total Income − Total Expenditure ≈ Consolidated Net Profit before
  Minority Interest
- Profit before Minority Interest − Minority Interest ≈ Consolidated
  Net Profit attributable to Group
- Current Profit + Brought Forward Profit ≈ Total Available for
  Appropriation where applicable

### Cash Flow Statement

For each comparative period:

- Operating + Investing + Financing + FX/Translation Adjustment ≈ Net
  Increase in Cash
- Opening Cash + Net Increase + applicable adjustments ≈ Closing Cash
- Parentheses/bracketed values are interpreted as negative numbers

If a required validation input is unavailable, the result is
`NOT_APPLICABLE` rather than an assumed value.

Each validation result contains the check/formula, inputs, calculated
value, reported value, variance, and status.

## Processing Status

- `PASS` --- successful processing with required applicable
  validations passing.
- `FAILED` --- invalid, unsupported, corrupted, unreadable, or
  otherwise unprocessable document.

Individual validation checks may be `PASS`, `FAIL`, or `NOT_APPLICABLE`.

## REST API

### Process document

```http
POST /api/v1/documents/process
Content-Type: multipart/form-data
```

Form fields:

```text
file=<PDF/JPG/PNG>
document_type=invoice
```

Allowed document types:

```text
invoice
balance_sheet
profit_and_loss
cash_flow_statement
```

Example:

```bash
curl -X POST "<BACKEND_URL>/api/v1/documents/process"   -F "file=@sample_invoice.pdf"   -F "document_type=invoice"
```

### List documents

```http
GET /api/v1/documents
```

### Get latest result

```http
GET /api/v1/documents/{document_name}
```

### Health

```http
GET /api/v1/health
```

### Swagger/OpenAPI

```text
<BACKEND_URL>/docs
```

## Response Structure

Successful processing responses contain:

- `document_name`
- `document_type`
- `processing_status`
- `file_validation`
- `extracted_data`
- `validation`
- `processing_metadata`

The structure remains consistent while extracted fields vary by document
type.

## Persistence

SQLite stores:

- Document name
- Document type
- Processing status
- Complete result JSON
- Processing timestamp

The database is initialized automatically when the FastAPI application
starts.

The repository returns the latest persisted result for a document name.

## Error Handling

Controlled errors are returned for unsupported formats, invalid/empty
files, corrupt/unreadable documents, page-limit violations, OCR
failures, AI unavailability, AI timeouts, database failures, and
unexpected processing errors.

Internal stack traces and API credentials are not intentionally exposed
to frontend users.

## Logging

The application logs major processing stages including processing start,
validation, OCR completion, AI extraction, Gemini upload/key rotation
events, financial validation, persistence, and failures.

API keys are not logged.

## Project Structure

```text
project-root/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes/documents.py
│   │   ├── core/database.py
│   │   ├── core/logging.py
│   │   ├── models/document.py
│   │   ├── schemas/extraction.py
│   │   ├── services/
│   │   │   ├── document_validation_service.py
│   │   │   ├── ocr_service.py
│   │   │   ├── extraction_service.py
│   │   │   ├── financial_validation_service.py
│   │   │   └── document_service.py
│   │   └── repositories/document_repository.py
│   ├── tests/
│   │   ├── test_api.py
│   │   ├── test_validation.py
│   │   ├── test_validation_service.py
│   │   ├── test_gemini.py
│   │   └── test_gemini_pdf.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── docs/
│   ├── architecture.png
│   └── solution_presentation.pptx
├── sample_outputs/
│   ├── invoice.json
│   ├── balance_sheet.json
│   ├── profit_and_loss.json
│   └── cash_flow_statement.json
├── .env.example
├── .gitignore
└── README.md
```

## Environment Variables

Use `.env.example` as the template:

```text
OCR_SPACE_API_KEY=
GEMINI_API_KEY_1=
GEMINI_API_KEY_2=
GEMINI_API_KEY_3=
GEMINI_API_KEY_4=
```

Real credentials must never be committed to GitHub.

## Local Setup

```cmd
cd backend
python -m venv venv
venv\Scriptsctivate
pip install -r requirements.txt
```

Create `backend/.env` and provide the required credentials.

Start the API:

```cmd
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Local API:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

The frontend is a static HTML/CSS/JavaScript application. For
deployment, its `API_BASE_URL` is configured to the deployed backend.

## Testing

Testing includes:

- Invoice images
- Balance Sheet PDFs
- Profit & Loss PDFs
- Cash Flow PDFs
- Scanned/image-based documents
- Unsupported/invalid files
- Page-limit validation
- Financial calculation validation
- Persistent result retrieval
- API health flow
- Missing-document 404 flow

The API automated tests currently include:

```text
2 passed
```

File-validation and financial-validation tests are also included.

## Sample Outputs

Representative real processed outputs are stored in:

```text
sample_outputs/
```

They cover Invoice, Balance Sheet, Profit & Loss, and Cash Flow
Statement processing and include validation calculations.

## Known Limitations

- OCR and AI accuracy depends on source quality and document layout.
- External OCR and LLM services are subject to quota, availability,
  and network latency.
- SQLite is suitable for this prototype but not ideal for
  high-concurrency production workloads.
- Complex layouts or severely degraded scans may require additional
  preprocessing or specialized document models.
- AI service outages can temporarily prevent processing.
- Automated document-type classification is outside the case-study
  scope.

## Production Improvements

A production deployment could add PostgreSQL, object storage,
asynchronous processing queues, authentication/authorization, rate
limiting, stronger file security scanning, OCR/model fallbacks, human
review for uncertain extraction, metrics/tracing, centralized logs,
CI/CD, and a larger automated regression corpus.

## Free-Tier Services

The prototype uses free/free-tier options where applicable:

- OCR.Space
- Gemini API
- SQLite

Provider quotas and availability may vary.

## AI / Tool Usage Declaration

Generative AI was explicitly permitted by the case study.

ChatGPT was used as an AI coding assistant for architecture guidance,
debugging, testing, implementation support, and documentation support.

Gemini is used by the application as the document extraction model.

AI-assisted code was reviewed, tested, debugged, and modified during
development. The candidate remains responsible for the submitted
solution.

## Deployment URLs

Live deployment links:

```text
GitHub:
https://github.com/Siva-py/neostats-document-intelligence

Frontend:
https://neostats-document-intelligence-mxy7.onrender.com/

Backend API:
https://neostats-document-intelligence-api.onrender.com/

Health:
https://neostats-document-intelligence-api.onrender.com/api/v1/health

Swagger/OpenAPI:
https://neostats-document-intelligence-api.onrender.com/docs
```

## Final Submission Checklist

- [X] Four supported document types
- [X] PDF / JPG / PNG support
- [X] Maximum 3-page validation
- [X] Native and scanned/image documents
- [X] Structured extraction
- [X] Evidence/page-number support
- [X] Financial validation
- [X] PASS / FAIL / NOT_APPLICABLE
- [X] SQLite persistence
- [X] REST API
- [X] Swagger/OpenAPI
- [X] Dashboard
- [X] Raw JSON view
- [X] Automated validation tests
- [X] Automated financial tests
- [X] Automated API tests
- [X] Sample JSON outputs
- [X] Architecture diagram
- [X] Solution presentation
- [X] AI/tool usage declaration
- [X] Known limitations and production improvements
- [X] Public GitHub repository
- [X] Live frontend URL
- [X] Live backend URL
- [X] Live Swagger URL
