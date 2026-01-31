from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database import get_db
from app.models import Account, User
from app.schemas import AccountResponse, AccountCreate, AccountUpdate
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=List[AccountResponse])
async def get_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of all accounts for the current user.
    """
    try:
        accounts = db.query(Account).filter(
            Account.user_id == current_user.id,
            Account.is_active == True
        ).order_by(Account.created_at.desc()).all()
        
        return accounts
        
    except Exception as e:
        logger.error(f"Error fetching accounts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch accounts")


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a single account by ID.
    """
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return account


@router.post("", response_model=AccountResponse, status_code=201)
async def create_account(
    account: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new account.
    """
    try:
        db_account = Account(
            user_id=current_user.id,
            name=account.name,
            account_type=account.account_type,
            balance=account.balance,
            currency=account.currency,
            is_active=account.is_active
        )
        
        db.add(db_account)
        db.commit()
        db.refresh(db_account)
        
        return db_account
        
    except Exception as e:
        logger.error(f"Error creating account: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create account")


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    account_update: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing account.
    """
    db_account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    try:
        # Update fields
        update_data = account_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_account, field, value)
        
        db.commit()
        db.refresh(db_account)
        
        return db_account
        
    except Exception as e:
        logger.error(f"Error updating account: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update account")


@router.delete("/{account_id}", status_code=204)
async def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft delete an account (set is_active to False).
    """
    db_account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    try:
        # Soft delete
        db_account.is_active = False
        db.commit()
        return None
        
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete account")
