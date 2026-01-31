from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime, date
import logging

from app.database import get_db
from app.models import Transaction, Category, Account, User
from app.schemas import TransactionResponse, TransactionCreate, TransactionUpdate
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=List[TransactionResponse])
async def get_transactions(
    start_date: Optional[date] = Query(None, description="Filter transactions from this date"),
    end_date: Optional[date] = Query(None, description="Filter transactions until this date"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    account_id: Optional[int] = Query(None, description="Filter by account ID"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of transactions with optional filters.
    """
    try:
        query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
        
        # Apply filters
        if start_date:
            query = query.filter(Transaction.created_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(Transaction.created_at <= datetime.combine(end_date, datetime.max.time()))
        if category_id:
            query = query.filter(Transaction.category_id == category_id)
        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        
        # Order by created_at descending
        query = query.order_by(Transaction.created_at.desc())
        
        # Apply pagination
        transactions = query.offset(offset).limit(limit).all()
        
        return transactions
        
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch transactions")


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a single transaction by ID.
    """
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return transaction


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new transaction.
    """
    try:
        # Validate category if provided
        if transaction.category_id:
            category = db.query(Category).filter(
                Category.id == transaction.category_id,
                Category.user_id == current_user.id
            ).first()
            if not category:
                raise HTTPException(status_code=404, detail="Category not found")
        
        # Validate account if provided
        if transaction.account_id:
            account = db.query(Account).filter(
                Account.id == transaction.account_id,
                Account.user_id == current_user.id
            ).first()
            if not account:
                raise HTTPException(status_code=404, detail="Account not found")
        
        # Create transaction
        db_transaction = Transaction(
            user_id=current_user.id,
            amount=transaction.amount,
            currency=transaction.currency,
            merchant=transaction.merchant,
            category_id=transaction.category_id,
            account_id=transaction.account_id,
            source_image_url=transaction.source_image_url,
            status=transaction.status
        )
        
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
        
        return db_transaction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating transaction: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create transaction")


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    transaction_update: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing transaction.
    """
    db_transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    try:
        # Validate category if provided
        if transaction_update.category_id is not None:
            if transaction_update.category_id:
                category = db.query(Category).filter(
                    Category.id == transaction_update.category_id,
                    Category.user_id == current_user.id
                ).first()
                if not category:
                    raise HTTPException(status_code=404, detail="Category not found")
        
        # Validate account if provided
        if transaction_update.account_id is not None:
            if transaction_update.account_id:
                account = db.query(Account).filter(
                    Account.id == transaction_update.account_id,
                    Account.user_id == current_user.id
                ).first()
                if not account:
                    raise HTTPException(status_code=404, detail="Account not found")
        
        # Update fields
        update_data = transaction_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_transaction, field, value)
        
        db.commit()
        db.refresh(db_transaction)
        
        return db_transaction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating transaction: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update transaction")


@router.delete("/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a transaction.
    """
    db_transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    try:
        db.delete(db_transaction)
        db.commit()
        return None
        
    except Exception as e:
        logger.error(f"Error deleting transaction: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete transaction")
