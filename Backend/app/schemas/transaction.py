
from datetime import date
from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    amount: float = Field(gt=0)
    category: str = Field(min_length=1)
    description: str | None = None
    date: date


class TransactionResponse(TransactionCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)
