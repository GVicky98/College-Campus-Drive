# Campus Assistant — College Placement Management

A web app for running campus placements, with three kinds of users and an AI assistant:

- **Student** — profile, eligible jobs, applications, interviews, offers, reminders, documents.
- **Faculty / Placement Officer** — companies, jobs and drives, students, applicant review, interviews, offers, reports.
- **Admin** — users, roles and permissions, placement policies, departments and courses, audit log, system settings.

| Part | Technology |
|---|---|
| `frontend/` | Vue 3 (JavaScript), Vite, Vue Router, Pinia, axios, Tailwind CSS 4, Chart.js |
| `backend/` | Python FastAPI, SQLAlchemy 2, Alembic migrations, PyMySQL, pytest |
| Database | MySQL 8 or MariaDB 10.6+ |

You need **two terminals** while running it: one for the backend (port 8000) and one for the frontend (port 5173).

---

## 1. Install the tools (once)

| Tool | Version | Check with |
|---|---|---|
| Git | any | `git --version` |
| Node.js (includes npm) | **20.19 or newer** | `node -v` |
| Python | **3.11 or newer** | `python3 --version` (Windows: `python --version`) |
| MySQL or MariaDB | MySQL 8 / MariaDB 10.6+ | `mysql --version` |

### Ubuntu / Debian
```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip mariadb-server
sudo systemctl enable --now mariadb

# Node.js 20 (the version in Ubuntu's own repository is too old)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```
Ubuntu 22.04 ships Python 3.10, which is too old. Use Ubuntu 24.04 (Python 3.12), or install a newer Python:
`sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.12 python3.12-venv`, then use `python3.12` instead of `python3` below.

### macOS (with [Homebrew](https://brew.sh))
```bash
brew install git node python@3.12 mysql
brew services start mysql
```

### Windows 10 / 11
Install these with their installers (keep the default options unless noted):
1. **Git** — https://git-scm.com/download/win
2. **Node.js 20 LTS** — https://nodejs.org (the `.msi` installer)
3. **Python 3.12** — https://www.python.org/downloads/ — **tick “Add python.exe to PATH”** on the first screen
4. **MySQL 8 Community Server** — https://dev.mysql.com/downloads/installer/ — choose “Server only”, set a **root password** and remember it. Tick “Add to PATH” if offered; otherwise use the *MySQL 8.0 Command Line Client* from the Start menu for step 3.

Then open **PowerShell** for every command below. If PowerShell later refuses to run the Python activation script, run this once:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 2. Get the code
```bash
git clone https://github.com/GVicky98/College-Campus-Drive.git
cd College-Campus-Drive
```

---

## 3. Create the database and a database user (once)
Choose your own password instead of `CHANGE_ME` and use the same one in step 4.

Open the MySQL prompt:

| OS | Command |
|---|---|
| Ubuntu (MariaDB) | `sudo mysql` |
| macOS (Homebrew MySQL, no root password by default) | `mysql -u root` |
| Windows | `mysql -u root -p` (enter the root password from the installer), or open *MySQL 8.0 Command Line Client* |

Then paste these lines and press Enter:
```sql
CREATE DATABASE campus_assistant CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'campus_app'@'localhost' IDENTIFIED BY 'CHANGE_ME';
GRANT ALL PRIVILEGES ON campus_assistant.* TO 'campus_app'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

---

## 4. Set up the backend (once)
All backend commands are run **inside the `backend` folder**, with the virtual environment **activated** (your prompt shows `(.venv)`).

### Ubuntu / macOS
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
cp .env.example .env
```

### Windows (PowerShell)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
copy .env.example .env
```

### Edit `backend/.env`
Generate two random secrets (run the command twice and copy each result):
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Open `backend/.env` in any editor (VS Code, Notepad, nano …) and fill in:

| Setting | Value |
|---|---|
| `DATABASE_URL` | `mysql+pymysql://campus_app:CHANGE_ME@127.0.0.1:3306/campus_assistant?charset=utf8mb4` — with your password from step 3 |
| `SECRET_KEY` | the first random value |
| `JWT_SECRET_KEY` | the second random value |
| `SEED_DEMO_PASSWORD` | a password for the demo accounts: 8+ characters with an upper-case letter and a digit, e.g. `Demo@2026` |

If your database password contains `@`, `:` or `/`, write it URL-encoded in `DATABASE_URL` (`@` → `%40`, `:` → `%3A`, `/` → `%2F`).

### Create the tables and data
Same commands on every OS (venv activated, inside `backend`):
```bash
alembic upgrade head                 # creates all tables
python -m app.cli seed-reference     # roles, permissions, departments, academic years, default policies
python -m app.cli seed-demo          # optional: fictional demo users, companies, jobs, applications
```
Instead of the demo data you can create just your own administrator (you will be asked for a password):
```bash
python -m app.cli create-user --role admin --email you@college.edu --name "Your Name" --code ADM001
```

---

## 5. Set up the frontend (once)
In a **second terminal**, from the project folder:
```bash
cd frontend
npm install
```

---

## 6. Run the app (every time)

**Terminal 1 — backend**

| OS | Commands |
|---|---|
| Ubuntu / macOS | `cd backend` → `source .venv/bin/activate` → `uvicorn app.main:app --reload --port 8000` |
| Windows | `cd backend` → `.venv\Scripts\Activate.ps1` → `uvicorn app.main:app --reload --port 8000` |

Leave it running. API documentation: http://localhost:8000/api/docs

**Terminal 2 — frontend** (all OS)
```bash
cd frontend
npm run dev
```
Open **http://localhost:5173** in your browser. The frontend forwards `/api` requests to the backend on port 8000.

Stop either server with **Ctrl + C**.

### Demo accounts (password = your `SEED_DEMO_PASSWORD`)
| Role | E-mail |
|---|---|
| Student | `student@campus.demo` |
| New student (goes through onboarding first) | `newstudent@campus.demo` |
| Faculty / Placement officer | `faculty@campus.demo` |
| Admin | `admin@campus.demo` |

---

## 7. AI assistant (optional)
Add these lines to `backend/.env`, then stop and restart the backend:
```
LLM_PROVIDER=anthropic          # or openai | gemini | mistral | groq | deepseek | openrouter | together | ollama | openai_compatible
LLM_API_KEY=<your key>          # not needed for ollama
LLM_MODEL=                      # optional for anthropic (defaults to claude-opus-5-5); required for every other provider
```
Check the connection: `python -m app.cli assistant-check --ping`. Without a key, the AI Assistant page says it is not configured; the rest of the app works normally.

The model never touches the database: it uses permission-checked tools, and every change it prepares must be confirmed by the user on a card (the server re-checks the rules at that moment). The API key stays on the server and is never sent to the browser.

---

## 8. Useful backend commands
Run inside `backend` with the venv activated:
```bash
python -m app.cli seed-reference        # roles, permissions, departments, default policies (safe to re-run)
python -m app.cli seed-demo             # fictional demo data (skipped if it already exists)
python -m app.cli create-user --role admin --email you@college.edu --name "Your Name" --code ADM001
python -m app.cli assistant-check --ping
python -m app.cli assistant-purge       # delete chat conversations archived longer than ASSISTANT_RETENTION_DAYS
pytest                                  # backend tests (use an in-memory database; your data is untouched)
```
To build the frontend for production: `cd frontend` → `npm run build` (output in `frontend/dist`).

Notes:
- E-mail sending is not set up. Password-reset and invitation links are printed in the **backend terminal** in development.
- Uploaded documents are stored in `backend/uploads/` (change with `UPLOAD_DIR` in `.env`).
- Users are signed out after the idle time set in *Admin → System Settings* (default 60 minutes).

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `Missing required settings: DATABASE_URL, SECRET_KEY …` | Run commands from inside `backend` (that is where `.env` is read) and fill in `.env` (step 4). |
| `Access denied for user 'campus_app'` | The password in `DATABASE_URL` differs from step 3, or contains unencoded `@ : /`. |
| `Can't connect to MySQL server on '127.0.0.1'` | Start the database: Ubuntu `sudo systemctl start mariadb` · macOS `brew services start mysql` · Windows: Services → start **MySQL80**. |
| `python3: command not found` (Windows) | Use `python` instead of `python3`; reinstall Python with “Add to PATH” ticked if needed. |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then try again. |
| `uvicorn` / `alembic` not found | The virtual environment is not activated (step 6). |
| `npm install` fails or Vite complains about the Node version | Install Node.js 20.19 or newer (`node -v`). |
| Port 8000 or 5173 already in use | Stop the other program, or run the backend on another port (`--port 8010`) and start the frontend with `VITE_DEV_PROXY_TARGET=http://127.0.0.1:8010 npm run dev` (Windows PowerShell: `$env:VITE_DEV_PROXY_TARGET="http://127.0.0.1:8010"; npm run dev`). |
| “Too many attempts” on sign-in | Wait one minute; after 5 wrong passwords an account is locked for 15 minutes. |
| Changed `backend/.env` but nothing happened | Stop the backend with Ctrl + C and start it again. |
