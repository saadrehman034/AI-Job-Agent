"""
app/agents/critic_agent.py
Bonus Agent — Critic (Multi-Agent Collaboration)

Critiques resume or cover letter output and optionally revises it.
Implements the "critic loop" where agents check each other's work.
"""
from __future__ import annotations

import uuid
from app.agents.base_agent import BaseAgent
from app.models.schemas import JobAnalysis, CritiqueResult


RESUME_CRITIC_PROMPT = """
You are a senior recruiter at a top tech company who reviews 100+ resumes per week.
You will critique a tailored resume with brutal honesty.

Rate it 1–10 and identify specific improvements.

OUTPUT SCHEMA (valid JSON only):
{
  "target": "resume",
  "score": 1-10,
  "strengths": ["specific things done well"],
  "weaknesses": ["specific problems"],
  "suggestions": ["actionable improvements"],
  "revised_content": "optionally provide the improved version in Markdown, or null"
}

Be specific. "Bullet point 3 in Experience 1 lacks a quantified outcome" is useful.
"The resume is good" is not useful.
"""

COVER_LETTER_CRITIC_PROMPT = """
You are a hiring manager who has read 10,000 cover letters.
You will critique a cover letter with specific, actionable feedback.

Rate it 1–10 and provide specific improvements.

Red flags you always check:
- Generic opening ("I am writing to apply for...")
- Restating the resume instead of telling a story
- No company-specific research evident
- Clichéd language
- Wrong length (< 200 or > 400 words)

OUTPUT SCHEMA (valid JSON only):
{
  "target": "cover_letter",
  "score": 1-10,
  "strengths": ["specific things done well"],
  "weaknesses": ["specific problems — be direct"],
  "suggestions": ["exactly what to change"],
  "revised_content": "provide the improved version in Markdown"
}
"""


class CriticAgent(BaseAgent):
    """
    Multi-agent critic — reviews resume or cover letter and suggests improvements.

    When enable_revision=True, it rewrites the content. This adds latency
    but significantly improves output quality.
    """

    def __init__(self):
        super().__init__("CriticAgent")

    def run(self, *args, **kwargs):
        """CriticAgent uses critique_resume() and critique_cover_letter() directly."""
        pass

    def critique_resume(
        self,
        resume_markdown: str,
        job: JobAnalysis,
        enable_revision: bool = True,
    ) -> CritiqueResult:
        self._log_agent_start(target="resume", enable_revision=enable_revision)

        user_message = f"""
Critique this resume for the role of {job.job_title} at {job.company_name}.

REQUIRED SKILLS FOR ROLE: {', '.join(job.required_skills)}
ATS KEYWORDS EXPECTED: {', '.join(job.keywords[:10])}

RESUME TO CRITIQUE:
{self._truncate(resume_markdown, 4000)}

{"Provide a revised version in revised_content field." if enable_revision else "Set revised_content to null."}

Return ONLY valid JSON.
"""

        raw = self._call_llm(RESUME_CRITIC_PROMPT, user_message, expect_json=True)
        data = self._parse_json_response(raw, fallback={"target": "resume", "score": 7})
        result = self._build_result(data, "resume")
        self._log_agent_done(f"score={result.score}/10, weaknesses={len(result.weaknesses)}")
        return result

    def critique_cover_letter(
        self,
        cover_letter_markdown: str,
        job: JobAnalysis,
        enable_revision: bool = True,
    ) -> CritiqueResult:
        self._log_agent_start(target="cover_letter", enable_revision=enable_revision)

        user_message = f"""
Critique this cover letter for the role of {job.job_title} at {job.company_name}.

Company context: {job.company_description}

COVER LETTER TO CRITIQUE:
{self._truncate(cover_letter_markdown, 3000)}

{"Provide a revised version in revised_content field." if enable_revision else "Set revised_content to null."}

Return ONLY valid JSON.
"""

        raw = self._call_llm(COVER_LETTER_CRITIC_PROMPT, user_message, expect_json=True)
        data = self._parse_json_response(raw, fallback={"target": "cover_letter", "score": 7})
        result = self._build_result(data, "cover_letter")
        self._log_agent_done(f"score={result.score}/10, suggestions={len(result.suggestions)}")
        return result

    def _build_result(self, data: dict, target: str) -> CritiqueResult:
        return CritiqueResult(
            target=target,
            score=max(1, min(10, int(data.get("score", 7)))),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            suggestions=data.get("suggestions", []),
            revised_content=data.get("revised_content"),
        )
