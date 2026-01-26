import json
import google.generativeai as genai
from typing import Dict
from app.services.parser_service import InvoiceParser
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class GeminiParser(InvoiceParser):
    """
    Gemini API implementation of InvoiceParser.
    Uses Google's Gemini 1.5 Flash model to extract transaction data from images.
    """
    
    def __init__(self):
        """Initialize Gemini API client with API key from settings."""
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables")
        
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    async def parse(self, image_bytes: bytes) -> Dict:
        """
        Parse invoice/screenshot using Gemini API.
        
        Args:
            image_bytes: Raw image bytes from uploaded file
            
        Returns:
            Dictionary with extracted transaction data
        """
        try:
            # Create prompt that forces JSON response
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
            - Amount should be a number (float), not a string
            - Date should be in YYYY-MM-DD format
            - Category should be a single word or short phrase (e.g., "Food", "Transport", "Shopping", "Coffee")
            - Currency should be ISO code (INR, USD, etc.)
            """
            
            # Create image part for Gemini
            import PIL.Image
            import io
            image = PIL.Image.open(io.BytesIO(image_bytes))
            
            # Generate content
            response = self.model.generate_content([prompt, image])
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                # Remove ```json or ``` markers
                lines = response_text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                response_text = "\n".join(lines)
            
            # Parse JSON
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Gemini response: {response_text}")
                logger.error(f"JSON decode error: {e}")
                # Return default structure with nulls
                return {
                    "merchant": None,
                    "amount": None,
                    "currency": "INR",
                    "date": None,
                    "category": None
                }
            
            # Validate and normalize response
            result = {
                "merchant": data.get("merchant"),
                "amount": data.get("amount"),
                "currency": data.get("currency", "INR"),
                "date": data.get("date"),
                "category": data.get("category")
            }
            
            logger.info(f"Successfully parsed invoice: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing invoice with Gemini: {e}")
            # Return default structure on error
            return {
                "merchant": None,
                "amount": None,
                "currency": "INR",
                "date": None,
                "category": None
            }
