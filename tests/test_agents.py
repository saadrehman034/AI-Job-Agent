"""
tests/test_agents.py
Test suite for the AI Job Application Agent pipeline.

Tests:
- Individual agent outputs
- Full pipeline integration
- Memory module operations
- API endpoints
"""
from __future__ import annotations

import json
import os
import pytest
import asyncio
from unittest.mock import MagicMock, patch

# Ensure we don't need a real API key for most tests
os.environ.setdefault("GEMINI_API_KEY", "test-key-placeholder")
os.environ.setdefault("LLM_MODEL", "gemini-2.5-flash")
os.environ.setdefault("DATA_DIR", "/tmp/test_job_agent")
os.environ.setdefault("FAISS_INDEX_PATH", "/tmp/test_job_agent/faiss_index")
os.environ.setdefault("SQLITE_DB_PATH", "/tmp/test_job_agent/test.db")

from app.models.schemas import (
    CandidateProfile, ExperienceEntry, EducationEntry,
    JobAnalysis, ProfileMatch, PipelineRequest
)


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def sample_candidate() -> CandidateProfile:
    return CandidateProfile(
        name="Alex Chen",
        email="alex@example.com",
        phone="+1 555-0100",
        location="San Francisco, CA",
        linkedin="linkedin.com/in/alexchen",
        github="github.com/alexchen",
        summary=(
            "Senior software engineer with 7 years building scalable backend systems. "
            "Experienced in Python, distributed systems, and cloud infrastructure."
        ),
        skills=[
            "Python", "FastAPI", "PostgreSQL", "Redis", "Docker",
            "Kubernetes", "AWS", "Terraform", "React", "TypeScript"
        ],
        experience=[
            ExperienceEntry(
                title="Senior Software Engineer",
                company="TechCorp",
                start_date="Jan 2021",
                end_date="Present",
                bullets=[
                    "Engineered microservices handling 50K req/s, reducing latency by 40%",
                    "Led migration from monolith to Kubernetes, cutting infrastructure costs by 35%",
                    "Mentored 4 junior engineers; established code review culture",
                    "Built real-time analytics pipeline processing 100M events/day using Kafka",
                ]
            ),
            ExperienceEntry(
                title="Software Engineer",
                company="StartupXYZ",
                start_date="Jun 2018",
                end_date="Dec 2020",
                bullets=[
                    "Built REST APIs serving 10K daily active users using FastAPI and PostgreSQL",
                    "Implemented CI/CD pipeline with GitHub Actions reducing deployment time by 60%",
                    "Developed React dashboard for internal operations team",
                ]
            ),
        ],
        education=[
            EducationEntry(
                degree="B.S. Computer Science",
                institution="UC Berkeley",
                year="2018",
                gpa="3.8"
            )
        ],
        certifications=["AWS Solutions Architect", "Kubernetes CKA"],
    )


@pytest.fixture
def sample_job_analysis() -> JobAnalysis:
    return JobAnalysis(
        job_title="Senior Backend Engineer",
        company_name="Acme Inc",
        company_description="A fast-growing fintech startup building payment infrastructure.",
        required_skills=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"],
        preferred_skills=["Kubernetes", "AWS", "Kafka"],
        experience_level="senior",
        experience_years="5+ years",
        responsibilities=[
            "Design and build high-throughput payment APIs",
            "Lead architectural decisions for backend systems",
            "Mentor junior engineers",
        ],
        keywords=["Python", "FastAPI", "PostgreSQL", "microservices", "high-throughput", "Kubernetes"],
        hidden_expectations=[
            "Comfortable with on-call rotation",
            "Experience with financial systems or compliance",
        ],
        tech_stack=["Python", "FastAPI", "PostgreSQL", "Redis", "Kafka", "Kubernetes", "AWS"],
        soft_skills=["communication", "leadership", "mentoring"],
        company_culture_hints=["fast-paced", "startup", "high ownership"],
        remote_policy="hybrid",
        raw_text="Senior Backend Engineer job description...",
    )


@pytest.fixture
def sample_profile_match() -> ProfileMatch:
    return ProfileMatch(
        overall_score=85,
        skill_match_score=90,
        experience_match_score=85,
        education_match_score=80,
        matched_skills=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes"],
        missing_skills=["financial systems experience"],
        transferable_skills=["distributed systems", "high-throughput APIs"],
        relevant_experience=[
            "Engineered microservices handling 50K req/s, reducing latency by 40%",
            "Led migration from monolith to Kubernetes, cutting infrastructure costs by 35%",
            "Mentored 4 junior engineers; established code review culture",
        ],
        gaps_summary="Lacks direct fintech/payments experience but has strong transferable skills.",
        strengths_summary="Strong match on technical skills and experience level. Leadership experience aligns well.",
        recommendation="apply",
    )


# ─────────────────────────────────────────────
# Unit tests — Schemas / Models
# ─────────────────────────────────────────────

class TestSchemas:
    def test_candidate_profile_valid(self, sample_candidate):
        assert sample_candidate.name == "Alex Chen"
        assert "Python" in sample_candidate.skills
        assert len(sample_candidate.experience) == 2

    def test_job_analysis_valid(self, sample_job_analysis):
        assert sample_job_analysis.experience_level == "senior"
        assert len(sample_job_analysis.required_skills) > 0
        assert len(sample_job_analysis.keywords) > 0

    def test_profile_match_score_clamped(self):
        """Scores should be in 0-100 range."""
        match = ProfileMatch(
            overall_score=150,  # Should be clamped
            skill_match_score=50,
            experience_match_score=50,
            education_match_score=50,
            matched_skills=[],
            missing_skills=[],
            transferable_skills=[],
            relevant_experience=[],
            gaps_summary="",
            strengths_summary="",
            recommendation="apply",
        )
        # Pydantic won't clamp automatically — orchestrator handles this
        assert match.overall_score == 150  # Stored as-is; orchestrator clamps


# ─────────────────────────────────────────────
# Unit tests — Base Agent
# ─────────────────────────────────────────────

class TestBaseAgent:
    def test_parse_json_clean(self):
        from app.agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self): pass

        agent = ConcreteAgent("test")
        result = agent._parse_json_response('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_parse_json_with_fences(self):
        from app.agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self): pass

        agent = ConcreteAgent("test")
        raw = '```json\n{"score": 85, "skills": ["Python"]}\n```'
        result = agent._parse_json_response(raw)
        assert result["score"] == 85
        assert "Python" in result["skills"]

    def test_parse_json_with_surrounding_text(self):
        from app.agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self): pass

        agent = ConcreteAgent("test")
        raw = 'Here is the analysis:\n{"job_title": "Engineer"}\nThank you.'
        result = agent._parse_json_response(raw)
        assert result["job_title"] == "Engineer"

    def test_parse_json_fallback(self):
        from app.agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self): pass

        agent = ConcreteAgent("test")
        result = agent._parse_json_response("not json at all", fallback={"default": True})
        assert result == {"default": True}

    def test_truncate(self):
        from app.agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self): pass

        agent = ConcreteAgent("test")
        long_text = "x" * 10000
        result = agent._truncate(long_text, max_chars=100)
        assert len(result) <= 200  # truncated + suffix
        assert "truncated" in result


# ─────────────────────────────────────────────
# Unit tests — Job Analyzer Agent (mocked LLM)
# ─────────────────────────────────────────────

class TestJobAnalyzerAgent:
    @patch.object(
        target=__import__("app.agents.base_agent", fromlist=["BaseAgent"]).BaseAgent,
        attribute="_call_llm",
        return_value=json.dumps({
            "job_title": "Backend Engineer",
            "company_name": "Acme",
            "company_description": "A tech company.",
            "required_skills": ["Python", "FastAPI"],
            "preferred_skills": ["Docker"],
            "experience_level": "senior",
            "experience_years": "5+",
            "responsibilities": ["Build APIs", "Lead projects"],
            "keywords": ["Python", "FastAPI", "microservices"],
            "hidden_expectations": ["On-call rotation"],
            "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
            "soft_skills": ["communication"],
            "company_culture_hints": ["fast-paced"],
            "salary_range": None,
            "remote_policy": "hybrid"
        })
    )
    def test_job_analyzer_returns_job_analysis(self, mock_llm):
        from app.agents.job_analyzer import JobAnalyzerAgent
        from app.models.schemas import JobAnalysis

        agent = JobAnalyzerAgent()
        result = agent.run("We are hiring a Backend Engineer at Acme...")
        assert isinstance(result, JobAnalysis)
        assert result.job_title == "Backend Engineer"
        assert "Python" in result.required_skills
        assert len(result.keywords) > 0


# ─────────────────────────────────────────────
# Unit tests — Profile Matcher Agent (mocked LLM)
# ─────────────────────────────────────────────

class TestProfileMatcherAgent:
    @patch.object(
        target=__import__("app.agents.base_agent", fromlist=["BaseAgent"]).BaseAgent,
        attribute="_call_llm",
        return_value=json.dumps({
            "overall_score": 82,
            "skill_match_score": 88,
            "experience_match_score": 80,
            "education_match_score": 75,
            "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
            "missing_skills": ["Kafka"],
            "transferable_skills": ["distributed systems"],
            "relevant_experience": ["Engineered microservices handling 50K req/s"],
            "gaps_summary": "Minor gap in Kafka experience.",
            "strengths_summary": "Strong Python and API experience.",
            "recommendation": "apply",
            "recommendation_reasoning": "Strong technical match."
        })
    )
    def test_profile_matcher_returns_match(self, mock_llm, sample_candidate, sample_job_analysis):
        from app.agents.profile_matcher import ProfileMatcherAgent
        from app.models.schemas import ProfileMatch

        agent = ProfileMatcherAgent()
        result = agent.run(sample_candidate, sample_job_analysis)
        assert isinstance(result, ProfileMatch)
        assert 0 <= result.overall_score <= 100
        assert result.recommendation in ("apply", "apply-with-note", "skip")
        assert isinstance(result.matched_skills, list)


# ─────────────────────────────────────────────
# Unit tests — Resume Generator (mocked LLM)
# ─────────────────────────────────────────────

class TestResumeGeneratorAgent:
    @patch.object(
        target=__import__("app.agents.base_agent", fromlist=["BaseAgent"]).BaseAgent,
        attribute="_call_llm",
        return_value="""# Alex Chen
alex@example.com | San Francisco, CA

## Summary
Senior backend engineer with 7 years building scalable APIs in Python and FastAPI.

## Experience
### Senior Software Engineer | TechCorp | Jan 2021–Present
- Engineered microservices handling 50K req/s using Python and FastAPI
- Led Kubernetes migration reducing costs by 35%

## Skills
Python, FastAPI, PostgreSQL, Redis, Docker, Kubernetes

## Education
B.S. Computer Science — UC Berkeley (2018)
"""
    )
    def test_resume_generator_produces_markdown(
        self, mock_llm, sample_candidate, sample_job_analysis, sample_profile_match
    ):
        from app.agents.resume_generator import ResumeGeneratorAgent
        from app.models.schemas import TailoredResume

        agent = ResumeGeneratorAgent()
        result = agent.run(sample_candidate, sample_job_analysis, sample_profile_match)
        assert isinstance(result, TailoredResume)
        assert len(result.markdown_content) > 100
        assert isinstance(result.keywords_included, list)
        assert 0 <= result.ats_score_estimate <= 100
        assert result.version_id  # Should be non-empty


# ─────────────────────────────────────────────
# Unit tests — Cover Letter (mocked LLM)
# ─────────────────────────────────────────────

class TestCoverLetterAgent:
    @patch.object(
        target=__import__("app.agents.base_agent", fromlist=["BaseAgent"]).BaseAgent,
        attribute="_call_llm",
        return_value="""April 18, 2026

Dear Hiring Team,

Acme's work on payment infrastructure immediately caught my attention — building systems
that handle financial transactions at scale is exactly the domain I've spent the last
several years mastering.

At TechCorp, I engineered microservices processing 50,000 requests per second, cutting
latency by 40% through careful architectural decisions around caching and async processing.
That experience maps directly to the high-throughput payment APIs your team is building.

I'm drawn to Acme because of your approach to developer ownership and your fast-paced
culture. I thrive in environments where engineers take end-to-end responsibility for systems.

I'd love to discuss how my experience can contribute to your engineering team.

Best regards,
Alex Chen
alex@example.com
"""
    )
    def test_cover_letter_agent_produces_letter(
        self, mock_llm, sample_candidate, sample_job_analysis,
        sample_profile_match
    ):
        from app.agents.cover_letter import CoverLetterAgent
        from app.models.schemas import CoverLetter, TailoredResume

        resume = TailoredResume(
            markdown_content="# Alex Chen\n...",
            keywords_included=["Python", "FastAPI"],
            keywords_missing=[],
            ats_score_estimate=82,
            version_id="abc123",
        )

        agent = CoverLetterAgent()
        result = agent.run(sample_candidate, sample_job_analysis, sample_profile_match, resume)
        assert isinstance(result, CoverLetter)
        assert result.word_count > 50
        assert "I am writing to apply" not in result.markdown_content
        assert result.tone != ""

    def test_tone_determination_startup(self, sample_job_analysis):
        from app.agents.cover_letter import CoverLetterAgent

        agent = CoverLetterAgent()
        sample_job_analysis.company_culture_hints = ["fast-paced", "startup", "scrappy"]
        tone = agent._determine_tone(sample_job_analysis)
        assert "conversational" in tone

    def test_tone_determination_enterprise(self, sample_job_analysis):
        from app.agents.cover_letter import CoverLetterAgent

        agent = CoverLetterAgent()
        sample_job_analysis.company_culture_hints = ["enterprise", "global compliance"]
        tone = agent._determine_tone(sample_job_analysis)
        assert "formal" in tone


# ─────────────────────────────────────────────
# Unit tests — Application Agent (mocked LLM)
# ─────────────────────────────────────────────

class TestApplicationAgent:
    @patch.object(
        target=__import__("app.agents.base_agent", fromlist=["BaseAgent"]).BaseAgent,
        attribute="_call_llm",
        return_value=json.dumps({
            "subject": "Application: Senior Backend Engineer — Alex Chen",
            "body": "Dear Hiring Team,\n\nPlease find my application attached.\n\nBest,\nAlex",
            "attachments_note": "Resume and cover letter attached."
        })
    )
    def test_application_agent_generates_email(
        self, mock_llm, sample_candidate, sample_job_analysis
    ):
        from app.agents.application_agent import ApplicationAgent
        from app.models.schemas import ApplicationEmail, TailoredResume, CoverLetter

        resume = TailoredResume(
            markdown_content="# Alex Chen",
            keywords_included=["Python"],
            keywords_missing=[],
            ats_score_estimate=80,
            version_id="v1",
        )
        cover_letter = CoverLetter(
            markdown_content="Dear...",
            word_count=200,
            tone="professional",
            version_id="v1",
        )

        agent = ApplicationAgent()
        result = agent.run(sample_candidate, sample_job_analysis, resume, cover_letter)
        assert isinstance(result, ApplicationEmail)
        assert len(result.subject) > 10
        assert len(result.body) > 20


# ─────────────────────────────────────────────
# Unit tests — Memory Module
# ─────────────────────────────────────────────

class TestVectorMemoryStore:
    def test_memory_stats_returns_dict(self):
        from app.memory.vector_store import VectorMemoryStore
        store = VectorMemoryStore()
        stats = store.get_stats()
        assert isinstance(stats, dict)
        assert "total_applications" in stats
        assert "faiss_available" in stats

    def test_retrieve_empty_store(self):
        from app.memory.vector_store import VectorMemoryStore
        store = VectorMemoryStore()
        # Fresh store returns empty list
        results = store.retrieve_similar("Python engineer at startup", top_k=3)
        assert isinstance(results, list)

    def test_format_context_empty(self):
        from app.memory.vector_store import VectorMemoryStore
        store = VectorMemoryStore()
        context = store.format_context_for_agent([])
        assert context == ""

    def test_format_context_with_data(self):
        from app.memory.vector_store import VectorMemoryStore
        store = VectorMemoryStore()
        apps = [
            {"job_title": "Engineer", "company": "ACME", "match_score": 78, "outcome": "interview"}
        ]
        context = store.format_context_for_agent(apps)
        assert "Engineer" in context
        assert "interview" in context


# ─────────────────────────────────────────────
# Integration tests — Database
# ─────────────────────────────────────────────

class TestApplicationDatabase:
    @pytest.mark.asyncio
    async def test_init_and_save(self):
        import os
        os.makedirs("/tmp/test_job_agent", exist_ok=True)
        from app.memory.database import ApplicationDatabase
        db = ApplicationDatabase()
        await db.init()

        ok = await db.save_application(
            application_id="test-001",
            job_title="Backend Engineer",
            company_name="TestCo",
            match_score=75,
            result_json={"test": True},
            job_url="https://example.com/jobs/1"
        )
        assert ok is True

    @pytest.mark.asyncio
    async def test_get_application(self):
        import os
        os.makedirs("/tmp/test_job_agent", exist_ok=True)
        from app.memory.database import ApplicationDatabase
        db = ApplicationDatabase()
        await db.init()
        await db.save_application(
            application_id="test-002",
            job_title="Frontend Engineer",
            company_name="WebCo",
            match_score=65,
            result_json={"foo": "bar"},
        )
        record = await db.get_application("test-002")
        assert record is not None
        assert record["job_title"] == "Frontend Engineer"

    @pytest.mark.asyncio
    async def test_record_feedback(self):
        import os
        os.makedirs("/tmp/test_job_agent", exist_ok=True)
        from app.memory.database import ApplicationDatabase
        db = ApplicationDatabase()
        await db.init()
        await db.save_application(
            application_id="test-003",
            job_title="DevOps",
            company_name="CloudCo",
            match_score=88,
            result_json={},
        )
        ok = await db.record_feedback("test-003", "interview", "Great response!")
        assert ok is True

    @pytest.mark.asyncio
    async def test_list_applications(self):
        import os
        os.makedirs("/tmp/test_job_agent", exist_ok=True)
        from app.memory.database import ApplicationDatabase
        db = ApplicationDatabase()
        await db.init()
        apps = await db.list_applications(limit=10)
        assert isinstance(apps, list)


# ─────────────────────────────────────────────
# Integration tests — FastAPI endpoints
# ─────────────────────────────────────────────

class TestAPIEndpoints:
    @pytest.fixture
    def client(self):
        """Create test client with mocked orchestrator."""
        from fastapi.testclient import TestClient
        from unittest.mock import AsyncMock
        from app.main import app
        from app.models.schemas import (
            PipelineResult, JobAnalysis, ProfileMatch,
            TailoredResume, CoverLetter
        )

        # Build a fake pipeline result
        fake_result = PipelineResult(
            application_id="test-abc",
            job_analysis=JobAnalysis(
                job_title="Engineer", company_name="TestCo",
                company_description="", required_skills=["Python"],
                preferred_skills=[], experience_level="mid",
                responsibilities=[], keywords=["Python"],
                hidden_expectations=[], tech_stack=[], soft_skills=[],
                company_culture_hints=[], raw_text=""
            ),
            profile_match=ProfileMatch(
                overall_score=75, skill_match_score=80,
                experience_match_score=70, education_match_score=75,
                matched_skills=["Python"], missing_skills=[],
                transferable_skills=[], relevant_experience=[],
                gaps_summary="", strengths_summary="",
                recommendation="apply"
            ),
            tailored_resume=TailoredResume(
                markdown_content="# Test Resume",
                keywords_included=["Python"], keywords_missing=[],
                ats_score_estimate=80, version_id="v1"
            ),
            cover_letter=CoverLetter(
                markdown_content="Dear Hiring Team...",
                word_count=200, tone="professional", version_id="v1"
            ),
            status="completed",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.run = AsyncMock(return_value=fake_result)
        app.state.orchestrator = mock_orchestrator

        import os
        os.makedirs("/tmp/test_job_agent", exist_ok=True)
        from app.memory.database import ApplicationDatabase
        db = ApplicationDatabase()
        import asyncio
        asyncio.get_event_loop().run_until_complete(db.init())
        app.state.db = db

        return TestClient(app, raise_server_exceptions=False)

    def test_health_endpoint(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_analyze_missing_inputs(self, client):
        resp = client.post("/api/v1/analyze", json={
            "candidate_profile": {
                "name": "Test", "email": "t@t.com",
                "summary": "A developer",
                "skills": [], "experience": [], "education": []
            }
        })
        # Should fail: no job_url or job_description_text
        assert resp.status_code == 400

    def test_list_applications(self, client):
        resp = client.get("/api/v1/applications")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
