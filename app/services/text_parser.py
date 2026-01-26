import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TextTransactionParser:
    """
    Parser for extracting transaction data from text messages.
    Handles formats like:
    - "add 15rs as coffee"
    - "15 coffee"
    - "₹15 coffee"
    - "15 INR coffee"
    - "spent 50 on food"
    """
    
    @staticmethod
    def parse(text: str) -> Optional[Dict]:
        """
        Parse text message to extract transaction data.
        
        Args:
            text: User's text message
            
        Returns:
            Dictionary with parsed data or None if parsing fails
        """
        if not text or not text.strip():
            return None
        
        text = text.strip().lower()
        
        # Remove common prefixes
        prefixes = ["add", "spent", "spend", "paid", "expense", "exp"]
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        
        # Extract amount (supports various formats)
        amount_patterns = [
            r'(\d+\.?\d*)\s*(?:rs|rupees?|inr|₹)',  # "15rs", "15 rupees", "15 INR", "₹15"
            r'₹\s*(\d+\.?\d*)',  # "₹15"
            r'(\d+\.?\d*)\s*(?:rs|rupees?|inr)',  # "15 rs"
            r'(\d+\.?\d*)',  # Just number
        ]
        
        amount = None
        remaining_text = text
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount = float(match.group(1))
                    # Remove the matched part from text to get category
                    remaining_text = text[:match.start()] + text[match.end():]
                    remaining_text = remaining_text.strip()
                    break
                except ValueError:
                    continue
        
        if amount is None:
            # Try to find just a number at the start
            number_match = re.match(r'^(\d+\.?\d*)', text)
            if number_match:
                try:
                    amount = float(number_match.group(1))
                    remaining_text = text[number_match.end():].strip()
                except ValueError:
                    pass
        
        if amount is None:
            return None
        
        # Extract category from remaining text
        category = None
        merchant = None
        
        # Remove common connectors
        connectors = ["as", "for", "on", "at", "to", "from"]
        for connector in connectors:
            if remaining_text.startswith(connector + " "):
                remaining_text = remaining_text[len(connector):].strip()
        
        if remaining_text:
            # Split by common separators
            parts = re.split(r'[,\s]+', remaining_text, maxsplit=1)
            category = parts[0].strip() if parts else None
            
            # If there's more text, it might be merchant
            if len(parts) > 1 and parts[1].strip():
                merchant = parts[1].strip()
        
        # If no category found, use "Uncategorized"
        if not category:
            category = "Uncategorized"
        
        return {
            "amount": amount,
            "currency": "INR",
            "merchant": merchant,
            "category": category,
            "date": None  # Text messages don't have date
        }
