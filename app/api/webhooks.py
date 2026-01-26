from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict
import logging

from app.database import get_db
from app.models import User, Transaction
from app.services.parser_service import get_parser
from app.services.telegram_service import telegram_service
from app.services.text_parser import TextTransactionParser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhooks"])


def get_or_create_user(db: Session, telegram_id: str) -> User:
    """
    Get existing user or create a new one based on Telegram ID.
    
    Args:
        db: Database session
        telegram_id: Telegram user ID
        
    Returns:
        User instance
    """
    user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
    
    if not user:
        user = User(
            telegram_id=str(telegram_id),
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user with telegram_id: {telegram_id}")
    
    return user


@router.post("/telegram")
async def telegram_webhook(
    update: Dict,
    db: Session = Depends(get_db)
):
    """
    Handle incoming Telegram webhook updates.
    Processes image messages, extracts transaction data, and saves to database.
    
    Args:
        update: Telegram webhook update dictionary
        db: Database session from dependency injection
        
    Returns:
        Success response
    """
    try:
        # Extract message and user info
        message = update.get("message")
        if not message:
            logger.warning("Received update without message")
            return {"ok": True}
        
        from_user = message.get("from", {})
        telegram_user_id = from_user.get("id")
        chat_id = message.get("chat", {}).get("id")
        
        if not telegram_user_id:
            logger.warning("Message without user ID")
            return {"ok": True}
        
        # Get or create user
        user = get_or_create_user(db, str(telegram_user_id))
        
        parsed_data = None
        
        # Check for image (photo or document) first
        file_id = await telegram_service.get_file_id_from_message(update)
        
        if file_id:
            # Process image
            await telegram_service.send_message(chat_id, "⏳ Processing your invoice...")
            image_bytes = await telegram_service.download_file(file_id)
            
            if not image_bytes:
                await telegram_service.send_message(
                    chat_id,
                    "❌ Failed to download image. Please try again."
                )
                return {"ok": True}
            
            # Parse invoice using parser service
            parser = get_parser()
            parsed_data = await parser.parse(image_bytes)
            
            # Validate parsed data
            if not parsed_data.get("amount"):
                await telegram_service.send_message(
                    chat_id,
                    "❌ Could not extract transaction amount from the image. Please try with a clearer image."
                )
                return {"ok": True}
        
        else:
            # Check for text message
            text = telegram_service.get_text_from_message(update)
            
            if text:
                # Parse text message for transaction data
                text_parser = TextTransactionParser()
                parsed_data = text_parser.parse(text)
                
                if not parsed_data:
                    await telegram_service.send_message(
                        chat_id,
                        "❌ Could not understand your message. Please send:\n"
                        "• A payment screenshot/invoice image, or\n"
                        "• Text like: 'add 15rs as coffee' or 'spent 50 on food'"
                    )
                    return {"ok": True}
            else:
                # Neither image nor text
                await telegram_service.send_message(
                    chat_id,
                    "📸 Please send:\n"
                    "• A payment screenshot or invoice image, or\n"
                    "• Text like: 'add 15rs as coffee' or 'spent 50 on food'"
                )
                return {"ok": True}
        
        # Create transaction record (for both image and text)
        transaction = Transaction(
            user_id=user.id,
            amount=str(parsed_data.get("amount", "")),
            currency=parsed_data.get("currency", "INR"),
            merchant=parsed_data.get("merchant"),
            category=parsed_data.get("category"),
            source_image_url=None,  # TODO: Store image URL if implementing storage
            status="PENDING"
        )
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        # Format confirmation message
        amount = parsed_data.get("amount", "N/A")
        currency = parsed_data.get("currency", "INR")
        merchant = parsed_data.get("merchant", "Unknown")
        category = parsed_data.get("category", "Uncategorized")
        
        # Format currency symbol
        currency_symbol = "₹" if currency == "INR" else currency
        
        confirmation_message = (
            f"✅ Tracked {currency_symbol}{amount}"
        )
        
        if merchant and merchant != "Unknown":
            confirmation_message += f" at {merchant}"
        
        if category:
            confirmation_message += f" ({category})"
        
        await telegram_service.send_message(chat_id, confirmation_message)
        
        logger.info(f"Successfully processed transaction for user {user.id}: {transaction.id}")
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}", exc_info=True)
        
        # Try to send error message to user if we have chat_id
        try:
            chat_id = update.get("message", {}).get("chat", {}).get("id")
            if chat_id:
                await telegram_service.send_message(
                    chat_id,
                    "❌ An error occurred while processing your request. Please try again later."
                )
        except Exception:
            pass
        
        return {"ok": True}  # Always return ok to Telegram to avoid retries
