"""
app/orchestrator.py
Master Orchestrator — controls the full agent pipeline.

Responsibilities:
- Coordinate all 5 agents in sequence
- Manage short-term state (current pipeline run)
- Interface with memory module (retrieve context + store results)
- Handle errors, retries, and partial failures gracefully
- Return complete PipelineResult

Pipeline flow:
  [Scrape] → [JobAnalyzer] → [ProfileMatcher] → [ResumeGen] → [CoverLetterGen]
          → (optional: CriticLoop) → [ApplicationAgent] → [Store in Memory]
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Optional

from loguru import logger

from app.agents.job_analyzer import JobAnalyzerAgent
from app.agents.profile_matcher import ProfileMatcherAgent
from app.agents.resume_generator import ResumeGeneratorAgent
from app.agents.cover_letter import CoverLetterAgent
from app.agents.application_agent import ApplicationAgent
from app.agents.critic_agent import CriticAgent
from app.memory.vector_store import VectorMemoryStore
from app.memory.database import ApplicationDatabase
from app.models.schemas import (
    PipelineRequest, PipelineResult, CandidateProfile
)
from app.tools.web_scraper import JobPostScraper
from app.tools.document_writer import DocumentWriter


class Orchestrator:
    """
    Master pipeline controller.

    Manages the multi-agent workflow, error handling, and memory.
    Designed for both async (FastAPI) and sync (CLI) usage.
    """

    def __init__(self):
        self.job_analyzer = JobAnalyzerAgent()
        self.profile_matcher = ProfileMatcherAgent()
        self.resume_generator = ResumeGeneratorAgent()
        self.cover_letter_agent = CoverLetterAgent()
        self.application_agent = ApplicationAgent()
        self.critic = CriticAgent()
        self.memory = VectorMemoryStore()
        self.db = ApplicationDatabase()
        self.scraper = JobPostScraper()
        self.doc_writer = DocumentWriter()
        self.enable_critic = os.getenv("ENABLE_CRITIC_LOOP", "true").lower() == "true"
        logger.info("[Orchestrator] All agents initialized")

    async def run(self, request: PipelineRequest) -> PipelineResult:
        """
        Execute the full job application pipeline.

        Steps:
        1. Scrape job URL (if provided)
        2. Analyze job description
        3. Retrieve similar past applications from memory
        4. Match candidate profile
        5. Generate tailored resume
        6. Generate cover letter
        7. Critic loop (if enabled)
        8. Generate application email
        9. Store results in memory
        10. Return complete result
        """
        application_id = str(uuid.uuid4())[:12]
        start_time = time.time()
        errors = []

        logger.info(f"[Orchestrator] ═══ Pipeline START | id={application_id} ═══")

        # ── Step 1: Get job description ──────────────────────────────────────
        job_description = await self._get_job_description(request, errors)
        if not job_description:
            return self._error_result(application_id, "Could not obtain job description", errors)

        # ── Step 2: Analyze job ───────────────────────────────────────────────
        logger.info(f"[Orchestrator] Step 2/9: Job Analysis")
        try:
            job_analysis = self.job_analyzer.run(job_description)
        except Exception as e:
            logger.error(f"[Orchestrator] Job analysis failed: {e}")
            return self._error_result(application_id, f"Job analysis failed: {e}", errors)

        # ── Step 3: Retrieve memory context ───────────────────────────────────
        logger.info(f"[Orchestrator] Step 3/9: Memory Retrieval")
        similar_apps = self.memory.retrieve_similar(job_description, top_k=3)
        memory_context = self.memory.format_context_for_agent(similar_apps)
        if similar_apps:
            logger.info(f"[Orchestrator] Retrieved {len(similar_apps)} similar past applications")

        # ── Step 4: Profile matching ───────────────────────────────────────────
        logger.info(f"[Orchestrator] Step 4/9: Profile Matching")
        try:
            profile_match = self.profile_matcher.run(
                request.candidate_profile,
                job_analysis,
                memory_context=memory_context,
            )
        except Exception as e:
            logger.error(f"[Orchestrator] Profile matching failed: {e}")
            errors.append(f"Profile matching error: {e}")
            profile_match = self._fallback_profile_match()

        # ── Step 5: Resume generation ──────────────────────────────────────────
        logger.info(f"[Orchestrator] Step 5/9: Resume Generation")
        try:
            tailored_resume = self.resume_generator.run(
                request.candidate_profile,
                job_analysis,
                profile_match,
            )
        except Exception as e:
            logger.error(f"[Orchestrator] Resume generation failed: {e}")
            return self._error_result(application_id, f"Resume generation failed: {e}", errors)

        # ── Step 6: Cover letter generation ────────────────────────────────────
        logger.info(f"[Orchestrator] Step 6/9: Cover Letter Generation")
        try:
            cover_letter = self.cover_letter_agent.run(
                request.candidate_profile,
                job_analysis,
                profile_match,
                tailored_resume,
            )
        except Exception as e:
            logger.error(f"[Orchestrator] Cover letter generation failed: {e}")
            errors.append(f"Cover letter error: {e}")
            cover_letter = None

        # ── Step 7: Critic loop ─────────────────────────────────────────────────
        resume_critique = None
        cover_letter_critique = None

        if self.enable_critic and request.enable_critic_loop:
            logger.info(f"[Orchestrator] Step 7/9: Critic Loop")
            try:
                resume_critique = self.critic.critique_resume(
                    tailored_resume.markdown_content,
                    job_analysis,
                    enable_revision=True,
                )
                # Use revised content if score improved
                if resume_critique.revised_content and resume_critique.score >= 7:
                    logger.info(f"[Orchestrator] Using critic-revised resume (score: {resume_critique.score}/10)")
                    tailored_resume.markdown_content = resume_critique.revised_content
            except Exception as e:
                logger.warning(f"[Orchestrator] Resume critique failed: {e}")
                errors.append(f"Resume critique error: {e}")

            if cover_letter:
                try:
                    cover_letter_critique = self.critic.critique_cover_letter(
                        cover_letter.markdown_content,
                        job_analysis,
                        enable_revision=True,
                    )
                    if cover_letter_critique.revised_content and cover_letter_critique.score >= 7:
                        logger.info(f"[Orchestrator] Using critic-revised cover letter (score: {cover_letter_critique.score}/10)")
                        cover_letter.markdown_content = cover_letter_critique.revised_content
                except Exception as e:
                    logger.warning(f"[Orchestrator] Cover letter critique failed: {e}")
                    errors.append(f"Cover letter critique error: {e}")

        # ── Step 8: Save documents to DOCX ────────────────────────────────────
        logger.info(f"[Orchestrator] Step 8/9: Document Generation")
        try:
            resume_path = self.doc_writer.save_resume(
                tailored_resume.markdown_content,
                request.candidate_profile.name,
                job_analysis.company_name,
                tailored_resume.version_id,
            )
            if resume_path:
                tailored_resume.docx_path = resume_path

            if cover_letter:
                cl_path = self.doc_writer.save_cover_letter(
                    cover_letter.markdown_content,
                    request.candidate_profile.name,
                    job_analysis.company_name,
                    cover_letter.version_id,
                )
                if cl_path:
                    cover_letter.docx_path = cl_path
        except Exception as e:
            logger.warning(f"[Orchestrator] Document save failed: {e}")
            errors.append(f"Document generation error: {e}")

        # ── Step 9: Application email + store in memory ────────────────────────
        application_email = None
        if request.generate_email:
            logger.info(f"[Orchestrator] Step 9/9: Application Email + Memory Store")
            try:
                application_email = self.application_agent.run(
                    request.candidate_profile,
                    job_analysis,
                    tailored_resume,
                    cover_letter,
                    job_url=request.job_url,
                )
            except Exception as e:
                logger.warning(f"[Orchestrator] Application email failed: {e}")
                errors.append(f"Email generation error: {e}")

        # ── Store in memory ─────────────────────────────────────────────────────
        try:
            self.memory.store_application(
                application_id=application_id,
                job_description=job_description,
                job_title=job_analysis.job_title,
                company=job_analysis.company_name,
                match_score=profile_match.overall_score,
            )
        except Exception as e:
            logger.warning(f"[Orchestrator] Memory store failed: {e}")

        # ── Build final result ──────────────────────────────────────────────────
        elapsed = time.time() - start_time

        result = PipelineResult(
            application_id=application_id,
            job_analysis=job_analysis,
            profile_match=profile_match,
            tailored_resume=tailored_resume,
            cover_letter=cover_letter or self._empty_cover_letter(),
            application_email=application_email,
            resume_critique=resume_critique,
            cover_letter_critique=cover_letter_critique,
            total_processing_time_seconds=round(elapsed, 2),
            status="completed" if not errors else "completed_with_warnings",
            errors=errors,
        )

        # Async save to DB (non-blocking)
        try:
            await self.db.init()
            await self.db.save_application(
                application_id=application_id,
                job_title=job_analysis.job_title,
                company_name=job_analysis.company_name,
                match_score=profile_match.overall_score,
                result_json=result.model_dump(mode="json"),
                job_url=request.job_url,
            )
        except Exception as e:
            logger.warning(f"[Orchestrator] DB save failed: {e}")

        logger.info(
            f"[Orchestrator] ═══ Pipeline DONE | id={application_id} | "
            f"time={elapsed:.1f}s | score={profile_match.overall_score}% ═══"
        )
        return result

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────

    async def _get_job_description(
        self, request: PipelineRequest, errors: list
    ) -> Optional[str]:
        """Get job description from URL or text."""
        if request.job_description_text:
            logger.info("[Orchestrator] Step 1/9: Using provided job description text")
            return request.job_description_text

        if request.job_url:
            logger.info(f"[Orchestrator] Step 1/9: Scraping job URL: {request.job_url}")
            try:
                return await self.scraper.scrape(request.job_url)
            except Exception as e:
                logger.error(f"[Orchestrator] Scraping failed: {e}")
                errors.append(f"Scraping error: {e}")
                return None

        errors.append("No job URL or description provided")
        return None

    def _fallback_profile_match(self):
        from app.models.schemas import ProfileMatch
        return ProfileMatch(
            overall_score=50,
            skill_match_score=50,
            experience_match_score=50,
            education_match_score=50,
            matched_skills=[],
            missing_skills=[],
            transferable_skills=[],
            relevant_experience=[],
            gaps_summary="Unable to compute gap analysis",
            strengths_summary="Unable to compute strength analysis",
            recommendation="apply",
        )

    def _empty_cover_letter(self):
        from app.models.schemas import CoverLetter
        return CoverLetter(
            markdown_content="Cover letter generation failed. Please try again.",
            word_count=0,
            tone="unknown",
            version_id="error",
        )

    def _error_result(self, application_id: str, message: str, errors: list) -> PipelineResult:
        from app.models.schemas import JobAnalysis, TailoredResume
        errors.append(message)
        logger.error(f"[Orchestrator] Pipeline failed: {message}")
        return PipelineResult(
            application_id=application_id,
            job_analysis=JobAnalysis(
                job_title="Unknown", company_name="Unknown",
                company_description="", required_skills=[], preferred_skills=[],
                experience_level="mid", responsibilities=[], keywords=[],
                hidden_expectations=[], tech_stack=[], soft_skills=[],
                company_culture_hints=[], raw_text=""
            ),
            profile_match=self._fallback_profile_match(),
            tailored_resume=TailoredResume(
                markdown_content="", keywords_included=[], keywords_missing=[],
                ats_score_estimate=0, version_id="error"
            ),
            cover_letter=self._empty_cover_letter(),
            status="failed",
            errors=errors,
        )
