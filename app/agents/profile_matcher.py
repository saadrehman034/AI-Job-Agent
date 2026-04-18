"""
app/agents/profile_matcher.py
Agent 2 — Profile Matcher

Input:  CandidateProfile + JobAnalysis
Output: ProfileMatch (score, gaps, selected experience, strategy)
"""
from __future__ import annotations

import json
from app.agents.base_agent import BaseAgent
from app.models.schemas import CandidateProfile, JobAnalysis, ProfileMatch


SYSTEM_PROMPT = """
You are a senior career strategist and ex-recruiter who specializes in matching candidates
to roles and identifying how to position their experience for maximum impact.

Your job is to:
1. Score the candidate against the job requirements across multiple dimensions
2. Identify which of their experience bullets are most relevant and should be foregrounded
3. Identify genuine skill gaps (don't fabricate gaps that aren't there)
4. Recommend whether to apply, apply with caveats, or skip

Scoring rubric (0–100 each):
- skill_match_score: % of required + preferred skills candidate has
- experience_match_score: quality and relevance of experience to responsibilities
- education_match_score: education alignment (be lenient — experience > education)
- overall_score: weighted average (skills 40%, experience 50%, education 10%)

Be honest but strategic. A 65% match is worth applying to; a 30% match is not.

OUTPUT SCHEMA (valid JSON only):
{
  "overall_score": 0-100,
  "skill_match_score": 0-100,
  "experience_match_score": 0-100,
  "education_match_score": 0-100,
  "matched_skills": ["skills candidate has that job requires"],
  "missing_skills": ["skills job requires that candidate lacks"],
  "transferable_skills": ["adjacent/transferable skills candidate has"],
  "relevant_experience": ["exact bullet points from candidate's history most relevant to this role"],
  "gaps_summary": "2-3 sentence honest gap analysis",
  "strengths_summary": "2-3 sentence summary of candidate's strongest selling points for this role",
  "recommendation": "apply|apply-with-note|skip",
  "recommendation_reasoning": "1-2 sentences explaining the recommendation"
}
"""


class ProfileMatcherAgent(BaseAgent):
    """
    Matches candidate profile against job requirements.

    Decision logic:
    - Pulls from memory for similar past jobs to improve scoring calibration
    - Selects the top N most relevant experience bullets for the resume generator
    - Makes a final recommendation: apply / apply-with-note / skip
    """

    def __init__(self):
        super().__init__("ProfileMatcher")

    def run(
        self,
        candidate: CandidateProfile,
        job: JobAnalysis,
        memory_context: str = "",
    ) -> ProfileMatch:
        self._log_agent_start(
            candidate=candidate.name,
            job=job.job_title,
            company=job.company_name
        )

        # Build structured representation of candidate
        candidate_summary = self._build_candidate_summary(candidate)
        job_summary = self._build_job_summary(job)

        memory_section = ""
        if memory_context:
            memory_section = f"\n\nRELEVANT PAST APPLICATION CONTEXT:\n{memory_context}"

        user_message = f"""
Score this candidate against the job requirements.

CANDIDATE PROFILE:
{candidate_summary}

JOB REQUIREMENTS:
{job_summary}
{memory_section}

Return ONLY valid JSON matching the schema. Ensure relevant_experience contains
EXACT bullet text copied from the candidate's experience bullets above.
"""

        raw = self._call_llm(SYSTEM_PROMPT, user_message, expect_json=True)
        data = self._parse_json_response(raw, fallback={
            "overall_score": 50,
            "recommendation": "apply-with-note"
        })

        # Clamp scores to valid range
        for score_field in ["overall_score", "skill_match_score", "experience_match_score", "education_match_score"]:
            data[score_field] = max(0, min(100, int(data.get(score_field, 50))))

        result = ProfileMatch(
            overall_score=data.get("overall_score", 50),
            skill_match_score=data.get("skill_match_score", 50),
            experience_match_score=data.get("experience_match_score", 50),
            education_match_score=data.get("education_match_score", 50),
            matched_skills=data.get("matched_skills", []),
            missing_skills=data.get("missing_skills", []),
            transferable_skills=data.get("transferable_skills", []),
            relevant_experience=data.get("relevant_experience", []),
            gaps_summary=data.get("gaps_summary", ""),
            strengths_summary=data.get("strengths_summary", ""),
            recommendation=data.get("recommendation", "apply"),
        )

        self._log_agent_done(
            f"score={result.overall_score}, "
            f"recommendation={result.recommendation}, "
            f"missing_skills={len(result.missing_skills)}"
        )
        return result

    def _build_candidate_summary(self, candidate: CandidateProfile) -> str:
        lines = [
            f"Name: {candidate.name}",
            f"Summary: {candidate.summary}",
            f"Skills: {', '.join(candidate.skills)}",
            "",
            "EXPERIENCE:",
        ]
        for exp in candidate.experience:
            lines.append(f"  {exp.title} @ {exp.company} ({exp.start_date}–{exp.end_date})")
            for bullet in exp.bullets:
                lines.append(f"    • {bullet}")
        lines.append("\nEDUCATION:")
        for edu in candidate.education:
            lines.append(f"  {edu.degree} — {edu.institution} ({edu.year})")
        return "\n".join(lines)

    def _build_job_summary(self, job: JobAnalysis) -> str:
        return json.dumps({
            "title": job.job_title,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "experience_level": job.experience_level,
            "experience_years": job.experience_years,
            "responsibilities": job.responsibilities,
            "hidden_expectations": job.hidden_expectations,
            "tech_stack": job.tech_stack,
        }, indent=2)
