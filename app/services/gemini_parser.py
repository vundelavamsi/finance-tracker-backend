import asyncio
import io
import json
import logging
import re
from typing import Dict

from google import genai
from PIL import Image

from app.config import settings
from app.services.parser_service import InvoiceParser

logger = logging.getLogger(__name__)

# Default structure when parsing fails
_DEFAULT_RESULT = {
    "merchant": None,
    "amount": None,
    "currency": "INR",
    "date": None,
    "category": None,
}

# Key added to result when Gemini returns 429 (quota/rate limit)
RATE_LIMIT_KEY = "_rate_limit"

# Retry: wait up to this many seconds when we get 429, then retry once
RETRY_DELAY_MAX = 60


def _parse_retry_seconds(error_message: str) -> int:
    """Extract 'retry in X.XXs' from Gemini 429 message; else return RETRY_DELAY_MAX."""
    match = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", error_message, re.IGNORECASE)
    if match:
        return min(int(float(match.group(1)) + 1), RETRY_DELAY_MAX)
    return RETRY_DELAY_MAX


def _is_rate_limit_error(e: Exception) -> bool:
    return "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)


def _extract_json_from_response(response_text: str) -> Dict:
    """Strip markdown code blocks and parse JSON from model response."""
    text = (response_text or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON: {text[:200]}")


def _get_response_text(response) -> str:
    """Get text from Gemini generate_content response."""
    if hasattr(response, "text") and response.text:
        return response.text
    if getattr(response, "candidates", None):
        c = response.candidates[0]
        if getattr(c, "content", None) and getattr(c.content, "parts", None) and c.content.parts:
            return getattr(c.content.parts[0], "text", "") or ""
    return ""


class GeminiParser(InvoiceParser):
    """
    Gemini API implementation of InvoiceParser.
    Uses Google's Gemini model (google-genai SDK) for images and text.
    """

    def __init__(self):
        """Initialize Gemini API client with API key from settings."""
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = getattr(settings, "gemini_model", None) or "gemini-2.0-flash"

    async def _generate_with_retry(self, contents) -> tuple[object | None, bool]:
        """
        Call Gemini generate_content with one retry on 429.
        Returns (response, rate_limited). If rate_limited is True, response is None.
        """
        last_error = None
        for attempt in range(2):
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=contents,
                )
                return (response, False)
            except Exception as e:
                last_error = e
                if not _is_rate_limit_error(e):
                    raise
                if attempt == 0:
                    delay = _parse_retry_seconds(str(e))
                    logger.warning(f"Gemini rate limit (429), retrying after {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Gemini still rate limited after retry: {last_error}")
                    return (None, True)
        return (None, True)

    async def parse(self, image_bytes: bytes) -> Dict:
        """
        Parse invoice/screenshot using Gemini API.

        Args:
            image_bytes: Raw image bytes from uploaded file

        Returns:
            Dictionary with extracted transaction data (may include _rate_limit if 429 after retry)
        """
        try:
            prompt = """
            Analyze this image (invoice or payment screenshot).
            Extract the following details in strict JSON format only (no Markdown, no code blocks):
            {
                "merchant": "string or null",
                "amount": float or null,
                "currency": "string (ISO code, default INR) or null",
                "date": "YYYY-MM-DD or null",
                "category": "string (guess based on merchant name) or null"
            }

            Rules:
            - Return ONLY valid JSON, no other text
            - If a field cannot be determined, use null
            - Amount: use a number (float). For expenses/payments/outgoing use NEGATIVE (e.g. -50). For income/refunds use POSITIVE (e.g. 100). Receipts and invoices are usually expenses.
            - Date should be in YYYY-MM-DD format
            - Category should be a single word or short phrase (e.g., "Food", "Transport", "Shopping", "Coffee")
            - Currency should be ISO code (INR, USD, etc.)
            """
            image = Image.open(io.BytesIO(image_bytes))
            response, rate_limited = await self._generate_with_retry([prompt.strip(), image])
            if rate_limited:
                out = _DEFAULT_RESULT.copy()
                out[RATE_LIMIT_KEY] = True
                return out
            response_text = _get_response_text(response)
            data = _extract_json_from_response(response_text)
            result = {
                "merchant": data.get("merchant"),
                "amount": data.get("amount"),
                "currency": data.get("currency", "INR"),
                "date": data.get("date"),
                "category": data.get("category"),
            }
            logger.info(f"Successfully parsed invoice: {result}")
            return result

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse JSON from Gemini response: {e}")
            return _DEFAULT_RESULT.copy()
        except Exception as e:
            if _is_rate_limit_error(e):
                out = _DEFAULT_RESULT.copy()
                out[RATE_LIMIT_KEY] = True
                return out
            logger.error(f"Error parsing invoice with Gemini: {e}")
            return _DEFAULT_RESULT.copy()

    async def parse_text(self, text: str) -> Dict:
        """
        Parse a text message using Gemini to extract transaction data.
        Uses amount sign: negative = expense, positive = income.
        """
        if not text or not text.strip():
            return _DEFAULT_RESULT.copy()

        prompt = """
        The user is logging a financial transaction in a short message.
        Extract the following in strict JSON only (no Markdown, no code blocks):
        {
            "merchant": "string or null",
            "amount": number,
            "currency": "string (ISO code, default INR) or null",
            "date": "YYYY-MM-DD or null",
            "category": "string or null"
        }

        Rules:
        - Return ONLY valid JSON, no other text.
        - Amount MUST reflect income vs expense:
          - Use NEGATIVE number for: spent, paid, expense, bought, cost, withdrew, etc. (e.g. -50, -100.5)
          - Use POSITIVE number for: add, received, income, salary, refund, credited, etc. (e.g. 100, 5000)
        - If intent is unclear, prefer expense (negative).
        - If no amount can be inferred, use null.
        - Currency default INR if not stated.
        - Category: single word or short phrase (Food, Transport, Salary, etc.) or null.
        - Date: YYYY-MM-DD if mentioned, else null.
        """
        full_prompt = f"{prompt.strip()}\n\nUser message: {text.strip()}"

        try:
            response, rate_limited = await self._generate_with_retry(full_prompt)
            if rate_limited:
                out = _DEFAULT_RESULT.copy()
                out[RATE_LIMIT_KEY] = True
                return out
            response_text = _get_response_text(response)
            data = _extract_json_from_response(response_text)
            result = {
                "merchant": data.get("merchant"),
                "amount": data.get("amount"),
                "currency": data.get("currency", "INR"),
                "date": data.get("date"),
                "category": data.get("category"),
            }
            logger.info(f"Successfully parsed text transaction: {result}")
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse JSON from Gemini text response: {e}")
            return _DEFAULT_RESULT.copy()
        except Exception as e:
            if _is_rate_limit_error(e):
                out = _DEFAULT_RESULT.copy()
                out[RATE_LIMIT_KEY] = True
                return out
            logger.error(f"Error parsing text with Gemini: {e}")
            return _DEFAULT_RESULT.copy()
