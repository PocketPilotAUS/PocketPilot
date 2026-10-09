
from datetime import date
from pydantic import BaseModel, ConfigDict, Field

MAX_TRANSACTION_AMOUNT = 1_000_000_000


class TransactionCreate(BaseModel):
    # Unknown fields (including user_id) are rejected; the owner always
    # comes from the authenticated user's token
    model_config = ConfigDict(extra="forbid")

    # Infinity, or huge amounts whose totals overflow to infinity, would be
    # stored and then break every spending calculation for that user
    amount: float = Field(gt=0, le=MAX_TRANSACTION_AMOUNT, allow_inf_nan=False)
    category: str = Field(min_length=1)
    description: str | None = None
    date: date


class TransactionResponse(TransactionCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)
