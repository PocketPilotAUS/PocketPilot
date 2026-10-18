"""Add durable Financial Plan reviews without changing existing financial records."""
from app.database import engine
from app.models.user import User
from app.models.plan_review import PlanReview

if __name__ == "__main__":
    PlanReview.__table__.create(bind=engine, checkfirst=True)
    print("Financial Plan review table is ready.")
