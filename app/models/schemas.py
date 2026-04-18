"""
app/models/schemas.py
All Pydantic models used across the agent pipeline.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Input models
# ─────────────────────────────────────────────

class CandidateProfile(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    summary: str
    skills: list[str]
    experience: list[ExperienceEntry]
    education: list[EducationEntry]
    certifications: list[str] = []
    languages: list[str] = []
    raw_resume_text: str = ""


class ExperienceEntry(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    start_date: str
    end_date: str = "Present"
    bullets: list[str]


class EducationEntry(BaseModel):
    degree: str
    institution: str
    year: str
    gpa: Optional[str] = None


class PipelineRequest(BaseModel):
    job_url: Optional[str] = None
    job_description_text: Optional[str] = None
    candidate_profile: CandidateProfile
    enable_critic_loop: bool = True
    generate_email: bool = True


# ─────────────────────────────────────────────
# Agent output models
# ─────────────────────────────────────────────

class JobAnalysis(BaseModel):
    job_title: str
    company_name: str
    company_description: str
    required_skills: list[str]
    preferred_skills: list[str]
    experience_level: str          # junior / mid / senior / lead
    experience_years: Optional[str] = None
    responsibilities: list[str]
    keywords: list[str]            # ATS-critical keywords
    hidden_expectations: list[str] # implicit requirements
    tech_stack: list[str]
    soft_skills: list[str]
    company_culture_hints: list[str]
    salary_range: Optional[str] = None
    remote_policy: Optional[str] = None
    raw_text: str = ""


class ProfileMatch(BaseModel):
    overall_score: int             # 0–100
    skill_match_score: int
    experience_match_score: int
    education_match_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    transferable_skills: list[str]
    relevant_experience: list[str] # selected experience bullets
    gaps_summary: str
    strengths_summary: str
    recommendation: str            # apply / apply-with-note / skip


class TailoredResume(BaseModel):
    markdown_content: str
    docx_path: Optional[str] = None
    keywords_included: list[str]
    keywords_missing: list[str]
    ats_score_estimate: int        # estimated ATS pass score 0–100
    version_id: str


class CoverLetter(BaseModel):
    markdown_content: str
    docx_path: Optional[str] = None
    word_count: int
    tone: str                      # professional / conversational / enthusiastic
    version_id: str


class ApplicationEmail(BaseModel):
    subject: str
    body: str
    attachments_note: str


class CritiqueResult(BaseModel):
    target: str                    # "resume" or "cover_letter"
    score: int                     # 0–10
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    revised_content: Optional[str] = None


# ─────────────────────────────────────────────
# Pipeline result
# ─────────────────────────────────────────────

class PipelineResult(BaseModel):
    application_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    job_analysis: JobAnalysis
    profile_match: ProfileMatch
    tailored_resume: TailoredResume
    cover_letter: CoverLetter
    application_email: Optional[ApplicationEmail] = None
    resume_critique: Optional[CritiqueResult] = None
    cover_letter_critique: Optional[CritiqueResult] = None
    total_processing_time_seconds: float = 0.0
    status: str = "completed"
    errors: list[str] = []


# ─────────────────────────────────────────────
# Memory / feedback models
# ─────────────────────────────────────────────

class ApplicationRecord(BaseModel):
    application_id: str
    job_title: str
    company_name: str
    job_url: Optional[str] = None
    match_score: int
    status: str = "pending"        # pending / applied / interview / offer / rejected
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None


class FeedbackRequest(BaseModel):
    application_id: str
    outcome: str                   # interview / offer / rejected / no_response
    notes: Optional[str] = None


# ─────────────────────────────────────────────
# API response wrappers
# ─────────────────────────────────────────────

class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: str = ""
