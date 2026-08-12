# SpecGuard AI

AI-powered software requirement and security assurance engine.

This repository contains:

- `backend/` - FastAPI API and LangGraph analysis workflow.
- `frontend/` - Next.js TypeScript UI.
- `supabase/migrations/` - PostgreSQL/pgvector schema.
- `docs/` - product, architecture, API, AI, and database specifications.

## Run Locally

Backend:

```bash
cp .env.example .env
source .venv/bin/activate
uvicorn backend.app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Current MVP

The first implementation follows the documented pipeline with deterministic analyzers and LangGraph orchestration. It stores local state in `data/state` so the app works before Supabase credentials are connected. The Supabase schema is ready for the next persistence pass.
