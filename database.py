"""
database.py
SQLAlchemy database setup and models for Personal Budget Monitoring System (TracSy).
Defines User and Transaction models with relationships.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

# ─────────────────────────────────────────────
# Detect environment
# Streamlit Cloud sets HOME=/home/appuser
# Locally HOME is your own user path
# ─────────────────────────────────────────────
IS_CLOUD = (
    os.getenv("STREAMLIT_SHARING_MODE") == "streamlit"
    or os.getenv("HOME") == "/home/appuser"
)

if IS_CLOUD:
    DB_FILE = "/tmp/finance.db"
else:
    # Always write next to this file so you can open it in DB Browser
    DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "finance.db")

DATABASE_URL = f"sqlite:///{DB_FILE}"

print(f"[TracSy] Using database at: {DB_FILE}")

# ─────────────────────────────────────────────
# Engine + Session
# ─────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
class User(Base):
    """
    User model for storing user authentication information.
    Each user has a unique username and hashed password.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(128), nullable=False)  # SHA-256 hashed

    transactions = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Transaction(Base):
    """
    Transaction model for storing income and expense records.
    Each transaction belongs to a specific user.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)
    transaction_type = Column(String(10), nullable=False)  # 'Income' or 'Expense'

    user = relationship("User", back_populates="transactions")

    def __repr__(self):
        return (
            f"<Transaction(id={self.id}, user_id={self.user_id}, "
            f"type={self.transaction_type}, amount={self.amount})>"
        )


# ─────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────
def init_db():
    """Create all tables if they don't exist. Call on app startup."""
    Base.metadata.create_all(bind=engine)
    print("[TracSy] Database initialized successfully!")


def get_db():
    """Return a new database session."""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e


def add_transaction(user_id, t_date, amount, category, desc, t_type):
    """
    Save a transaction to the database.
    Returns (True, success_message) or (False, error_message).
    """
    # ── Guard: never allow a missing user_id ──────────────────────────────
    if not user_id:
        return False, "No user is logged in. Cannot save transaction."

    db = SessionLocal()
    try:
        transaction = Transaction(
            user_id=user_id,          # never fall back to a hardcoded value
            date=t_date,
            amount=amount,
            category=category,
            description=desc,
            transaction_type=t_type,
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return True, "Transaction saved successfully!"

    except Exception as e:
        db.rollback()                 # ← roll back on any error
        return False, str(e)

    finally:
        db.close()                    # ← always close, even on error


def get_user_by_username(username: str):
    """Fetch a User row by username. Returns None if not found."""
    db = SessionLocal()
    try:
        return db.query(User).filter(User.username == username).first()
    finally:
        db.close()


def get_transactions_by_user(user_id: int):
    """Return all transactions for a given user_id, newest first."""
    db = SessionLocal()
    try:
        return (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id)
            .order_by(Transaction.date.desc())
            .all()
        )
    finally:
        db.close()
