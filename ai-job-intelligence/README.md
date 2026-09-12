# CareerLens API (`ai-job-intelligence`)

The FastAPI backend of CareerLens: CV parsing, skill evidence, job matching,
career insights, the CareerLens assistant, and the employer and admin
workflows. The Next.js frontend lives in [`frontend/`](frontend/).

**For a full explanation of how everything works, read
[`../PROJECT_GUIDE.md`](../PROJECT_GUIDE.md).**

## Run locally

Needs Python 3.12 and PostgreSQL.

```bash
cd ai-job-intelligence
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
# create .env with at least DATABASE_URL=postgresql://user:pass@localhost:5432/ai_job_intelligence
.venv/bin/uvicorn ai_job_intelligence.main:app --app-dir src --reload --port 8000
```

Open <http://127.0.0.1:8000/docs> for the interactive API documentation.
Database migrations run automatically at start-up.

## Test

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest -q          # runs in a throwaway PostgreSQL schema
```
