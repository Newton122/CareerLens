# CareerLens

An AI-powered career platform: job seekers upload a CV, see which skills it
actually evidences, get matched to jobs, and get specific advice on what to
learn next; employers post jobs, search candidates by meaning rather than
keywords, and run interviews and messaging; admins oversee the platform.

**New here? Read [PROJECT_GUIDE.md](PROJECT_GUIDE.md)**: a complete explanation of every part of the project, how to run it, and how to deploy it.

## Stack

- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS (deployed on Vercel)
- **Backend:** FastAPI, SQLAlchemy, Alembic (deployed on Render)
- **Database:** PostgreSQL
- **AI:** rule-based skill extraction, `all-MiniLM-L6-v2` embeddings on ONNX
  Runtime for semantic matching, and optional Google Gemini

## Run locally

```bash
# Backend (needs PostgreSQL; set DATABASE_URL in ai-job-intelligence/.env)
cd ai-job-intelligence
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn ai_job_intelligence.main:app --app-dir src --reload --port 8000

# Frontend, in a second terminal
cd ai-job-intelligence/frontend
npm install && npm run dev          # http://localhost:3001
```

## Test

```bash
cd ai-job-intelligence && .venv/bin/python -m pytest -q     # backend
cd ai-job-intelligence/frontend && npm run lint && npm run build
# Browser tests: see the comment at the top of frontend/playwright.config.ts
```
