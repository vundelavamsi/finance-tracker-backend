from abc import ABC, abstractmethod
from typing import Dict
from app.config import settings


class InvoiceParser(ABC):
    """
    Abstract base class for invoice parsers.
    This interface allows switching between different parsing implementations
    (Gemini, OCR, etc.) without changing the calling code.
    Supports both image (invoice/screenshot) and text message parsing.
    """

    @abstractmethod
    async def parse(self, image_bytes: bytes) -> Dict:
        """
        Parse an invoice/screenshot image and extract transaction data.

        Args:
            image_bytes: Raw image bytes from the uploaded file

        Returns:
            Dictionary with extracted data:
            {
                "merchant": str,
                "amount": float (negative = expense, positive = income),
                "currency": str,
                "date": str (YYYY-MM-DD),
                "category": str
            }
        """
        pass

    @abstractmethod
    async def parse_text(self, text: str) -> Dict:
        """
        Parse a text message and extract transaction data.

        Args:
            text: User's text message (e.g. "spent 50 on food", "add 100 as salary")

        Returns:
            Dictionary with extracted data (same shape as parse).
            amount: negative for expense, positive for income.
        """
        pass


def get_parser() -> InvoiceParser:
    """
    Factory function to get the appropriate parser based on configuration.
    
    Returns:
        Instance of InvoiceParser implementation
    """
    parser_type = settings.parser_type.upper()
    
    if parser_type == "LOCAL":
        # TODO: Implement LocalOCRParser
        # from app.services.local_ocr_parser import LocalOCRParser
        # return LocalOCRParser()
        raise NotImplementedError("Local OCR parser not yet implemented")
    else:
        # Default to Gemini parser
        from app.services.gemini_parser import GeminiParser
        return GeminiParser()
