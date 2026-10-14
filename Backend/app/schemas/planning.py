from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Money = Annotated[Decimal, Field(ge=0, le=1000000000, decimal_places=2, allow_inf_nan=False)]
CATEGORIES = ("Rent", "Food", "Transport", "Bills", "Debt payments", "Entertainment", "Shopping", "Subscriptions", "Other")


class PlanningInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    income: Money | None = Field(default=None, description="Monthly take-home income explicitly provided by user, NOT savings or goal progress.")
    other_income: Money | None = Field(default=None, description="Additional monthly household income; zero only if user explicitly says none.")
    household_size: int | None = Field(default=None, ge=1, le=100, strict=True)
    goal: str | None = Field(default=None, min_length=1, max_length=200)
    goal_kind: Literal["savings", "debt", "spending"] | None = None
    target_amount: Money | None = None
    current_amount: Money | None = Field(default=None, description="Money ALREADY saved or paid toward this goal, never salary or monthly income.")
    preferred_monthly_savings: Money | None = Field(
        default=None,
        description="Optional amount the user wants to contribute monthly toward a savings goal. None means use the amount required by the deadline."
    )
    deadline: date | None = Field(default=None, description="User requested future target date YYYY-MM-DD. Never invent a deadline.")
    monthly_contribution: Money | None = Field(default=None, description="Monthly savings contribution explicitly chosen by the user for this goal, NOT income or money already saved. Must be positive.")
    # Only months explicitly marked complete/typical may establish a baseline.
    typical_months: list[str] = Field(default_factory=list, max_length=12)
    expenses: dict[str, Money | None] = Field(default_factory=dict, description="Baseline monthly costs explicitly stated by user. Allowed category names: Rent, Food, Transport, Bills, Debt payments, Entertainment, Shopping, Subscriptions, Other. Never invent zero costs.")
    protected_categories: list[str] = Field(default_factory=list, max_length=9)

    @model_validator(mode="after")
    def validate_profile(self):
        import re
        if self.monthly_contribution is not None and self.monthly_contribution <= 0:
            raise ValueError("Choose a positive monthly contribution")
        if any(key not in CATEGORIES for key in self.expenses) or any(key not in CATEGORIES for key in self.protected_categories):
            raise ValueError("Unknown expense category")
        if any(not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", month) or int(month[:4]) < 1 for month in self.typical_months):
            raise ValueError("Use YYYY-MM for typical months")
        if len(set(self.typical_months)) != len(self.typical_months):
            raise ValueError("Choose each typical month only once")
        if self.goal is not None and not self.goal.strip():
            raise ValueError("Describe your main goal")
        if self.preferred_monthly_savings is not None and self.goal_kind != "savings":
            raise ValueError("Preferred monthly savings is only available for savings goals")
        return self
