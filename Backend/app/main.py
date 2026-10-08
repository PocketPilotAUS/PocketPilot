
from fastapi import FastAPI, Depends, HTTPException
from datetime import date
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.transaction import Transaction
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

app = FastAPI(title="PocketPilot API")


@app.get("/")
def root():
    return {"message": "PocketPilot API is running"}


@app.post("/transactions/", response_model=TransactionResponse, status_code=201)
def create_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db)
):
    new_transaction = Transaction(**transaction.model_dump())

    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    return new_transaction


@app.get("/transactions/", response_model=list[TransactionResponse])
def get_transactions(db: Session = Depends(get_db)):
    return db.query(Transaction).order_by(Transaction.id).all()


@app.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    transaction = db.get(Transaction, transaction_id)

    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()

    return {"message": "Transaction deleted successfully"}


@app.get("/spending/summary")
def get_spending_summary(db: Session = Depends(get_db)):
    transactions = db.query(Transaction).all()

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
    db: Session = Depends(get_db)
):
    if year < 2 or month < 1 or month > 12:
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
    current_transactions = db.query(Transaction).filter(
        extract("year", Transaction.date) == year,
        extract("month", Transaction.date) == month
    ).all()

    # Retrieve transactions for the previous month
    previous_transactions = db.query(Transaction).filter(
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
    db: Session = Depends(get_db)
):
    if year < 2 or month < 1 or month > 12:
        raise HTTPException(
            status_code=422,
            detail="Enter a valid year and month."
        )

    # Reuse the existing monthly comparison endpoint logic
    comparison = compare_spending(year, month, db)

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
    db: Session = Depends(get_db)
):
    # Retrieve recommendations based on saved transactions
    result = get_recommendations(year, month, db)

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
