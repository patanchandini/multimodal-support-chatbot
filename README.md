# Multimodal Customer-Support Chatbot

A production-shaped FastAPI service that accepts a customer message plus an
optional file (PDF invoice, screenshot, product image), extracts structured
fields via OCR / PDF text extraction, and verifies the file against the
customer's written claims. It rejects prompt-injection attempts, masks PII
in logs, sweeps expired uploads, and moves slow requests to a Celery
background queue.


**🔗 Live Demo:** https://multimodal-support-chatbot.onrender.com/docs

**⚡ Health Check:** https://multimodal-support-chatbot.onrender.com/health

> ⚠️ **Free-tier note:** the live demo sleeps after 15 minutes of inactivity. The first request may take ~30 seconds to wake the server.


---

## Features

| Requirement | Implementation |
|---|---|
| Extract order IDs, dates, amounts, products, error codes | `app/ocr/extractor.py`, `app/ocr/parsers.py` |
| OCR for screenshots and photos | Tesseract via `pytesseract` |
| Text extraction from PDFs | `pdfplumber` |
| Cross-verify file evidence vs customer message | `app/verification/comparator.py` |
| Detect conflicts and request clarification | `app/chat/handler.py` |
| Reject prompt-injection attempts | `app/security.py` |
| Auto-delete unsafe files | `app/main.py` (on rejection) |
| Mask PII / payment info in logs | `app/masking.py` |
| Retention sweep for expired uploads | `app/cleanup.py` + background loop |
| 30-second timeout → background queue | `app/main.py` → `app/tasks.py` (Celery + Redis) |
| Poll background job status | `GET /jobs/{job_id}` |

---

## Architecture

```
                     ┌───────────────────────────────┐
                     │        FastAPI (/chat)        │
                     └───────────────┬───────────────┘
                                     │
             ┌───────────────────────┼───────────────────────┐
             │                       │                       │
        Validate file          Extract text             Verify fields
    (magic bytes, size)     ┌──────────────┐        ┌──────────────────┐
             │              │  pdfplumber  │        │  comparator.py   │
             │              │  or Tesseract│        │  (order IDs,     │
             │              └──────────────┘        │   dates, amounts)│
             │                       │              └──────────────────┘
             │                       │                       │
    ┌────────▼────────┐    ┌─────────▼──────┐      ┌─────────▼────────┐
    │  security.py    │    │  masking.py    │      │   handler.py     │
    │  (injection)    │    │  (PII masks)   │      │  (compose reply) │
    └─────────────────┘    └────────────────┘      └──────────────────┘
             │
    ┌────────▼────────┐
    │ storage.py      │──► uploads/ (retention sweep every 60s)
    └─────────────────┘
             │
             └──► >30s? ──► Celery queue (Redis) ──► app/tasks.py
                                │
                                └──► GET /jobs/{id} polls DB
```

---

## Requirements

- Python 3.11
- Tesseract OCR 5.x — install from https://github.com/UB-Mannheim/tesseract/wiki
- Redis 7 (for the background queue)
- Docker (optional, for Redis + full stack)

---

## Installation

```powershell
# 1. Enter the project directory
cd "E:\real-time projects\chatbot"

# 2. Create and activate a virtual environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install Python dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Tesseract must be installed at `C:\Program Files\Tesseract-OCR\`. The path is
set in `app/ocr/_tess.py`.

---

## Configuration

Create `.env` in the project root:

```
UPLOAD_DIR=./uploads
RETENTION_SECONDS=3600
PROCESSING_TIMEOUT_SECONDS=30
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=sqlite:///./chatbot.db
```

| Key | Meaning | Default |
|---|---|---|
| `UPLOAD_DIR` | Where uploaded files are stored | `./uploads` |
| `RETENTION_SECONDS` | How long files are kept before deletion | `3600` |
| `PROCESSING_TIMEOUT_SECONDS` | Above this, requests go to the background queue | `30` |
| `REDIS_URL` | Broker URL for Celery | `redis://localhost:6379/0` |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./chatbot.db` |

---

## Running the Service

### Minimal (FastAPI only)

```powershell
uvicorn app.main:app --reload --port 8000
```

- API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

### Full stack (with background queue)

**Terminal 1 — Redis:**

```powershell
docker run -d -p 6379:6379 --name chatbot-redis redis:7-alpine
```

**Terminal 2 — Celery worker:**

```powershell
.\.venv\Scripts\Activate.ps1
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

**Terminal 3 — FastAPI:**

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

---

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/chat` | Main multimodal endpoint |
| `GET` | `/jobs/{job_id}` | Poll background job status |
| `POST` | `/admin/cleanup` | Manually sweep expired files |

### `POST /chat` — Request

Multipart form fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `session_id` | string | yes | Groups related requests |
| `message` | string | yes | Customer's typed text |
| `file` | file | no | PDF, PNG, JPEG, or WebP |

### Response — Match

```json
{
  "session_id": "abc",
  "status": "answered",
  "reply": "Thanks — here's what I verified from your document:\n- order_ids: ['ORD-12345']\n- amounts: [149.99]",
  "job_id": null,
  "verification": {
    "status": "match",
    "matched_fields": {
      "order_ids": ["ORD-12345"],
      "amounts": [149.99]
    },
    "conflicts": [],
    "missing": [],
    "notes": []
  }
}
```

### Response — Conflict

```json
{
  "session_id": "abc",
  "status": "needs_clarification",
  "reply": "I found a mismatch between your message and the file:\n- Order ID mismatch: message=['ORD-99999'] file=['ORD-12345']\n- Amount mismatch: message=[500.0] file=[149.99]",
  "verification": {
    "status": "conflict",
    "matched_fields": {},
    "conflicts": [
      "Order ID mismatch: message=['ORD-99999'] file=['ORD-12345']",
      "Amount mismatch: message=[500.0] file=[149.99]"
    ],
    "missing": [],
    "notes": []
  }
}
```

### Response — Rejected (prompt-injection)

```json
{
  "session_id": "abc",
  "status": "rejected",
  "reply": "I can't act on instructions that appear inside uploaded files. Please describe your request in the chat message.",
  "job_id": null,
  "verification": null
}
```

### Response — Queued (background processing)

```json
{
  "session_id": "abc",
  "status": "queued",
  "reply": "Your file is taking longer than usual to process. I've queued it and will reply here shortly.",
  "job_id": "9f1c4e8a2b7d4e01",
  "verification": null
}
```

---

## Example Requests

### Matching invoice

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat `
  -F "session_id=abc" `
  -F "message=My order ORD-12345 for USD 149.99 was damaged" `
  -F "file=@test_files/good_invoice.pdf"
```

### Mismatched data (triggers conflict)

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat `
  -F "session_id=abc" `
  -F "message=My order ORD-99999 for USD 500.00 was damaged" `
  -F "file=@test_files/good_invoice.pdf"
```

### Blurry image (triggers clarification)

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat `
  -F "session_id=abc" `
  -F "message=Help with my order" `
  -F "file=@test_files/blurry.png"
```

### Prompt-injection PDF (rejected)

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat `
  -F "session_id=abc" `
  -F "message=Please help with my invoice" `
  -F "file=@test_files/injection.pdf"
```

### Poll a background job

```powershell
curl.exe http://127.0.0.1:8000/jobs/<job_id>
```

---

## Testing

```powershell
python -m pytest tests\ -v
```

**43 tests, all passing.** Coverage by module:

| Module | Tests | What it verifies |
|---|---|---|
| `test_api.py` | 8 | Endpoints, uploads, conflict/injection routing |
| `test_masking.py` | 7 | PII / card / IBAN / CVV / phone redaction |
| `test_parsers.py` | 8 | Order IDs, dates, amounts, error codes, products |
| `test_quality.py` | 4 | Image size / sharpness / brightness gates |
| `test_retention.py` | 4 | File persistence + retention sweep |
| `test_security.py` | 7 | Prompt-injection pattern detection |
| `test_verification.py` | 5 | Message-vs-file comparison logic |

---

## Security Model

- **File type validation** — magic-byte sniffing, not just extension
- **Size limit** — 15 MB default (`max_file_size_mb`)
- **Prompt-injection detection** — regex patterns for common attacks
  (`ignore previous instructions`, `reveal system prompt`, `you are now`,
  `<script>`, etc.)
- **PII masking** — cards, IBANs, emails, phones, CVVs, national IDs
- **Auto-deletion** — rejected files are removed immediately
- **Retention sweep** — expired uploads purged every 60 seconds
- **Audit log** — every request recorded with masked fields

### Masked fields

```
4111 1111 1111 1111    →  [CARD_REDACTED]
DE89 3704 0044 0532... →  [IBAN_REDACTED]
john@example.com       →  [EMAIL_REDACTED]
+1 555 123 4567        →  [PHONE_REDACTED]
CVV: 123               →  CVV [CVV_REDACTED]
123456789012           →  [ID_REDACTED]
```

---

## Data Model

| Table | Purpose |
|---|---|
| `uploaded_files` | Tracks every uploaded file with `expires_at` for the sweep |
| `jobs` | Persists background job state for `GET /jobs/{id}` |
| `audit_log` | Records every event with masked details |

---

## Deployment

`docker-compose.yml` at the project root brings up Redis, the Celery worker,
and the FastAPI service:

```powershell
docker compose up --build
```

The API is exposed on port 8000.

---

## Project Layout

```
chatbot/
├── README.md
├── .env
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── app/
│   ├── main.py                  FastAPI application
│   ├── config.py                Settings (pydantic-settings)
│   ├── db.py                    SQLAlchemy engine + session
│   ├── models.py                UploadedFile, Job, AuditLog
│   ├── schemas.py               Pydantic response types
│   ├── masking.py               PII redaction
│   ├── security.py              MIME + injection checks
│   ├── storage.py               File persistence
│   ├── cleanup.py               Retention sweeper
│   ├── tasks.py                 Celery worker entry point
│   ├── ocr/
│   │   ├── _tess.py             Tesseract path config
│   │   ├── extractor.py         OCR + PDF text extraction
│   │   ├── parsers.py           Field extraction regexes
│   │   └── quality.py           Image quality gate
│   ├── verification/
│   │   └── comparator.py        Message-vs-file verification
│   └── chat/
│       ├── handler.py           Response composition
│       └── prompts.py           System prompt text
└── tests/
    ├── conftest.py
    ├── test_api.py
    ├── test_masking.py
    ├── test_parsers.py
    ├── test_quality.py
    ├── test_retention.py
    ├── test_security.py
    └── test_verification.py
```

---

## Evaluation Criteria Coverage

| # | Criterion | Verified by |
|---|---|---|
| 1 | OCR extracts order IDs, dates, amounts, products, error codes | `test_parsers.py`, manual PDF test |
| 2 | Cross-verify with customer message | `test_verification.py`, `test_api.py` |
| 3 | Conflicts → request clarification | `test_conflict_when_order_ids_differ` |
| 4 | Blurred images → request re-upload | `test_chat_handles_blurry_image` |
| 5 | Low-resolution images → request re-upload | `test_chat_handles_tiny_image` |
| 6 | Never invent missing values | `test_no_matched_fields_on_conflict` |
| 7 | Prompt-injection rejected | `test_chat_rejects_injection_pdf` |
| 8 | Unsafe file auto-deleted | `uploads/` listing post-test |
| 9 | PII masked in logs | `test_masking.py` |
| 10 | Files deleted after retention | `test_retention.py` |
| 11 | 30s timeout → background queue | Celery worker log + `/jobs` poll |

---

