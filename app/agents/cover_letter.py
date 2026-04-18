# """
# app/agents/cover_letter.py
# Agent 4 — Cover Letter Generator

# Input:  CandidateProfile + JobAnalysis + ProfileMatch + TailoredResume
# Output: CoverLetter (Markdown)

# Anti-patterns to avoid:
# - "I am writing to apply for..."
# - "I am a passionate [adjective] professional..."
# - "With my extensive experience in..."
# - Generic statements with no company-specific substance
# - Restating the resume verbatim
# """
# from __future__ import annotations

# import uuid
# from app.agents.base_agent import BaseAgent
# from app.models.schemas import CandidateProfile, JobAnalysis, ProfileMatch, TailoredResume, CoverLetter


# SYSTEM_PROMPT = """
# You are a master cover letter writer who understands that great cover letters are NOT
# summaries of the resume. They tell a STORY and make a human CONNECTION.

# Your cover letter formula:
# 1. OPENING — Hook them in the first sentence. Reference something specific about the
#    company's mission, a recent product, a culture value, or a real problem they're solving.
#    Never start with "I am writing to apply for...". Never.

# 2. WHY YOU — One specific, compelling story that demonstrates your most relevant value.
#    Show, don't tell. "I built X which resulted in Y" beats "I am experienced in Z".

# 3. WHY THEM — Show genuine research. Connect your interests to what they're actually doing.
#    Reference the company description, tech stack, or stated values.

# 4. BRIDGE — Connect your specific skills/experience to their specific needs.
#    Make the hiring manager see you in the role.

# 5. CLOSE — Confident, not desperate. Express genuine enthusiasm and a clear call to action.

# Style rules:
# - Conversational but professional — write like a human, not a template
# - First paragraph: 2-3 sentences max
# - Total length: 250-350 words
# - No clichés: "synergy", "leverage", "team player", "results-driven", "passionate about"
# - Do NOT start any sentence with "I" as the first word of a paragraph
# - Vary sentence structure and length
# - Sound like YOU, not like every other applicant

# Output: Clean Markdown cover letter only. No preamble. Start with the date line.
# """


# class CoverLetterAgent(BaseAgent):
#     """
#     Generates a personalized, human-sounding cover letter.

#     Decision logic:
#     - Adjusts tone based on company culture hints (startup = conversational,
#       enterprise = formal, tech company = technical + direct)
#     - References specific company details to signal genuine research
#     - Builds narrative bridge between candidate's best story and job needs
#     """

#     def __init__(self):
#         super().__init__("CoverLetterGenerator")

#     def run(
#         self,
#         candidate: CandidateProfile,
#         job: JobAnalysis,
#         match: ProfileMatch,
#         resume: TailoredResume,
#     ) -> CoverLetter:
#         self._log_agent_start(
#             candidate=candidate.name,
#             job=job.job_title,
#             company=job.company_name
#         )

#         tone = self._determine_tone(job)

#         user_message = f"""
# Write a compelling, personalized cover letter for this application.

# CANDIDATE: {candidate.name}
# APPLYING TO: {job.job_title} at {job.company_name}
# EMAIL: {candidate.email}
# DATE: [Today's date]

# THEIR STRONGEST SELLING POINTS FOR THIS ROLE:
# {match.strengths_summary}

# MOST RELEVANT EXPERIENCE HIGHLIGHTS (use 1-2 as specific examples):
# {chr(10).join('• ' + b for b in match.relevant_experience[:5])}

# COMPANY CONTEXT:
# - Description: {job.company_description}
# - Culture hints: {', '.join(job.company_culture_hints)}
# - Tech stack: {', '.join(job.tech_stack[:6])}
# - They need someone who can: {'; '.join(job.responsibilities[:3])}

# TONE: {tone}

# IMPORTANT:
# - Do NOT start with "I am writing to apply..."
# - Reference something SPECIFIC about {job.company_name} in the first paragraph
# - Tell ONE specific story/achievement, not a list of skills
# - Length: 250-350 words
# - End with a confident (not desperate) call to action

# Write the complete cover letter in Markdown. Start with the date.
# """

#         markdown = self._call_llm(SYSTEM_PROMPT, user_message, expect_json=False)
#         word_count = len(markdown.split())
#         version_id = str(uuid.uuid4())[:8]

#         result = CoverLetter(
#             markdown_content=markdown,
#             word_count=word_count,
#             tone=tone,
#             version_id=version_id,
#         )

#         self._log_agent_done(f"words={word_count}, tone={tone}, version={version_id}")
#         return result

#     def _determine_tone(self, job: JobAnalysis) -> str:
#         """
#         Decide cover letter tone based on company culture signals.
#         """
#         culture_text = " ".join(job.company_culture_hints).lower()
#         company_desc = job.company_description.lower()

#         startup_signals = ["startup", "fast-paced", "dynamic", "scrappy", "wear many hats", "move fast"]
#         formal_signals = ["enterprise", "fortune 500", "global", "compliance", "governance", "corporate"]

#         if any(s in culture_text + company_desc for s in startup_signals):
#             return "conversational and energetic"
#         elif any(s in culture_text + company_desc for s in formal_signals):
#             return "professional and formal"
#         else:
#             return "professional yet personable"


"""
app/agents/cover_letter.py
Agent 4 — Cover Letter Generator
"""
from __future__ import annotations

import uuid
from app.agents.base_agent import BaseAgent
from app.models.schemas import CandidateProfile, JobAnalysis, ProfileMatch, TailoredResume, CoverLetter


SYSTEM_PROMPT = """
You are a master cover letter writer who understands that great cover letters are NOT
summaries of the resume. They tell a STORY and make a human CONNECTION.

Your cover letter formula:
1. OPENING — Hook them in the first sentence. Reference something specific about the
   company's mission, a recent product, a culture value, or a real problem they're solving.
   Never start with "I am writing to apply for...". Never.

2. WHY YOU — One specific, compelling story that demonstrates your most relevant value.
   Show, don't tell. "I built X which resulted in Y" beats "I am experienced in Z".

3. WHY THEM — Show genuine research. Connect your interests to what they're actually doing.
   Reference the company description, tech stack, or stated values.

4. BRIDGE — Connect your specific skills/experience to their specific needs.
   Make the hiring manager see you in the role.

5. CLOSE — Confident, not desperate. Express genuine enthusiasm and a clear call to action.

Style rules:
- Conversational but professional — write like a human, not a template
- First paragraph: 2-3 sentences max
- Total length: 250-350 words
- No cliches: "synergy", "leverage", "team player", "results-driven", "passionate about"
- Do NOT start any sentence with "I" as the first word of a paragraph
- Vary sentence structure and length
- Sound like YOU, not like every other applicant

Output: Clean Markdown cover letter only. No preamble. Start with the date line.
"""


class CoverLetterAgent(BaseAgent):

    def __init__(self):
        super().__init__("CoverLetterGenerator")

    def run(
        self,
        candidate: CandidateProfile,
        job: JobAnalysis,
        match: ProfileMatch,
        resume: TailoredResume,
    ) -> CoverLetter:
        self._log_agent_start(
            candidate=candidate.name,
            job=job.job_title,
            company=job.company_name
        )

        tone = self._determine_tone(job)

        # Safe joins — handle None or empty lists
        culture_hints = ", ".join(job.company_culture_hints) if job.company_culture_hints else "not specified"
        tech_stack = ", ".join(job.tech_stack[:6]) if job.tech_stack else "not specified"
        responsibilities = "; ".join(job.responsibilities[:3]) if job.responsibilities else "not specified"
        experience_bullets = "\n".join(
            "• " + b for b in match.relevant_experience[:5]
        ) if match.relevant_experience else "• See resume for relevant experience"

        user_message = f"""
Write a compelling, personalized cover letter for this application.

CANDIDATE: {candidate.name}
APPLYING TO: {job.job_title} at {job.company_name}
EMAIL: {candidate.email}
DATE: [Today's date]

THEIR STRONGEST SELLING POINTS FOR THIS ROLE:
{match.strengths_summary or "Strong technical background relevant to this role"}

MOST RELEVANT EXPERIENCE HIGHLIGHTS (use 1-2 as specific examples):
{experience_bullets}

COMPANY CONTEXT:
- Description: {job.company_description or "A growing technology company"}
- Culture hints: {culture_hints}
- Tech stack: {tech_stack}
- They need someone who can: {responsibilities}

TONE: {tone}

IMPORTANT:
- Do NOT start with "I am writing to apply..."
- Reference something SPECIFIC about {job.company_name} in the first paragraph
- Tell ONE specific story/achievement, not a list of skills
- Length: 250-350 words
- End with a confident (not desperate) call to action

Write the complete cover letter in Markdown. Start with the date.
"""

        try:
            markdown = self._call_llm(SYSTEM_PROMPT, user_message, expect_json=False)
        except Exception as e:
            from loguru import logger
            logger.error(f"[CoverLetterGenerator] LLM call failed: {e}")
            markdown = None

        # Fallback if LLM returns nothing
        if not markdown or not markdown.strip():
            markdown = f"""April 18, 2026

Dear {job.company_name} Hiring Team,

{job.company_name}'s work in this space is exactly the kind of challenge I have been preparing for. The {job.job_title} role aligns directly with my experience and what I want to work on next.

{match.strengths_summary or f"My background in {', '.join(candidate.skills[:3]) if candidate.skills else 'software engineering'} maps well to what you are building."}

I would love to discuss how my experience can contribute to your team.

Best regards,
{candidate.name}
{candidate.email}"""

        word_count = len(markdown.split())
        version_id = str(uuid.uuid4())[:8]

        result = CoverLetter(
            markdown_content=markdown,
            word_count=word_count,
            tone=tone,
            version_id=version_id,
        )

        self._log_agent_done(f"words={word_count}, tone={tone}, version={version_id}")
        return result

    def _determine_tone(self, job: JobAnalysis) -> str:
        try:
            culture_text = " ".join(job.company_culture_hints or []).lower()
            company_desc = (job.company_description or "").lower()

            startup_signals = ["startup", "fast-paced", "dynamic", "scrappy", "wear many hats", "move fast"]
            formal_signals = ["enterprise", "fortune 500", "global", "compliance", "governance", "corporate"]

            if any(s in culture_text + company_desc for s in startup_signals):
                return "conversational and energetic"
            elif any(s in culture_text + company_desc for s in formal_signals):
                return "professional and formal"
            else:
                return "professional yet personable"
        except Exception:
            return "professional yet personable"