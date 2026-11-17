# AI-Powered Resume Parser & Job Application Pipeline

Company career-site flow for a single open role: browse the job, upload a resume,
auto-fill an editable application (education, projects, internships, experience),
register with Argon2id-hashed passwords, verify identity via **Email OTP** and
**WhatsApp OTP** (both mandatory) plus optional **Browser TOTP**, then track the
application from the candidate dashboard.

The sample role is configured in `app/core/jobs.py` (`Nexora Technologies` · Graduate Software
Engineer · Chennai).

## Application flow

1. `/` — job landing page and role overview.
2. `/apply` — upload a PDF/DOCX resume; the parser fills the application.
3. `/apply/details` — review/edit personal details plus structured education,
   projects, internships, and experience lists.
4. `/apply/password` — set a password and submit the application.
5. `/verify` — verify the email and WhatsApp OTPs.
6. `/dashboard/student` — application dashboard with status and full profile.

Legacy `/upload` and `/register` URLs redirect to `/apply`.

## Stack

FastAPI · PostgreSQL 16 · SQLAlchemy Async · Pydantic v2 · Argon2id (`pwdlib`) ·
PyJWT · pdfplumber · python-docx · Gmail SMTP · Meta WhatsApp Cloud API.

## Quick start

### Option A — Native PostgreSQL (no Docker)

```powershell
# 1. Install PostgreSQL (16 or newer; verified on 18.6)
winget install PostgreSQL.PostgreSQL.16

# 2. Create the role + database (run as the postgres superuser)
#    Add PostgreSQL's bin folder to PATH first, e.g.
#    C:\Program Files\PostgreSQL\16\bin
psql -U postgres -f scripts/init_postgres.sql

# 3. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure secrets
Copy-Item .env.example .env
# edit .env — the default DATABASE_URL already matches the role/db above

# 6. Existing databases only: apply the application-field migration
alembic upgrade head

# 7. Run the app (creates tables automatically in development)
uvicorn app.main:app --reload
```

The default `.env` connection string is:

```
postgresql+asyncpg://resume:resume@localhost:5432/resume_db
```

If you use different credentials, update `DATABASE_URL` accordingly. The role
password must match the one in `scripts/init_postgres.sql` (default `resume`);
if they differ, run `ALTER ROLE resume WITH PASSWORD '<your-password>';`.

### Option B — Docker PostgreSQL (optional)

```powershell
docker compose up -d db
```

Then follow steps 3–6 above. The Docker service uses the same credentials.

Open:

- UI: http://localhost:8000/
- Apply: http://localhost:8000/apply
- Swagger: http://localhost:8000/docs

> Tables are created automatically when `AUTO_CREATE_TABLES=true`. The included
> Alembic migration (`migrations/versions/0001_application_fields.py`) adds the
> application columns to an existing database, and creates the full schema if the
> database is empty.

## API endpoints

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/api/v1/resume/parse` | none | Parse PDF/DOCX → structured JSON |
| POST | `/api/v1/auth/register` | none | Create pending user + send email and WhatsApp OTPs |
| POST | `/api/v1/auth/verify-2fa` | none | Verify email/WhatsApp; activate + JWT when both pass |
| POST | `/api/v1/auth/resend-otp` | none | Resend OTP (cooldown enforced) |
| POST | `/api/v1/auth/login` | none | Login for active users |
| GET | `/api/v1/auth/totp/setup` | JWT | Optional TOTP provisioning |
| POST | `/api/v1/auth/totp/verify` | JWT | Enable TOTP |
| GET | `/api/v1/profile` | JWT | View profile |
| PATCH | `/api/v1/profile` | JWT | Update profile |
| GET | `/api/v1/dashboard/student` | JWT | Dashboard payload |
| GET | `/dashboard/student` | cookie | Dashboard page |

## Verification rules

- Account activates when both `email_verified` and `whatsapp_verified` are true.
- TOTP is optional and never blocks activation.
- OTPs are stored as HMAC-SHA256 hashes, expire after 5 minutes, allow 5 attempts,
  and have a 60-second resend cooldown.

## External service notes

- **Gmail SMTP**: enable 2FA on the account, then create a 16-character App Password.
  Use that as `SMTP_PASSWORD` (not your normal password).
- **Meta WhatsApp Cloud API**: business-initiated messages require an **approved
  template**. This project uses an **Authentication** template named
  `otp_verification` (`en_US`) whose body is `{{1}} is your verification code.`
  Authentication templates expose a "Copy code" button, so the send payload also
  includes a button parameter at index `0`. Set `WHATSAPP_OTP_BUTTON_INDEX=0`
  (or `-1` if your template has no OTP button). Use a **System User** token, or
  exchange a short-lived token for a 60-day token with `META_APP_SECRET`.

## Project layout

See [`docs/BLUEPRINT.md`](docs/BLUEPRINT.md) for the full technical blueprint
(database schema, API contracts, data flow, security design).

```
app/
  core/       config, security, exceptions, logging
  db/         async engine + session
  models/     SQLAlchemy ORM
  schemas/    Pydantic v2 contracts
  routers/    API + HTML routes
  services/   business logic
  templates/  Jinja2 minimal UI
  static/     css/js
```

## Python version

Designed for Python 3.11+. This project was scaffolded and verified on
**Python 3.14.8** with all dependencies installing from wheels. If a dependency
later lacks a wheel for your interpreter, use a 3.12 virtual environment.
