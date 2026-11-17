# Technical Blueprint — AI-Powered Resume Parser & Job Application Pipeline

> Status: implemented
> Scope: 3-day backend-focused internship task, plus a Company career-site UI.
> Source of truth: Internship Cohort Technical Task Document (3 pages).
>
> **Implementation update:** the UI now follows a single-role company application
> flow (`/` → `/apply` → `/apply/details` → `/apply/password` → `/verify` →
> `/dashboard/student`) for the role in `app/core/jobs.py`. Registration and
> profiles additionally store `dob`, `education`, `projects`, `internships`,
> `experience_entries`, `applied_role`, and `application_status`; `/upload` and
> `/register` redirect to `/apply`. The API contracts below remain accurate for
> the original resume/2FA endpoints, with these structured fields added.

---

## 1. Locked decisions

| Area | Decision |
|---|---|
| Verification policy | **Email OTP and WhatsApp OTP are mandatory** (`WHATSAPP_VERIFICATION_REQUIRED=true`). **Browser TOTP is optional.** |
| Email delivery | **Gmail SMTP + App Password** (real delivery) |
| WhatsApp delivery | **Meta WhatsApp Cloud API** (real delivery) |
| Database runtime | **Native PostgreSQL 16** (Docker Compose optional) |
| Frontend | **Minimal HTML UI** served by FastAPI (Jinja2 + static assets), alongside the REST API |
| Secrets | User fills `.env` from `.env.example`; secrets never committed or pasted in chat |
| Password hashing | **Argon2id via `argon2-cffi` / `pwdlib`** (passlib is unmaintained and risky on Python 3.13+; still Argon2id as required) |
| Python | Local machine has **3.14.8**. Target 3.11+; verify all deps install on 3.14. |

### Known prerequisites / risks
- **PostgreSQL is not installed** → install natively via `winget install PostgreSQL.PostgreSQL.16` (Docker optional).
- **Meta WhatsApp Cloud API** requires an **approved authentication/message template** to send business-initiated OTPs to arbitrary numbers. Sandbox/test number needed for dev. This is the biggest external risk.
- **Gmail SMTP** requires 2FA enabled + a generated App Password.
- Python 3.14 may lag for some libs; fallback to Python 3.11/3.12 venv if installs fail.

---

## 2. System architecture

```
Browser (minimal HTML UI / Postman)
        |
        | HTTP REST (JSON + multipart)
        v
FastAPI application
  ├── routers/        request validation + routing
  ├── services/       business logic (parser, auth, otp, delivery, profile)
  ├── schemas/        Pydantic v2 contracts
  ├── models/         SQLAlchemy ORM
  ├── core/           config, security (Argon2id, JWT), exceptions
  └── db/             async engine/session
        |
        ├── PostgreSQL 16 (native)  ── users, user_resumes, otp_challenges
        ├── Gmail SMTP              ── Email OTP
        ├── Meta WhatsApp Cloud API ── WhatsApp OTP
        └── Local uploads/          ── resume files (outside web root)
```

---

## 3. Folder architecture

```
ai_resume_parser/
├── app/
│   ├── main.py                  # FastAPI app factory, middleware, exception handlers, router mounting
│   ├── core/
│   │   ├── config.py            # Pydantic Settings from .env
│   │   ├── jobs.py              # single open role shown across the UI
│   │   ├── security.py          # Argon2id hash/verify, JWT create/decode
│   │   ├── exceptions.py        # AppException + handlers
│   │   └── logging.py           # structured logging
│   ├── db/
│   │   ├── base.py              # Declarative Base
│   │   ├── session.py           # async engine, async_sessionmaker, get_db
│   │   └── init_db.py           # dev create_all (Alembic for real migrations)
│   ├── models/
│   │   ├── enums.py             # UserStatus, OtpChannel, OtpStatus, OtpPurpose
│   │   ├── user.py
│   │   ├── resume.py
│   │   └── otp.py
│   ├── schemas/
│   │   ├── common.py            # envelope + error models
│   │   ├── resume.py
│   │   ├── auth.py
│   │   ├── application.py       # education/project/internship/experience entries
│   │   ├── profile.py
│   │   └── dashboard.py
│   ├── routers/
│   │   ├── resume.py            # POST /api/v1/resume/parse
│   │   ├── auth.py              # register, verify-2fa, resend-otp, login, totp setup/verify
│   │   ├── profile.py           # GET/PATCH /api/v1/profile
│   │   ├── dashboard.py         # GET /api/v1/dashboard/student
│   │   └── pages.py             # HTML UI routes
│   ├── dependencies/
│   │   └── auth.py              # get_current_user (JWT), require_active_user
│   ├── services/
│   │   ├── resume_parser.py     # text extraction + field heuristics (pure, unit-testable)
│   │   ├── resume_service.py    # file save, DB persistence, ownership linking
│   │   ├── auth_service.py      # registration orchestration
│   │   ├── otp_service.py       # generate/hash/store/verify/expire/attempts/resend
│   │   ├── totp_service.py      # secret gen, provisioning URI, verify, encryption
│   │   ├── email_service.py     # Gmail SMTP adapter (aiosmtplib)
│   │   ├── whatsapp_service.py  # Meta Cloud API adapter (httpx)
│   │   ├── profile_service.py
│   │   └── dashboard_service.py
│   ├── templates/               # base, landing, upload, apply_details, apply_password, verify, profile, dashboard
│   └── static/                  # css, js
├── uploads/                     # gitignored
├── migrations/                  # Alembic
├── tests/
│   ├── unit/                    # parser, otp, security
│   └── integration/             # API flows
├── docs/BLUEPRINT.md
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. Database schema

### 4.1 Enums
```sql
CREATE TYPE user_status  AS ENUM ('pending', 'active', 'disabled');
CREATE TYPE otp_channel  AS ENUM ('email', 'whatsapp', 'totp');
CREATE TYPE otp_status   AS ENUM ('pending', 'verified', 'expired', 'failed', 'locked');
CREATE TYPE otp_purpose  AS ENUM ('registration', 'login', 'totp_enrollment');
CREATE TYPE parse_status AS ENUM ('parsed', 'failed');
```

### 4.2 `users`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | `gen_random_uuid()` |
| full_name | varchar(150) | not null |
| email | varchar(255) | not null, **unique**, stored lowercased |
| phone | varchar(20) | not null, E.164 normalized, unique |
| password_hash | text | not null, Argon2id |
| status | user_status | default `pending` |
| email_verified | boolean | default false |
| whatsapp_verified | boolean | default false |
| totp_enabled | boolean | default false |
| totp_secret_encrypted | text | nullable, Fernet-encrypted base32 secret |
| created_at | timestamptz | default now() |
| updated_at | timestamptz | on update |
| last_login_at | timestamptz | nullable |

Indexes: unique(email), unique(phone), index(status).

### 4.3 `user_resumes`
> Parsing happens **before** registration, so a resume may exist without a user.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | also used as `resume_id` handed to the client |
| user_id | UUID FK → users.id | **nullable**, `ON DELETE CASCADE`, set on registration |
| original_filename | varchar(255) | sanitized display name |
| stored_path | text | `uploads/{uuid}.{ext}` |
| mime_type | varchar(100) | |
| size_bytes | bigint | |
| extracted_text | text | raw text |
| extracted_metadata | **JSONB** | `{name,email,phone,skills,experience,qualification}` |
| parse_status | parse_status | default `parsed` |
| created_at | timestamptz | |
| updated_at | timestamptz | |

Indexes: index(user_id), index(created_at). Orphan resumes (user_id NULL) cleaned by a periodic job (documented, not required).

### 4.4 `otp_challenges`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users.id | `ON DELETE CASCADE` |
| channel | otp_channel | email / whatsapp / totp |
| purpose | otp_purpose | default `registration` |
| otp_hash | text | nullable (null for TOTP); HMAC-SHA256 |
| status | otp_status | default `pending` |
| attempts | int | default 0 |
| max_attempts | int | default 5 |
| resend_count | int | default 0 |
| expires_at | timestamptz | |
| verified_at | timestamptz | nullable |
| last_sent_at | timestamptz | for resend cooldown |
| created_at | timestamptz | |

Indexes: index(user_id, channel, status), index(expires_at).

### 4.5 Relationships
```
users 1 ──< user_resumes   (user_id, nullable)
users 1 ──< otp_challenges (user_id)
```
- One user → many resumes (history); one active linked resume for profile display.
- One user → many OTP challenges (one active per channel per purpose).

### 4.6 Activation rule
`status = active` **iff** `email_verified = true` and `whatsapp_verified = true`.
TOTP `totp_enabled` is informational and never blocks activation.

---

## 5. API contracts

### 5.0 Response envelope
Success:
```json
{ "success": true, "message": "...", "data": { } }
```
Error:
```json
{ "success": false, "message": "...", "error": { "code": "INVALID_OTP", "details": null } }
```
HTTP status codes follow REST semantics (200/201/400/401/403/404/409/410/413/415/422/429/502/500).

---

### 5.1 `POST /api/v1/resume/parse`
- **Auth:** none (pre-registration)
- **Content-Type:** `multipart/form-data`, field `file`
- **Accepts:** `.pdf`, `.docx`; max 5 MB (configurable)
- **Validations:** extension + MIME + magic bytes; non-empty; extractable text
- **Processing:** extract text → regex heuristics → persist file + `user_resumes` row (user_id NULL) → return parsed JSON + `resume_id`

Request: `file=@resume.pdf`

Response `200`:
```json
{
  "success": true,
  "message": "Resume parsed successfully",
  "data": {
    "resume_id": "8f1c...",
    "file_name": "resume.pdf",
    "parsed": {
      "full_name": "Arun Kumar",
      "email": "arun@example.com",
      "phone": "9876543210",
      "skills": ["Python", "FastAPI", "SQL", "React"],
      "experience": "Fresher",
      "qualification": "B.E. Computer Science"
    },
    "warnings": ["phone normalized from resume", "qualification inferred"]
  }
}
```
Errors: `415` unsupported type, `413` too large, `422` no extractable text / parse failure, `400` empty file.

---

### 5.2 `POST /api/v1/auth/register`
- **Auth:** none
- **Body:** JSON

```json
{
  "full_name": "Arun Kumar",
  "email": "arun@example.com",
  "phone": "+919876543210",
  "password": "Arun@12345",
  "skills": ["Python", "FastAPI", "React"],
  "experience": "Fresher",
  "qualification": "B.E. Computer Science",
  "resume_id": "8f1c..."
}
```
- `resume_id` optional; if present it must be unlinked (else `409`).
- **Validation:** EmailStr; phone E.164/India; password ≥8 with upper/lower/digit/special; name length; skills list ≤50.
- **Processing:** normalize email/phone → duplicate check (`409`) → Argon2id hash → create 
`pending` user → link resume → create email and WhatsApp challenges → send both OTPs → return challenge info.
- **No JWT is issued at registration.**

Response `201`:
```json
{
  "success": true,
  "message": "Registration successful. Verify your email and WhatsApp to activate your account.",
  "data": {
    "user_id": "a1b2...",
    "status": "pending",
    "verification": {
      "required": ["email", "whatsapp"],
      "optional": ["totp"],
      "challenges": [
        { "channel": "email", "expires_in": 300, "sent_to": "a***@example.com" },
        { "channel": "whatsapp", "expires_in": 300, "sent_to": "+91••••••1234" }
      ]
    }
  }
}
```
Delivery failure → `502` with user kept `pending`; client can call `resend-otp`.

---

### 5.3 `POST /api/v1/auth/verify-2fa`
- **Auth:** none (uses `user_id` + channel challenge)
- **Body:**
```json
{ "user_id": "a1b2...", "channel": "email", "code": "483921" }
```
- **Processing:** find latest `pending` challenge for `(user_id, channel)` → check expiry (`410`) → check attempts/lock (`429`) → verify OTP (HMAC compare) or TOTP (window ±1) → mark verified → set user flags → activate when both email and WhatsApp are verified → issue JWT on activation.

Response `200` (activated after both required verifications):
```json
{
  "success": true,
  "message": "Verification successful.",
  "data": {
    "channel": "email",
    "verified": true,
    "user_status": "active",
    "remaining_channels": [],
    "access_token": "jwt...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "redirect_url": "/dashboard/student"
  }
}
```
Response `200` (final, activates + JWT):
```json
{
  "success": true,
  "message": "Account activated successfully",
  "data": {
    "channel": "whatsapp",
    "verified": true,
    "user_status": "active",
    "remaining_channels": [],
    "access_token": "<jwt>",
    "token_type": "Bearer",
    "expires_in": 3600,
    "redirect_url": "/dashboard/student"
  }
}
```
Errors: `400` invalid code (attempt++), `404` no active challenge, `410` expired, `429` locked.

---

### 5.4 `POST /api/v1/auth/resend-otp` *(supplementary — needed for UX)*
```json
{ "user_id": "a1b2...", "channel": "email" }
```
- Cooldown 60s (`429`), max 5 resends, regenerates OTP, invalidates previous challenge, re-sends.

### 5.5 `POST /api/v1/auth/login` *(supplementary — returning users)*
```json
{ "email": "arun@example.com", "password": "Arun@12345" }
```
- Only `active` users get a JWT (`403` if pending/disabled). Constant-time verify; generic error message.

### 5.6 TOTP (optional channel)
- `GET /api/v1/auth/totp/setup` *(JWT)* → `{ secret, otpauth_uri }` (secret shown once).
- `POST /api/v1/auth/totp/verify` *(JWT)* → `{ code }` enables TOTP.
- `POST /api/v1/auth/totp/disable` *(JWT, password required)*.

### 5.7 `GET /api/v1/profile`
- **Auth:** Bearer JWT, active user
- Returns user + latest linked resume metadata:
```json
{
  "success": true,
  "data": {
    "id": "a1b2...",
    "full_name": "Arun Kumar",
    "email": "arun@example.com",
    "phone": "+919876543210",
    "status": "active",
    "email_verified": true,
    "whatsapp_verified": true,
    "totp_enabled": false,
    "skills": ["Python", "FastAPI", "React"],
    "experience": "Fresher",
    "qualification": "B.E. Computer Science",
    "resume": { "file_name": "resume.pdf", "parsed_at": "2026-11-11T10:00:00Z" },
    "created_at": "2026-11-11T09:55:00Z"
  }
}
```
Errors: `401` missing/invalid token, `403` inactive account.

### 5.8 `PATCH /api/v1/profile`
- **Auth:** Bearer JWT, active user
- **Body:** any subset (email immutable)
```json
{ "phone": "+919876543211", "skills": ["Python", "FastAPI", "React", "PostgreSQL"] }
```
- Validates fields, updates `users` + linked resume JSONB, returns full updated profile.
- Authorization enforced by `sub` claim; a user can only edit self.

### 5.9 Dashboard
- `GET /api/v1/dashboard/student` *(JWT, active)*:
```json
{
  "success": true,
  "message": "Account activated successfully",
  "data": {
    "user_state": "active",
    "full_name": "Arun Kumar",
    "redirect_url": "/dashboard/student"
  }
}
```
- `GET /dashboard/student` → protected HTML dashboard page.

### 5.10 Endpoint summary
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/api/v1/resume/parse` | none | Parse PDF/DOCX → JSON |
| POST | `/api/v1/auth/register` | none | Create pending user + send OTPs |
| POST | `/api/v1/auth/verify-2fa` | none | Verify a channel; activate + JWT when complete |
| POST | `/api/v1/auth/resend-otp` | none | Resend OTP (supplementary) |
| POST | `/api/v1/auth/login` | none | Login for active users (supplementary) |
| GET | `/api/v1/auth/totp/setup` | JWT | TOTP provisioning (optional) |
| POST | `/api/v1/auth/totp/verify` | JWT | Enable TOTP (optional) |
| GET | `/api/v1/profile` | JWT | View profile |
| PATCH | `/api/v1/profile` | JWT | Update profile |
| GET | `/api/v1/dashboard/student` | JWT | Dashboard payload |
| GET | `/dashboard/student` | JWT/cookie | Dashboard HTML |

---

## 6. Resume parsing design

### 6.1 Text extraction
- **PDF:** `pdfplumber`, concatenate `page.extract_text()`; if empty, fail `422`.
- **DOCX:** `python-docx`, paragraphs + table cell text.
- Normalize whitespace, unify line endings.

### 6.2 Field heuristics
| Field | Strategy |
|---|---|
| Email | regex `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`; first match; lowercase |
| Phone | India + generic regex; strip spaces/dashes; normalize to E.164; prefer numbers near "phone/mobile" |
| Name | first non-empty line that is not email/phone/URL and has 2–4 title-case words; fallback to the original filename (e.g., `Naveen Kumar S - Resume.pdf` → `Naveen Kumar S`) |
| Skills | match against a curated dictionary (software, AI/ML, and engineering/design tools such as AutoCAD, SolidWorks, Creo, CATIA, ANSYS, MATLAB, MS Office); dedupe, canonical casing |
| Experience | "fresher" shortcut; prefer lines mentioning experience/worked/professional, then all non-age lines; regex `(\d+)\s*(?:\+)?\s*(?:years?|yrs?)` and months; age/DOB lines excluded |
| Qualification | first line containing a degree keyword; abbreviations (B.E., B.Tech, M.Tech, B.Sc, MBA, Ph.D) are case-sensitive so common words like "be" are ignored; full words (Bachelor, Master, Diploma) case-insensitive |

Every field is best-effort; missing fields return `null`/`[]` and are added to `warnings`. The UI must let the user correct everything before registering.

### 6.3 Extensibility
`resume_parser.py` exposes pure functions:
```python
extract_text(path: Path, suffix: str) -> str
parse_fields(text: str, filename: str | None = None) -> tuple[dict, list[str]]
name_from_filename(filename: str) -> str | None
```
No DB/IO in field parsing → easy unit tests and future LLM fallback behind the same interface.

---

## 7. OTP & TOTP design

### 7.1 OTP generation & storage
- 6-digit numeric via `secrets.randbelow`.
- Store `HMAC-SHA256(OTP_SECRET, f"{otp}:{challenge_id}")` (never plaintext). HMAC chosen over Argon2 for speed; OTP entropy is low but expiry + attempts + single-use compensate.
- Expiry: 300s (config). Single active challenge per `(user_id, channel, purpose)`; new sends invalidate old.
- Attempts: max 5 → status `locked`; expiry check first.
- Resend cooldown: 60s, max 5.

### 7.2 Verification
- Constant-time compare (`hmac.compare_digest`).
- On success: `status=verified`, `verified_at=now`, set user flag.
- Activation check after each verify: `email_verified` plus `whatsapp_verified`.

### 7.3 TOTP
- `pyotp.random_base32()` secret, encrypted at rest with Fernet (`TOTP_ENCRYPTION_KEY`).
- Provisioning URI: `otpauth://totp/{issuer}:{email}?secret=...&issuer=...`.
- Verify `window=1` (±30s). Optional channel; never blocks activation.

---

## 8. Security

- **Passwords:** Argon2id (`argon2-cffi`), tuned params, rehash-on-verify if needed.
- **JWT:** HS256, `SECRET_KEY` from env, access 60 min, claims `sub`, `role=student`, `status`, `iat`, `exp`, `jti`; algorithm pinned on decode; no PII in payload.
- **Auth dependency:** decode → load user → require `active` for profile/dashboard.
- **Duplicates:** one email = one login; DB unique constraints on email/phone + pre-check (`409`).
- **Uploads:** extension + MIME + magic bytes + size cap; randomized stored filename; outside static web root; no path traversal.
- **Enumeration:** generic auth errors where appropriate.
- **Rate limiting:** `slowapi` on parse/register/verify/resend (documented as recommended).
- **CORS:** restricted to UI origin in non-dev.
- **Secrets:** `.env` only; `.env` + `uploads/` gitignored.
- **TOTP secret:** encrypted; never returned after enrollment.

---

## 9. Configuration (`.env.example`)

```env
APP_ENV=development
APP_NAME=AI Resume Parser
API_V1_PREFIX=/api/v1
LOG_LEVEL=INFO

SECRET_KEY=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

OTP_SECRET=change-me
OTP_EXPIRE_SECONDS=300
OTP_MAX_ATTEMPTS=5
OTP_RESEND_COOLDOWN_SECONDS=60

TOTP_ISSUER=AIResumeParser
TOTP_ENCRYPTION_KEY=change-me-fernet-key

DATABASE_URL=postgresql+asyncpg://resume:resume@localhost:5432/resume_db

UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_MB=5

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM=you@gmail.com

WHATSAPP_API_URL=https://graph.facebook.com/v25.0
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_ACCESS_TOKEN=your-permanent-token
WHATSAPP_OTP_TEMPLATE=otp_verification
```

### Docker Compose (optional)
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: resume
      POSTGRES_PASSWORD: resume
      POSTGRES_DB: resume_db
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U resume -d resume_db"]
      interval: 5s
      retries: 10
volumes:
  pgdata:
```

---

## 10. Complete data flow

```
1. UI uploads resume
   → POST /resume/parse
   → save file + user_resumes row (user_id NULL)
   → return { resume_id, parsed fields }

2. UI autofills registration form with parsed fields (editable)
   → user reviews/corrects, sets password

3. POST /auth/register { profile..., resume_id }
   → validate + duplicate check
   → Argon2id hash password
   → create user status=pending
   → link resume.user_id
   → create email and WhatsApp challenges
   → send both OTPs (Gmail SMTP + WhatsApp Cloud API)
   → return challenges (no JWT)

4. POST /auth/verify-2fa { user_id, channel=email|whatsapp, code }
   → verify each channel → email_verified=true / whatsapp_verified=true
   → activate after both verifications
   → activation rule met → status=active
   → issue JWT + redirect_url=/dashboard/student

6. Client stores JWT
   → GET /profile (autofill/correct again)
   → PATCH /profile (update)

7. GET /dashboard/student (HTML) / GET /api/v1/dashboard/student (JSON)
   → authenticated student dashboard
```

### State machine
```
pending ──(email verified)──> active
pending ──(expired/locked)──> pending (resend / retry)
active  ──(admin)──────────> disabled
```

---

## 11. Day-by-day execution plan

### Day 1 — Foundation + parsing
1. Scaffold folders, `requirements.txt`, `.env.example`, `.gitignore`, `docker-compose.yml`.
2. `core/config.py` (Pydantic Settings), `db/session.py`, models + enums.
3. Alembic init + first migration; `docker compose up -d db`; verify tables.
4. `services/resume_parser.py` (text extraction + heuristics) with unit tests.
5. `services/resume_service.py` + `POST /resume/parse` + validation/error handling.
6. Verify with sample PDF and DOCX.

### Day 2 — Registration + 2FA + JWT
1. `core/security.py` (Argon2id + JWT).
2. `POST /auth/register` + duplicate checks + resume linking.
3. `otp_service.py` (generate/hash/expiry/attempts/resend).
4. `email_service.py` (Gmail SMTP) + `whatsapp_service.py` (Meta Cloud API) adapters.
5. `POST /auth/verify-2fa` + activation + JWT issuance.
6. `POST /auth/resend-otp`, `POST /auth/login`.
7. Optional TOTP setup/verify.

### Day 3 — Profile + dashboard + UI + testing
1. `GET/PATCH /profile` with JWT auth + authorization.
2. `GET /dashboard/student` (HTML) + `GET /api/v1/dashboard/student` (JSON).
3. Company career-site UI (`/` → `/apply` → `/apply/details` → `/apply/password` → `/verify` → `/dashboard/student`).
4. End-to-end tests + Postman collection + README.
5. Final verification against the deliverable checklist.

---

## 12. Testing plan

### Unit
- Parser: each field on varied sample resumes; missing fields; malformed docs.
- Security: Argon2id hash/verify; JWT create/decode/expiry/tamper.
- OTP: generate, hash compare, expiry, attempts/lock, resend cooldown.

### Integration (pytest + httpx AsyncClient, test Postgres)
| Test | Expected |
|---|---|
| Upload valid PDF/DOCX | 200 + parsed JSON |
| Upload unsupported/oversize | 415 / 413 |
| Register valid | 201 pending + challenges |
| Register duplicate email | 409 |
| Register duplicate phone | 409 |
| Register invalid email/weak password | 422 |
| Verify wrong OTP | 400, attempt++ |
| Verify expired OTP | 410 |
| Verify email and WhatsApp | pending → active + JWT |
| Profile without JWT | 401 |
| Profile with JWT | 200 |
| PATCH profile | 200 updated |
| Dashboard active | 200 + redirect |
| Dashboard pending | 403 |

### E2E
Upload → autofill → register → verify email and WhatsApp → JWT → profile GET/PATCH → dashboard.

---

## 13. Dependencies (proposed `requirements.txt`)

```
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
asyncpg
alembic
pydantic
pydantic-settings
email-validator
python-multipart
argon2-cffi
pwdlib[argon2]
pyjwt
pdfplumber
python-docx
pyotp
cryptography
aiosmtplib
httpx
jinja2
itsdangerous
slowapi
python-dotenv
pytest
pytest-asyncio
```

> Pin versions after confirming Python 3.14 compatibility; fall back to Python 3.12 venv if needed.

---

## 14. Deliverable checklist (from task doc)

- [ ] PDF + DOCX upload and parsing
- [ ] Extract name, email, phone, skills, experience (qualification extra)
- [ ] Structured JSON response
- [ ] Registration validation + Argon2id hashing + staged user
- [ ] Email OTP (mandatory, real Gmail SMTP)
- [ ] WhatsApp OTP (mandatory, Meta WhatsApp Cloud API)
- [ ] Browser TOTP (optional)
- [ ] OTP hash + expiry + attempts
- [ ] Account activation only after mandatory verification
- [ ] JWT issuance + validation
- [ ] Protected profile GET/PATCH
- [ ] Dashboard routing payload + page
- [ ] Minimal HTML UI
- [ ] Postman/cURL end-to-end tests
- [ ] README with setup + run instructions

---

## 15. Open questions / notes for trainer
1. Confirm Email and WhatsApp mandatory, TOTP optional (current policy).
2. Confirm whether `email` is editable via PATCH (blueprint: immutable; phone/skills/etc. editable).
3. Confirm acceptable OTP expiry (300s) and attempt limits (5) if trainer has a preference.
4. Meta WhatsApp requires an **approved authentication template** — confirm template name/approval status.
5. Confirm whether a login endpoint is expected (added as supplementary).
6. Confirm resume storage policy (local disk for dev; cloud later).
