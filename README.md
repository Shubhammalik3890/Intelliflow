# IntelliFlow AI

IntelliFlow AI is an enterprise request automation platform built alongside the existing Edge–Fog–Cloud scheduler in this repository.

The added application includes:

- FastAPI backend with app-managed JWT authentication, database-backed users, role checks, SQLite/PostgreSQL persistence, audit logging, Swagger, and Gemini/mock AI modes.
- React/Vite dashboard for requests, approvals, AI agents, workflows, knowledge documents, and settings.
- Request classification, sentiment, priority, routing, response drafting, supervisor approval, and workflow state.
- PostgreSQL migration; no Supabase Auth or Supabase keys are required. The same schema works with Supabase PostgreSQL via its database URL.
- PDF/TXT knowledge upload and text extraction.
- Railway and Vercel deployment configuration.

## Run IntelliFlow locally

Copy `.env.example` to `.env` in the project root and set `JWT_SECRET`, `GEMINI_API_KEY`, and (if needed) `DATABASE_URL` before starting the backend.

Backend:

```powershell
cd backend
py -3.12 -m venv .venv312
.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (Node.js 20+):

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The backend is documented at `http://localhost:8000/docs`.

Create a key in [Google AI Studio](https://aistudio.google.com/apikey), set `AI_PROVIDER=gemini`, and put it in `GEMINI_API_KEY` in `.env`. `GEMINI_MODEL` defaults to `gemini-3.5-flash-lite` and can be changed to another model enabled for your key. Set a database URL and a random `JWT_SECRET` of at least 32 characters. For example, generate one with:

```powershell
py -c "import secrets; print(secrets.token_urlsafe(48))"
```

The first account registered becomes the initial Admin; subsequent self-registered accounts are Employees. Roles cannot be chosen in the registration request. Passwords are hashed before storage, and the backend issues its own 12-hour JWTs. `AI_PROVIDER=mock` enables explicitly labeled offline demo mode; Gemini errors are reported rather than silently switching to mock. There is no Supabase Auth, Gmail OAuth, or email-sending integration.

Never put database credentials, JWT secrets, or AI provider keys in frontend environment variables or source code.

## Run existing scheduler

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

A one-page Streamlit simulator. Enter a task's CPU, RAM and latency sensitivity; the scheduler tells you whether it can be placed on Edge, Fog or Cloud.

## Run on Windows (VS Code terminal)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

## Placement rules

| Tier | Simulated latency | CPU | RAM |
|---|---:|---:|---:|
| Edge | 5 ms | 4 cores | 8 GB |
| Fog | 20 ms | 8 cores | 16 GB |
| Cloud | 80 ms | 16 cores | 64 GB |

Latency limits: High = 20 ms, Medium = 60 ms, Low = 150 ms. A node must satisfy both the latency limit and the task's remaining CPU/RAM requirements. The eligible node with the lowest latency is selected.

This is a learning simulation only: it does not deploy real VMs or cloud infrastructure.
