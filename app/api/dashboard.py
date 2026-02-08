from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Dict, List
from datetime import datetime, date, timedelta
import logging

from app.database import get_db
from app.models import Transaction, Account, Category, User
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get dashboard statistics including:
    - Total income/expenses
    - Monthly breakdown
    - Category-wise spending
    - Account balances
    - Recent transactions
    """
    try:
        # Get all transactions for the user
        transactions = db.query(Transaction).filter(
            Transaction.user_id == current_user.id
        ).all()
        
        # Calculate totals (assuming negative amounts are expenses, positive are income)
        total_income = 0.0
        total_expenses = 0.0
        
        for txn in transactions:
            try:
                amount = float(txn.amount)
                if amount > 0:
                    total_income += amount
                else:
                    total_expenses += abs(amount)
            except (ValueError, TypeError):
                continue
        
        net_balance = total_income - total_expenses
        
        # Monthly breakdown (last 6 months)
        monthly_data = []
        for i in range(6):
            month_start = (datetime.now() - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # End of last day (23:59:59.999999) so transactions on the last day are included
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(microseconds=1)
            
            month_transactions = [t for t in transactions 
                                 if month_start <= t.created_at <= month_end]
            
            month_income = sum(float(t.amount) for t in month_transactions 
                             if float(t.amount) > 0)
            month_expenses = sum(abs(float(t.amount)) for t in month_transactions 
                               if float(t.amount) < 0)
            
            monthly_data.append({
                "month": month_start.strftime("%Y-%m"),
                "income": month_income,
                "expenses": month_expenses
            })
        
        monthly_data.reverse()  # Oldest to newest
        
        # Category-wise spending (only expense transactions, by category)
        category_spending = {}
        for txn in transactions:
            if txn.category_id and txn.category:
                try:
                    amt = float(txn.amount)
                    if amt < 0:  # Only count expenses (negative amounts)
                        amount = abs(amt)
                        category_name = txn.category.name
                        category_spending[category_name] = category_spending.get(category_name, 0) + amount
                except (ValueError, TypeError):
                    continue
        
        category_breakdown = [
            {"name": name, "amount": amount, "color": db.query(Category).filter(Category.name == name).first().color if db.query(Category).filter(Category.name == name).first() else "#6366f1"}
            for name, amount in sorted(category_spending.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Account balances
        accounts = db.query(Account).filter(
            Account.user_id == current_user.id,
            Account.is_active == True
        ).all()
        
        account_balances = [
            {
                "id": acc.id,
                "name": acc.name,
                "type": acc.account_type.value if hasattr(acc.account_type, 'value') else str(acc.account_type),
                "balance": float(acc.balance),
                "currency": acc.currency
            }
            for acc in accounts
        ]
        
        # Recent transactions (last 10)
        recent_transactions = db.query(Transaction).filter(
            Transaction.user_id == current_user.id
        ).order_by(Transaction.created_at.desc()).limit(10).all()
        
        recent_txns = []
        for txn in recent_transactions:
            recent_txns.append({
                "id": txn.id,
                "amount": txn.amount,
                "currency": txn.currency,
                "merchant": txn.merchant,
                "category": txn.category.name if txn.category else None,
                "account": txn.account.name if txn.account else None,
                "date": txn.created_at.isoformat()
            })
        
        return {
            "summary": {
                "total_income": total_income,
                "total_expenses": total_expenses,
                "net_balance": net_balance,
                "accounts_count": len(accounts)
            },
            "monthly_breakdown": monthly_data,
            "category_breakdown": category_breakdown,
            "account_balances": account_balances,
            "recent_transactions": recent_txns
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard statistics")
