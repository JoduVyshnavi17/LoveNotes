# NoteMind AI — Master Web Application Source

NoteMind AI reconstructs handwritten notes from notebook photos and scanned PDFs. It keeps the raw OCR, faithful reconstruction, AI-organized notes, and accepted AI additions distinct. It is intentionally **not** an LMS, quiz application, student-management platform, meeting assistant, or generic chatbot.

## Included
- React + Vite responsive web workspace.
- FastAPI backend and SQLAlchemy data model.
- Argon2 password hashing and signed JWT access tokens.
- User-owned documents, page records, suggestions, and revision snapshots.
- Multi-file image/PDF upload, extension/signature checks, size limits, generated storage names.
- PDF page rasterization and image preprocessing.
- OCR provider abstraction: local Tesseract or optional OpenAI vision.
- Faithful / Enhanced / Complete processing modes.
- Cautious AI gap suggestions with category, rationale, evidence, confidence, and accept/reject state.
- Editable faithful and enhanced note fields.
- PDF, DOCX and TXT export; archive, restore, delete, search, page reorder API.
- Docker Compose, env examples, architecture and production checklist.

## Run on Windows
Install Python 3.11+, Node.js 20+, and (for local OCR) Tesseract OCR.

Backend PowerShell:
```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env: set a long random JWT_SECRET_KEY. Set OPENAI_API_KEY for AI features.
uvicorn app.main:app --reload
```

Frontend in a second PowerShell terminal:
```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open `http://localhost:5173`; API docs are at `http://127.0.0.1:8000/docs`.

## Run on macOS/Linux
```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env before starting.
uvicorn app.main:app --reload
```
In another terminal:
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Docker
```bash
cp backend/.env.example backend/.env
# Edit backend/.env and set JWT_SECRET_KEY. Add OPENAI_API_KEY if desired.
docker compose up --build
```
Frontend: `http://localhost:8080`; API docs: `http://localhost:8000/docs`.

## OCR and AI configuration
- `OCR_PROVIDER=tesseract`: local Tesseract. It is primarily optimized for printed text and may perform poorly on cursive handwriting.
- `OCR_PROVIDER=openai_vision`: uses `OPENAI_API_KEY` and `AI_MODEL` for image transcription.
- AI organization and gap suggestions require `OPENAI_API_KEY` regardless of OCR provider.
- Never place the OpenAI key in the frontend environment.
- The model output is not guaranteed correct. Verify all transcription and suggestions against the original pages.

## API routes
- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `POST /api/documents/upload`, `GET /api/documents`, `GET /api/documents/{id}`
- `POST /api/documents/{id}/process?mode=faithful|enhanced|complete`
- `PATCH /api/documents/{id}/content`
- `POST /api/documents/{id}/suggestions?depth=basic|detailed|comprehensive`
- `PATCH /api/suggestions/{id}`
- `POST /api/documents/{id}/pages/reorder`
- `POST /api/documents/{id}/archive`, `POST /api/documents/{id}/restore`, `DELETE /api/documents/{id}`
- `POST /api/documents/{id}/export?format=pdf|docx|txt`
- `GET /api/documents/{id}/revisions`, `GET /api/documents/search?q=...`

Protected routes use `Authorization: Bearer <access_token>`.

## Known work still required before public production launch
This is the master application code foundation, not a claim of audited production readiness. Add Alembic migrations, refresh-token rotation/revocation, email verification/password reset, rate limiting, malware scanning, private cloud object storage, async job workers, robust source-region traceability, crop/deskew UI, comprehensive tests, monitoring, backup/restore, and a security/privacy review. See `docs/PRODUCTION_CHECKLIST.md`.


## LoveNotes account data and MySQL setup
1. Install MySQL Server and start the MySQL service.
2. In MySQL Workbench or the MySQL command line, run: `CREATE DATABASE lovenotes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
3. In `backend/.env`, set `DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/lovenotes` (URL-encode special characters in the password).
4. Install updated backend dependencies with `pip install -r requirements.txt`, then restart FastAPI. The SQLAlchemy tables are created on startup for a fresh database.

Account profiles are stored in the `users` table (`full_name`, `email`, password hash, purpose, education level, created_at). Uploaded notebook metadata is in `documents`; original uploaded page paths and page OCR/reconstruction are in `pages`; AI suggestions are in `suggestions`; edit snapshots are in `revisions`; generated summaries/quizzes are in `study_materials`. Every document query is scoped to its authenticated owner. Data does not expire after 100 days; it remains available until the account/document is deleted. Back up both the MySQL database and the `storage/uploads` folder.

For same-language OCR, set `OCR_PROVIDER=openai_vision` and configure `OPENAI_API_KEY`. Tesseract mode uses `OCR_LANGUAGE=eng` by default and only recognizes languages whose Tesseract language data is installed (for example `tel`, `hin`, `eng`). AI reconstruction, suggestions, summaries and quizzes are instructed to stay in the source language.
