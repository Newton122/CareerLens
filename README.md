# CareerLens
# AI Job Intelligence

A simple AI-powered CV and job description analyzer built with FastAPI, Python, and a rule-based matching engine.

## Stack

- Next.js (frontend)
- FastAPI (backend API)
- PostgreSQL (future persistence)
- Google GenAI (future extraction and explanation)
- ML / embeddings / similarity scoring
- File storage for CV uploads

## MVP goals

- Upload a CV PDF
- Paste a job description
- Extract CV text
- Compare skills and experience
- Return a match score plus recommendations

## Run locally

```bash
cd ai-job-intelligence
uv sync
source .venv/bin/activate
uv run python -m ai_job_intelligence.main
```

Then open:

- http://127.0.0.1:8000/docs

## Project layout

```text
src/
  ai_job_intelligence/
    __init__.py
    config.py
    main.py
    schemas.py
    services/
      __init__.py
      pdf_parser.py
```
