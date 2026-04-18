"""
app/agents/job_analyzer.py
Agent 1 — Job Analyzer

Input:  raw job description text
Output: JobAnalysis (structured skills, keywords, hidden expectations, etc.)
"""
from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.models.schemas import JobAnalysis


# ─────────────────────────────────────────────
# System prompt (internal prompt used by agent)
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """
You are an expert talent acquisition analyst and career coach with 15 years of experience
reading job descriptions. Your job is to deeply analyze a job posting and extract ALL
meaningful signals — both explicit and implicit.

You think like an ATS system, a recruiter, AND a hiring manager simultaneously.

Always respond with valid JSON only. No explanation, no markdown prose outside the JSON block.

OUTPUT SCHEMA:
{
  "job_title": "exact title from posting",
  "company_name": "company name",
  "company_description": "1-2 sentence company description inferred from context",
  "required_skills": ["list of hard required skills"],
  "preferred_skills": ["nice-to-have skills"],
  "experience_level": "junior|mid|senior|lead|executive",
  "experience_years": "e.g. 3-5 years or null",
  "responsibilities": ["key responsibilities as bullets"],
  "keywords": ["ATS-critical keywords to include in resume — include exact phrasing"],
  "hidden_expectations": ["implicit requirements not stated but clearly expected"],
  "tech_stack": ["specific tools, frameworks, platforms mentioned"],
  "soft_skills": ["communication, leadership, etc."],
  "company_culture_hints": ["values, working style, culture signals from the description"],
  "salary_range": "if mentioned, else null",
  "remote_policy": "remote|hybrid|onsite|unknown"
}

Hidden expectations to look for:
- If they mention "fast-paced startup" → expect ability to handle ambiguity
- If they list 10+ tools → expect T-shaped generalist, not deep specialist
- If they say "work closely with executives" → expect strong communication and presence
- Management experience often implied by "lead", "mentor", "own", "drive"
- Startup stage signals: "wear many hats", "build from scratch", "0→1"
"""


class JobAnalyzerAgent(BaseAgent):
    """
    Analyzes job descriptions and extracts structured requirements.

    Decision logic:
    - If URL provided, scraping is done by the web_scraper tool before this agent runs
    - Extracts both explicit requirements AND hidden/implicit expectations
    - Identifies ATS keywords with exact phrasing match priority
    """

    def __init__(self):
        super().__init__("JobAnalyzer")

    def run(self, job_description: str) -> JobAnalysis:
        self._log_agent_start(text_length=len(job_description))

        truncated = self._truncate(job_description, max_chars=6000)

        user_message = f"""
Analyze this job description and return structured JSON output.
Be thorough — include hidden expectations that aren't explicitly stated but are clearly implied.

JOB DESCRIPTION:
{truncated}

Return ONLY valid JSON matching the schema. No other text.
"""

        raw = self._call_llm(SYSTEM_PROMPT, user_message, expect_json=True)
        data = self._parse_json_response(raw, fallback={"job_title": "Unknown", "company_name": "Unknown"})

        # Ensure all list fields exist
        list_fields = [
            "required_skills", "preferred_skills", "responsibilities",
            "keywords", "hidden_expectations", "tech_stack",
            "soft_skills", "company_culture_hints"
        ]
        for field in list_fields:
            if field not in data or not isinstance(data[field], list):
                data[field] = []

        result = JobAnalysis(
            job_title=data.get("job_title", "Unknown"),
            company_name=data.get("company_name", "Unknown"),
            company_description=data.get("company_description", ""),
            required_skills=data.get("required_skills", []),
            preferred_skills=data.get("preferred_skills", []),
            experience_level=data.get("experience_level", "mid"),
            experience_years=data.get("experience_years"),
            responsibilities=data.get("responsibilities", []),
            keywords=data.get("keywords", []),
            hidden_expectations=data.get("hidden_expectations", []),
            tech_stack=data.get("tech_stack", []),
            soft_skills=data.get("soft_skills", []),
            company_culture_hints=data.get("company_culture_hints", []),
            salary_range=data.get("salary_range"),
            remote_policy=data.get("remote_policy", "unknown"),
            raw_text=job_description,
        )

        self._log_agent_done(
            f"title={result.job_title}, "
            f"required_skills={len(result.required_skills)}, "
            f"keywords={len(result.keywords)}"
        )
        return result
