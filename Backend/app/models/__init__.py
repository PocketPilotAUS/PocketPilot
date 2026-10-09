# Importing both models here registers them together, so the string-based
# relationships ("User" <-> "Transaction") resolve no matter which model
# module the rest of the app imports first.
from app.models.transaction import Transaction
from app.models.user import User

__all__ = ["Transaction", "User"]
