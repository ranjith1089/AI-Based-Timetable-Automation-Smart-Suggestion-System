# AI-Based Timetable Automation & Smart Suggestion System

This repository includes a baseline implementation across:
- **Frontend**: React + Vite
- **Backend**: FastAPI
- **Database**: PostgreSQL schema
- **Testing**: Pytest API tests

## Environment Variables
Environment configuration is included through `.env.example`.

```bash
cp .env.example .env
```

Key variables:
- `API_HOST`, `API_PORT`, `API_TITLE`, `ALLOWED_ORIGINS`
- `VITE_APP_TITLE`, `VITE_API_BASE_URL`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DB_PORT`
- `FRONTEND_PORT`, `BACKEND_PORT`

## Project Structure
- `frontend/` - Coordinator dashboard scaffold
- `backend/` - Tenant-aware API scaffold
- `database/schema.sql` - Multi-tenant relational schema
- `IMPLEMENTATION_PLAN.md` - Product and delivery plan

## Backend Run
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000} --reload
```

## Backend Tests
```bash
cd backend
source .venv/bin/activate
pytest -q
```

## Frontend Run
```bash
cd frontend
npm install
npm run dev
```

## Docker Compose Run
```bash
docker compose up --build
```
