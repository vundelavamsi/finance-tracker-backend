import httpx
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    """
    Service for interacting with Telegram Bot API.
    Handles file downloads and sending messages.
    """
    
    def __init__(self):
        """Initialize Telegram service with bot token."""
        if not settings.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables")
        
        self.bot_token = settings.telegram_bot_token
        self.base_url = f"{settings.telegram_api_url}{self.bot_token}"
    
    async def download_file(self, file_id: str) -> Optional[bytes]:
        """
        Download a file from Telegram by file_id.
        
        Args:
            file_id: Telegram file_id from the message
            
        Returns:
            File bytes if successful, None otherwise
        """
        try:
            # First, get file path from Telegram
            async with httpx.AsyncClient() as client:
                # Get file info
                get_file_url = f"{self.base_url}/getFile"
                response = await client.get(
                    get_file_url,
                    params={"file_id": file_id}
                )
                response.raise_for_status()
                file_info = response.json()
                
                if not file_info.get("ok"):
                    logger.error(f"Failed to get file info: {file_info}")
                    return None
                
                file_path = file_info["result"]["file_path"]
                
                # Download the actual file
                download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
                file_response = await client.get(download_url)
                file_response.raise_for_status()
                
                return file_response.content
                
        except Exception as e:
            logger.error(f"Error downloading file from Telegram: {e}")
            return None
    
    async def send_message(self, chat_id: int, text: str) -> bool:
        """
        Send a message to a Telegram user.
        
        Args:
            chat_id: Telegram chat ID (user ID)
            text: Message text to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                send_url = f"{self.base_url}/sendMessage"
                response = await client.post(
                    send_url,
                    json={
                        "chat_id": chat_id,
                        "text": text
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("ok"):
                    return True
                else:
                    logger.error(f"Failed to send message: {result}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending message to Telegram: {e}")
            return False
    
    async def get_file_id_from_message(self, update: dict) -> Optional[str]:
        """
        Extract file_id from a Telegram update message.
        Handles both photo and document messages.
        
        Args:
            update: Telegram webhook update dictionary
            
        Returns:
            file_id if found, None otherwise
        """
        try:
            message = update.get("message", {})
            
            # Check for photo (Telegram sends multiple sizes, get the largest)
            if "photo" in message:
                photos = message["photo"]
                # Get the last (largest) photo
                return photos[-1]["file_id"]
            
            # Check for document
            if "document" in message:
                document = message["document"]
                # Check if it's an image
                mime_type = document.get("mime_type", "")
                if mime_type.startswith("image/"):
                    return document["file_id"]
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting file_id from message: {e}")
            return None
    
    def get_text_from_message(self, update: dict) -> Optional[str]:
        """
        Extract text from a Telegram update message.
        
        Args:
            update: Telegram webhook update dictionary
            
        Returns:
            Text content if found, None otherwise
        """
        try:
            message = update.get("message", {})
            
            # Check for text message
            if "text" in message:
                return message["text"]
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting text from message: {e}")
            return None


# Create singleton instance
telegram_service = TelegramService()
