"""
app/main.py
FastAPI application entry point.

Endpoints:
  POST /api/v1/analyze          — Run full pipeline
  GET  /api/v1/applications     — List past applications
  GET  /api/v1/applications/:id — Get single application
  POST /api/v1/feedback         — Submit outcome feedback
  GET  /api/v1/stats            — Memory + outcome stats
  GET  /api/v1/health           — Health check
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from loguru import logger

from app.models.schemas import (
    PipelineRequest, PipelineResult, FeedbackRequest,
    APIResponse, CandidateProfile
)
from app.orchestrator import Orchestrator
from app.memory.database import ApplicationDatabase

load_dotenv()


# ── Lifespan: startup / shutdown ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Job Application Agent API...")
    db = ApplicationDatabase()
    await db.init()
    app.state.orchestrator = Orchestrator()
    app.state.db = db
    logger.info("✓ All services initialized")
    yield
    logger.info("Shutting down...")


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Job Application Agent",
    description="Multi-agent system for tailored resume + cover letter generation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "model": os.getenv("LLM_MODEL", "unknown")}


@app.post("/api/v1/analyze", response_model=PipelineResult)
async def analyze(request: PipelineRequest):
    """
    Run the full job application pipeline.

    Accepts either job_url (will be scraped) or job_description_text.
    Returns complete application package: analysis, match score,
    tailored resume, cover letter, and email draft.
    """
    if not request.job_url and not request.job_description_text:
        raise HTTPException(400, "Provide either job_url or job_description_text")

    orchestrator: Orchestrator = app.state.orchestrator

    try:
        result = await orchestrator.run(request)
        return result
    except Exception as e:
        logger.exception(f"Pipeline error: {e}")
        raise HTTPException(500, f"Pipeline failed: {str(e)}")


@app.get("/api/v1/applications")
async def list_applications(limit: int = 20):
    """List recent job applications."""
    db: ApplicationDatabase = app.state.db
    apps = await db.list_applications(limit=limit)
    return APIResponse(success=True, data=apps, message=f"{len(apps)} applications found")


@app.get("/api/v1/applications/{application_id}")
async def get_application(application_id: str):
    """Retrieve a single application by ID."""
    db: ApplicationDatabase = app.state.db
    app_data = await db.get_application(application_id)
    if not app_data:
        raise HTTPException(404, f"Application {application_id} not found")
    return APIResponse(success=True, data=app_data)


@app.post("/api/v1/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit success/failure feedback for an application.
    Outcome: interview | offer | rejected | no_response
    This updates the memory module to improve future recommendations.
    """
    db: ApplicationDatabase = app.state.db
    orchestrator: Orchestrator = app.state.orchestrator

    ok = await db.record_feedback(
        feedback.application_id,
        feedback.outcome,
        feedback.notes,
    )
    if not ok:
        raise HTTPException(404, f"Application {feedback.application_id} not found")

    # Update vector store outcome
    orchestrator.memory.update_outcome(feedback.application_id, feedback.outcome)

    return APIResponse(
        success=True,
        message=f"Feedback recorded: {feedback.outcome}",
    )


@app.get("/api/v1/stats")
async def get_stats():
    """Get memory and outcome statistics."""
    db: ApplicationDatabase = app.state.db
    orchestrator: Orchestrator = app.state.orchestrator

    outcome_stats = await db.get_outcome_stats()
    memory_stats = orchestrator.memory.get_stats()

    return APIResponse(success=True, data={
        "outcomes": outcome_stats,
        "memory": memory_stats,
    })


@app.get("/api/v1/download/{filename}")
async def download_file(filename: str):
    """Download a generated document (resume or cover letter)."""
    import re
    # Sanitize filename — only allow safe characters
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", filename):
        raise HTTPException(400, "Invalid filename")

    data_dir = os.getenv("DATA_DIR", "./data")
    filepath = os.path.join(data_dir, "applications", filename)

    if not os.path.exists(filepath):
        raise HTTPException(404, "File not found")

    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_DEBUG", "true").lower() == "true",
    )
