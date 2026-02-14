# AI-Based Timetable Automation & Smart Suggestion System

This repository now includes a baseline implementation across:
- **Frontend**: React + Vite
- **Backend**: FastAPI
- **Database**: PostgreSQL schema
- **Testing**: Pytest API tests

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
uvicorn app.main:app --reload
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
