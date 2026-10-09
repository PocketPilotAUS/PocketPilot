
from app.database import Base, engine
from app.models.transaction import Transaction
from app.models.user import User

Base.metadata.create_all(bind=engine)

print("PocketPilot database tables created successfully!")
