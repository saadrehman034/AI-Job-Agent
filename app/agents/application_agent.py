"""
app/agents/application_agent.py
Agent 5 — Application Agent

Responsibilities:
1. Draft a professional application email
2. (Optional) Automate form submission via Playwright

This agent is optional and gated by the ENABLE_BROWSER_AUTOMATION env flag.
"""
from __future__ import annotations

import os
from app.agents.base_agent import BaseAgent
from app.models.schemas import (
    CandidateProfile, JobAnalysis,
    TailoredResume, CoverLetter, ApplicationEmail
)
from loguru import logger


SYSTEM_PROMPT = """
You are an expert job application coach who writes professional application emails
that get opened and read.

Rules for application emails:
1. Subject line: Clear, professional, role-specific — not generic
   Good: "Application: Senior Backend Engineer — Jane Smith"
   Bad: "Job Application" or "Inquiry about position"

2. Opening: Brief and direct — who you are and what you're applying for
3. Middle: 2-3 sentences highlighting your most relevant qualification (1 specific thing)
4. Attachments note: Mention resume and cover letter are attached
5. Close: Professional, with a forward-looking statement
6. Signature: Full name, contact info

Length: 150-200 words maximum. Hiring managers are busy.

Return ONLY valid JSON:
{
  "subject": "email subject line",
  "body": "full email body text (use \\n for line breaks)",
  "attachments_note": "brief note about attachments"
}
"""


class ApplicationAgent(BaseAgent):
    """
    Agent 5 — Application Agent

    Decision logic:
    - Always generates email draft
    - Browser automation only if ENABLE_BROWSER_AUTOMATION=true AND job_url provided
    - Gracefully degrades if Playwright is not installed
    """

    def __init__(self):
        super().__init__("ApplicationAgent")
        self.enable_browser = os.getenv("ENABLE_BROWSER_AUTOMATION", "false").lower() == "true"
        self.enable_email_send = os.getenv("ENABLE_EMAIL_SEND", "false").lower() == "true"

    def run(
        self,
        candidate: CandidateProfile,
        job: JobAnalysis,
        resume: TailoredResume,
        cover_letter: CoverLetter,
        job_url: str | None = None,
    ) -> ApplicationEmail:
        self._log_agent_start(
            candidate=candidate.name,
            job=job.job_title,
            company=job.company_name,
            browser_automation=self.enable_browser
        )

        # Step 1: Generate email draft
        email = self._generate_email(candidate, job, resume)

        # Step 2: (Optional) Browser automation
        if self.enable_browser and job_url:
            logger.info(f"[{self.name}] Browser automation enabled — attempting form fill")
            self._attempt_form_fill(job_url, candidate, resume, cover_letter)
        else:
            if self.enable_browser and not job_url:
                logger.warning(f"[{self.name}] Browser automation enabled but no URL provided")

        self._log_agent_done(f"subject='{email.subject}'")
        return email

    def _generate_email(
        self,
        candidate: CandidateProfile,
        job: JobAnalysis,
        resume: TailoredResume,
    ) -> ApplicationEmail:
        user_message = f"""
Draft a professional application email for:

Candidate: {candidate.name}
Email: {candidate.email}
Applying for: {job.job_title} at {job.company_name}

Key qualifications to highlight (pick the most impressive ONE):
{chr(10).join('• ' + b for b in resume.keywords_included[:5])}

Return ONLY valid JSON with subject, body, and attachments_note fields.
"""

        raw = self._call_llm(SYSTEM_PROMPT, user_message, expect_json=True)
        data = self._parse_json_response(raw, fallback={
            "subject": f"Application: {job.job_title} — {candidate.name}",
            "body": f"Dear Hiring Team,\n\nPlease find my application for the {job.job_title} role attached.\n\nBest regards,\n{candidate.name}",
            "attachments_note": "Resume and cover letter attached."
        })

        return ApplicationEmail(
            subject=data.get("subject", ""),
            body=data.get("body", ""),
            attachments_note=data.get("attachments_note", "")
        )

    def _attempt_form_fill(
        self,
        url: str,
        candidate: CandidateProfile,
        resume: TailoredResume,
        cover_letter: CoverLetter,
    ) -> None:
        """
        Optional: Use Playwright to automate job application form filling.
        This is a best-effort operation — failures are logged and ignored.
        """
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                logger.info(f"[{self.name}] Navigating to {url}")
                page.goto(url, wait_until="networkidle", timeout=30000)

                # Common form field selectors — these work on many ATS systems
                field_map = {
                    'input[name*="first"]': candidate.name.split()[0],
                    'input[name*="last"]': candidate.name.split()[-1],
                    'input[name*="email"]': candidate.email,
                    'input[name*="phone"]': candidate.phone or "",
                    'input[name*="linkedin"]': candidate.linkedin or "",
                    'input[name*="github"]': candidate.github or "",
                    'textarea[name*="cover"]': cover_letter.markdown_content[:2000],
                }

                for selector, value in field_map.items():
                    try:
                        if page.query_selector(selector) and value:
                            page.fill(selector, value)
                            logger.debug(f"[{self.name}] Filled: {selector}")
                    except Exception:
                        pass  # Field not found — skip gracefully

                logger.info(f"[{self.name}] Form fields pre-filled — human review required before submission")
                # NOTE: We deliberately do NOT auto-submit. The human reviews and submits.
                browser.close()

        except ImportError:
            logger.warning(f"[{self.name}] Playwright not installed — skipping browser automation")
        except Exception as e:
            logger.warning(f"[{self.name}] Browser automation failed: {e} — continuing without it")
