"""
app/tools/web_scraper.py
Tool — Job Post Scraper

Handles multiple job board formats:
- LinkedIn, Indeed, Greenhouse, Lever, Workday, custom pages
- Falls back to generic text extraction
"""
from __future__ import annotations

import os
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from loguru import logger


class JobPostScraper:
    """
    Scrapes job descriptions from URLs.
    Handles common job boards with specialized selectors,
    falls back to full-page text extraction.
    """

    TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", "30"))
    USER_AGENT = os.getenv(
        "SCRAPER_USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Board-specific CSS selectors for clean extraction
    BOARD_SELECTORS = {
        "greenhouse.io": [".job__description", "#content"],
        "lever.co": [".posting-description", ".posting"],
        "workday.com": ["[data-automation-id='jobPostingDescription']"],
        "linkedin.com": [".job-description", ".description__text"],
        "indeed.com": ["#jobDescriptionText", ".jobsearch-jobDescriptionText"],
        "myworkdayjobs.com": ["[data-automation-id='jobPostingDescription']"],
        "ashbyhq.com": [".job-description"],
        "rippling.com": [".job-description"],
    }

    async def scrape(self, url: str) -> str:
        """
        Scrape job description from URL.
        Returns clean text or raises exception.
        """
        logger.info(f"[Scraper] Fetching: {url}")

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.TIMEOUT,
                headers={"User-Agent": self.USER_AGENT},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

        except httpx.TimeoutException:
            raise ValueError(f"Timeout fetching job URL: {url}")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"HTTP error {e.response.status_code} fetching: {url}")
        except Exception as e:
            raise ValueError(f"Failed to fetch URL: {e}")

        text = self._extract_text(response.text, url)

        if len(text) < 100:
            raise ValueError(f"Extracted text too short ({len(text)} chars) — page may require login")

        logger.info(f"[Scraper] Extracted {len(text)} characters")
        return text

    def _extract_text(self, html: str, url: str) -> str:
        """Extract clean text from HTML using board-specific or generic selectors."""
        soup = BeautifulSoup(html, "lxml")

        # Remove noise elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "meta"]):
            tag.decompose()

        # Try board-specific selectors first
        for domain, selectors in self.BOARD_SELECTORS.items():
            if domain in url:
                for selector in selectors:
                    el = soup.select_one(selector)
                    if el:
                        text = el.get_text(separator="\n", strip=True)
                        if len(text) > 200:
                            logger.debug(f"[Scraper] Used board selector: {selector}")
                            return self._clean_text(text)

        # Fall back to main content heuristic
        for tag in ["main", "article", "[role='main']", "#main", ".main", "#content", ".content"]:
            el = soup.select_one(tag)
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 200:
                    return self._clean_text(text)

        # Last resort: body text
        body = soup.find("body")
        if body:
            return self._clean_text(body.get_text(separator="\n", strip=True))

        return self._clean_text(soup.get_text(separator="\n", strip=True))

    def _clean_text(self, text: str) -> str:
        """Clean extracted text — remove excess whitespace, normalize line breaks."""
        # Collapse multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Remove lines that are just whitespace or single chars
        lines = [line.strip() for line in text.split("\n")]
        lines = [line for line in lines if len(line) > 1]
        return "\n".join(lines).strip()


# Convenience function for sync usage
def scrape_job_sync(url: str) -> str:
    """Synchronous wrapper for use in non-async contexts."""
    import asyncio
    scraper = JobPostScraper()
    return asyncio.run(scraper.scrape(url))
