# Campus Assistant — College Placement Management

Vue 3 + Tailwind CSS (frontend) · FastAPI + SQLAlchemy + MySQL/MariaDB (backend).
Three roles: **Student**, **Faculty / Placement Officer**, **Admin**, plus an AI assistant.

```
frontend/   Vue 3 (JavaScript), Vite, Vue Router, Pinia, axios, Tailwind CSS 4, Chart.js
backend/    FastAPI, SQLAlchemy 2, Alembic migrations, PyMySQL, pytest
```

## 1. Prerequisites
Node.js 20.19+, Python 3.11+, MySQL 8 or MariaDB 10.6+.

## 2. Database (once)
```bash
sudo mysql <<'SQL'
CREATE DATABASE campus_assistant CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'campus_app'@'localhost' IDENTIFIED BY 'CHANGE_ME';
GRANT ALL PRIVILEGES ON campus_assistant.* TO 'campus_app'@'localhost';
SQL
```

## 3. Backend
```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # then edit: DATABASE_URL password, SECRET_KEY, JWT_SECRET_KEY, SEED_DEMO_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # run twice for the two keys
alembic upgrade head                 # create the tables
python -m app.cli seed-reference     # roles, permissions, departments, policies
python -m app.cli seed-demo          # optional fictional demo data
uvicorn app.main:app --reload --port 8000
```
API docs (development only): http://localhost:8000/api/docs

## 4. Frontend (second terminal)
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api to port 8000)
```

## Demo accounts (password = SEED_DEMO_PASSWORD)
| Role | E-mail |
|---|---|
| Student | student@campus.demo |
| New student (onboarding) | newstudent@campus.demo |
| Faculty | faculty@campus.demo |
| Admin | admin@campus.demo |

## AI assistant (optional)
Add to `backend/.env`, then restart the API:
```
LLM_PROVIDER=anthropic          # or openai | gemini | mistral | groq | deepseek | openrouter | together | ollama | openai_compatible
LLM_API_KEY=<your key>          # not needed for ollama
LLM_MODEL=                      # optional for anthropic (default claude-opus-5-5); required for the others
```
Check it with `python -m app.cli assistant-check --ping`. Without a key the assistant page says it is not configured.
The model never touches the database: it calls ~37 permission-checked tools, and every change it prepares
must be confirmed by the user on a card (the server re-validates the rules at that moment).

## Useful commands (backend)
```bash
python -m app.cli seed-reference        # roles, permissions, departments, default policies (safe to re-run)
python -m app.cli seed-demo             # fictional demo data
python -m app.cli create-user --role admin --email you@college.edu --name "Your Name" --code ADM001
python -m app.cli assistant-check --ping
python -m app.cli assistant-purge       # delete conversations archived longer than ASSISTANT_RETENTION_DAYS (run daily)
```
E-mail is not set up: password-reset and invitation links are printed in the API server log in development.
Uploaded documents are stored under `backend/uploads/` (`UPLOAD_DIR`).

## Tests
```bash
cd backend && pytest
```
