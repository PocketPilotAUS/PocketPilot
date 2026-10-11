
import logging
import math

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from datetime import date
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.core.config import ConfigurationError
from app.database import MAX_DATABASE_ID, get_db
from app.dependencies import CurrentUser
from app.routers import auth, chat, budget, proposals, recurring, planning
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionResponse

from app.ai.explanation import prepare_ai_explanation
from app.ai.client import generate_ai_explanation

from app.algorithms.spending_analysis import (
    calculate_total_spending,
    calculate_category_spending,
    calculate_category_percentages,
    compare_monthly_spending
)

from app.algorithms.recommendations import generate_spending_recommendations

logger = logging.getLogger(__name__)

app = FastAPI(title="PocketPilot API")

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(budget.router)
app.include_router(proposals.router)
app.include_router(recurring.router)
app.include_router(planning.router)


@app.exception_handler(ConfigurationError)
def configuration_error_handler(request: Request, error: ConfigurationError):
    # Full reason goes to the server log only; clients get a generic message
    logger.error("Server configuration error: %s", error)

    return JSONResponse(
        status_code=503,
        content={"detail": "Authentication is not configured on the server."}
    )


def json_safe(value):
    # JSON cannot represent infinity or NaN, so they are returned as text
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)

    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    return value


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError):
    # Same response format as FastAPI's default handler, with two changes:
    # auth requests contain passwords, so submitted values ("input") are never
    # echoed back; elsewhere, values like infinity are made JSON-safe, since
    # the default handler would crash with a 500 trying to echo them.
    if request.url.path.startswith(auth.router.prefix + "/"):
        errors = [
            {key: value for key, value in detail.items() if key != "input"}
            for detail in error.errors()
        ]
    else:
        errors = json_safe(error.errors())

    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(errors)}
    )


def user_transactions(db: Session, user: User):
    recurring.sync_recurring(db, user.id)
    # Every transaction query goes through this filter. Unowned legacy
    # rows (user_id NULL) never match, so they stay hidden from everyone.
    return db.query(Transaction).filter(Transaction.user_id == user.id)


@app.get("/")
def root():
    return {"message": "PocketPilot API is running"}


@app.post("/transactions/", response_model=TransactionResponse, status_code=201)
def create_transaction(
    transaction: TransactionCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    # The owner always comes from the verified token, never the request body
    new_transaction = Transaction(
        **transaction.model_dump(),
        user_id=current_user.id
    )

    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    return new_transaction


@app.get("/transactions/", response_model=list[TransactionResponse])
def get_transactions(
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    return user_transactions(db, current_user).order_by(Transaction.id).all()


@app.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    # IDs too large for SQLite cannot exist; checking first avoids an error
    if 1 <= transaction_id <= MAX_DATABASE_ID:
        transaction = user_transactions(db, current_user).filter(
            Transaction.id == transaction_id
        ).first()
    else:
        transaction = None

    # Another user's transaction gets the same 404 as a missing one,
    # so IDs belonging to other users cannot be discovered
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()

    return {"message": "Transaction deleted successfully"}


@app.get("/spending/summary")
def get_spending_summary(
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    transactions = user_transactions(db, current_user).all()

    transaction_data = [
        {
            "amount": transaction.amount,
            "category": transaction.category
        }
        for transaction in transactions
    ]

    if not transaction_data:
        return {
            "total_spending": 0,
            "category_spending": {},
            "category_percentages": {}
        }

    return {
        "total_spending": calculate_total_spending(transaction_data),
        "category_spending": calculate_category_spending(transaction_data),
        "category_percentages": calculate_category_percentages(transaction_data)
    }


@app.get("/spending/compare")
def compare_spending(
    year: int,
    month: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    if year < 2 or year > 9999 or month < 1 or month > 12:
        raise HTTPException(
            status_code=422,
            detail="Enter a valid year and month."
        )

    # Determine the previous month
    if month == 1:
        previous_month = 12
        previous_year = year - 1
    else:
        previous_month = month - 1
        previous_year = year

    # Retrieve transactions for the selected month
    current_transactions = user_transactions(db, current_user).filter(
        extract("year", Transaction.date) == year,
        extract("month", Transaction.date) == month
    ).all()

    # Retrieve transactions for the previous month
    previous_transactions = user_transactions(db, current_user).filter(
        extract("year", Transaction.date) == previous_year,
        extract("month", Transaction.date) == previous_month
    ).all()

    # Convert database records into the format used by our algorithms
    current_data = [
        {"category": t.category, "amount": t.amount}
        for t in current_transactions
    ]

    previous_data = [
        {"category": t.category, "amount": t.amount}
        for t in previous_transactions
    ]

    changes = compare_monthly_spending(
        current_data,
        previous_data
    )

    return {
        "year": year,
        "month": month,
        "previous_year": previous_year,
        "previous_month": previous_month,
        "current_spending": calculate_category_spending(current_data),
        "previous_spending": calculate_category_spending(previous_data),
        "percentage_changes": changes
    }


@app.get("/recommendations/")
def get_recommendations(
    year: int,
    month: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    if year < 2 or year > 9999 or month < 1 or month > 12:
        raise HTTPException(
            status_code=422,
            detail="Enter a valid year and month."
        )

    # Reuse the existing monthly comparison endpoint logic
    comparison = compare_spending(year, month, current_user, db)

    # Generate recommendations from calculated percentage changes
    recommendations = generate_spending_recommendations(
        comparison["percentage_changes"]
    )

    return {
        "year": year,
        "month": month,
        "recommendations": recommendations
    }


@app.get("/recommendations/ai")
def get_ai_recommendations(
    year: int,
    month: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    # Retrieve recommendations based on saved transactions
    result = get_recommendations(year, month, current_user, db)

    ai_recommendations = []

    for recommendation in result["recommendations"]:
        # Prepare the prompt using verified calculations
        prompt = prepare_ai_explanation(recommendation)

        try:
            # Request an explanation from Qwen3
            explanation = generate_ai_explanation(prompt)

        except Exception:
            raise HTTPException(
                status_code=503,
                detail="AI explanations are temporarily unavailable. Please check the Ollama server."
            )

        ai_recommendations.append({
            "category": recommendation["category"],
            "priority": recommendation["priority"],
            "percentage_change": recommendation["percentage_change"],
            "recommendation": recommendation["message"],
            "ai_explanation": explanation
        })

    return {
        "year": year,
        "month": month,
        "ai_recommendations": ai_recommendations
    }
