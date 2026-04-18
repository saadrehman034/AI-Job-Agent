# AI Job Application Agent

A production-ready, multi-agent system that autonomously analyzes job postings, tailors resumes and cover letters, and assists with job applications — powered by Anthropic Claude.

## Architecture

```
User Input (Resume + Job URL)
        │
        ▼
┌─────────────────────────────────────────────┐
│              Orchestrator                   │
│  (manages pipeline, retries, state)         │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Job Analyzer │───▶│Profile Matcher│───▶│ Resume Gen   │───▶│ Cover Letter │───▶│  App Agent   │
│              │    │              │    │              │    │   Generator  │    │ (email/form) │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │                   │                   │
       └───────────────────┴───────────────────┴───────────────────┴───────────────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │   Memory Module     │
                                    │ (FAISS + SQLite)    │
                                    └─────────────────────┘
```

## Features

- **Job Analyzer Agent** — extracts required skills, keywords, seniority, hidden expectations
- **Profile Matcher Agent** — scores your resume against job requirements (match %)
- **Resume Generator Agent** — ATS-optimized, keyword-rich, tailored resume in Markdown + DOCX
- **Cover Letter Agent** — personalized, non-generic cover letter with company-specific tone
- **Application Agent** — drafts professional application email; optional Playwright form fill
- **Memory Module** — stores past applications, learns from success/failure signals via FAISS
- **Critic Loop** — agents review each other's output before finalization
- **Streamlit UI** — upload resume, paste job URL, generate and download everything

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Anthropic Claude (claude-sonnet-4-20250514) |
| Backend API | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Agent Framework | Custom (LangChain-compatible tool pattern) |
| Memory | FAISS + SQLite |
| Document generation | python-docx, markdown |
| Browser automation | Playwright (optional) |
| Email | SMTP / smtplib |

## Quick Start

```bash
# 1. Clone and enter project
cd ai_job_agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
playwright install chromium   # for Application Agent

# 4. Configure environment
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY

# 5. Run backend API
uvicorn app.main:app --reload --port 8000

# 6. Run Streamlit UI (new terminal)
streamlit run ui/streamlit_app.py
```

Open http://localhost:8501 in your browser.

## Project Structure

```
ai_job_agent/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── orchestrator.py          # Master pipeline controller
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py        # Abstract base with retry logic
│   │   ├── job_analyzer.py      # Agent 1
│   │   ├── profile_matcher.py   # Agent 2
│   │   ├── resume_generator.py  # Agent 3
│   │   ├── cover_letter.py      # Agent 4
│   │   └── application_agent.py # Agent 5
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── vector_store.py      # FAISS wrapper
│   │   └── database.py          # SQLite application log
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── web_scraper.py       # Job post scraper
│   │   ├── document_writer.py   # PDF/DOCX output
│   │   └── email_sender.py      # SMTP email tool
│   └── models/
│       ├── __init__.py
│       └── schemas.py           # Pydantic models
├── ui/
│   └── streamlit_app.py         # Streamlit frontend
├── data/
│   ├── applications/            # Saved application data
│   └── faiss_index/             # Vector memory store
├── tests/
│   └── test_agents.py
├── .env.example
├── requirements.txt
└── README.md
```

## Environment Variables

See `.env.example` for all options.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/analyze` | Full pipeline run |
| GET | `/api/v1/applications` | List past applications |
| POST | `/api/v1/feedback` | Submit success/failure signal |
| GET | `/api/v1/health` | Health check |

## Improving Results

- Add more past applications via `/api/v1/feedback` — the memory module learns
- Provide rich candidate profiles with quantified achievements
- Use the critic loop flag `--critique` for a second AI pass on outputs

## Bonus Features

- **Match Score** — 0–100% compatibility score with breakdown by category
- **ATS Keywords** — highlights missing high-value terms
- **Critic Loop** — Resume Gen and Cover Letter agents review each other
- **Feedback Loop** — mark applications as success/rejection; system adapts

## License

MIT
