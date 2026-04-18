# """
# app/agents/base_agent.py
# Abstract base class for all agents.
# Provides: LLM client, structured output parsing, retry with backoff, logging.
# """
# from __future__ import annotations

# import json
# import os
# import re
# import time
# from abc import ABC, abstractmethod
# from typing import Any, Optional

# import anthropic
# from loguru import logger
# from tenacity import (
#     retry,
#     stop_after_attempt,
#     wait_exponential,
#     retry_if_exception_type,
#     before_sleep_log,
# )
# import logging


# class AgentError(Exception):
#     """Raised when an agent fails after all retries."""


# class BaseAgent(ABC):
#     """
#     Base class for all pipeline agents.

#     Each subclass implements `run()` and uses `_call_llm()` to interact
#     with Claude. Structured JSON outputs are enforced via prompting and
#     parsed with `_parse_json_response()`.
#     """

#     def __init__(self, name: str):
#         self.name = name
#         self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
#         self.model = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
#         self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))
#         self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))
#         self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
#         logger.info(f"[{self.name}] Initialized")

#     @abstractmethod
#     def run(self, *args, **kwargs) -> Any:
#         """Execute the agent's primary task."""
#         ...

#     # ─────────────────────────────────────────────
#     # LLM interaction
#     # ─────────────────────────────────────────────

#     def _call_llm(
#         self,
#         system_prompt: str,
#         user_message: str,
#         expect_json: bool = True,
#     ) -> str:
#         """
#         Call Claude with retry logic.
#         Returns the raw text content of the response.
#         """
#         start = time.time()
#         logger.debug(f"[{self.name}] Calling LLM (expect_json={expect_json})")

#         @retry(
#             stop=stop_after_attempt(self.max_retries),
#             wait=wait_exponential(multiplier=1, min=2, max=30),
#             retry=retry_if_exception_type((anthropic.APIError, anthropic.APIConnectionError)),
#             before_sleep=before_sleep_log(logger, logging.WARNING),
#         )
#         def _make_call():
#             response = self.client.messages.create(
#                 model=self.model,
#                 max_tokens=self.max_tokens,
#                 system=system_prompt,
#                 messages=[{"role": "user", "content": user_message}],
#             )
#             return response.content[0].text

#         try:
#             result = _make_call()
#             elapsed = time.time() - start
#             logger.info(f"[{self.name}] LLM response received in {elapsed:.2f}s")
#             return result
#         except Exception as e:
#             logger.error(f"[{self.name}] LLM call failed: {e}")
#             raise AgentError(f"{self.name} LLM call failed: {e}") from e

#     def _parse_json_response(self, raw: str, fallback: dict | None = None) -> dict:
#         """
#         Extract and parse JSON from LLM response.
#         Handles markdown code fences and trailing text.
#         """
#         # Strip ```json ... ``` fences
#         cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
#         cleaned = re.sub(r"```\s*$", "", cleaned).strip()

#         # Find first { and last } to isolate JSON object
#         start = cleaned.find("{")
#         end = cleaned.rfind("}") + 1
#         if start == -1 or end == 0:
#             logger.warning(f"[{self.name}] No JSON object found in response")
#             return fallback or {}

#         json_str = cleaned[start:end]

#         try:
#             return json.loads(json_str)
#         except json.JSONDecodeError as e:
#             logger.warning(f"[{self.name}] JSON parse error: {e} — returning fallback")
#             return fallback or {}

#     # ─────────────────────────────────────────────
#     # Shared utilities
#     # ─────────────────────────────────────────────

#     def _truncate(self, text: str, max_chars: int = 8000) -> str:
#         """Truncate long text to fit context window budget."""
#         if len(text) > max_chars:
#             logger.warning(f"[{self.name}] Truncating input from {len(text)} to {max_chars} chars")
#             return text[:max_chars] + "\n\n[...truncated for context window]"
#         return text

#     def _log_agent_start(self, **context):
#         details = ", ".join(f"{k}={v}" for k, v in context.items())
#         logger.info(f"[{self.name}] ▶ Starting | {details}")

#     def _log_agent_done(self, result_summary: str = ""):
#         logger.info(f"[{self.name}] ✓ Done | {result_summary}")
from __future__ import annotations

import os
import re
import time
from abc import ABC, abstractmethod
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()


class AgentError(Exception):
    pass


class BaseAgent(ABC):

    def __init__(self, name: str):
        self.name = name
        self.model_name = os.getenv("LLM_MODEL", "gemini-2.0-flash")
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))

        # Create client INSIDE __init__ so dotenv is already loaded
        from google import genai
        self._genai = genai
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        logger.info(f"[{self.name}] Initialized with Gemini ({self.model_name})")

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        ...

    def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        expect_json: bool = True,
    ) -> str:
        from google.genai import types

        start = time.time()
        logger.debug(f"[{self.name}] Calling Gemini (expect_json={expect_json})")

        full_prompt = f"{system_prompt}\n\n{user_message}"

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=30),
        )
        def _make_call():
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                ),
            )
            return response.text

        try:
            result = _make_call()
            elapsed = time.time() - start
            logger.info(f"[{self.name}] Response received in {elapsed:.2f}s")
            return result
        except Exception as e:
            logger.error(f"[{self.name}] Gemini call failed: {e}")
            raise AgentError(f"{self.name} failed: {e}") from e

    def _parse_json_response(self, raw: str, fallback: dict | None = None) -> dict:
        import json
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            return fallback or {}
        try:
            return json.loads(cleaned[start:end])
        except Exception:
            return fallback or {}

    def _truncate(self, text: str, max_chars: int = 8000) -> str:
        if len(text) > max_chars:
            return text[:max_chars] + "\n\n[...truncated]"
        return text

    def _log_agent_start(self, **context):
        details = ", ".join(f"{k}={v}" for k, v in context.items())
        logger.info(f"[{self.name}] ▶ Starting | {details}")

    def _log_agent_done(self, result_summary: str = ""):
        logger.info(f"[{self.name}] ✓ Done | {result_summary}")