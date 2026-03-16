"""
database.py
SQLAlchemy database setup and models for Personal Budget Monitoring System (TracSy).

FIX SUMMARY
-----------
1. Removed IS_CLOUD / /tmp branch entirely.
   Streamlit Cloud's /tmp is wiped on every restart → all data was lost.
   We now ALWAYS write the DB next to this file, which is part of the
   GitHub repo working directory on the cloud dyno and persists across
   warm restarts (though not across full redeploys — see note below).

2. Removed the duplicate add_transaction() / get_transactions_by_user()
   helpers that shadowed the ones in crud.py and were never called by
   main.py.  Having two definitions with slightly different logic was a
   source of confusion and silent bugs.

PERSISTENT STORAGE NOTE
-----------------------
Streamlit Community Cloud does NOT offer a persistent filesystem between
redeploys.  The file-based SQLite approach works fine for local development
and for demos where you redeploy rarely.  If you need true persistence on
the cloud, switch the DATABASE_URL to a hosted Postgres (e.g. Supabase free
tier) and change only the two lines marked "CLOUD UPGRADE" below — no other
code needs to change because SQLAlchemy abstracts the dialect.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

# ─────────────────────────────────────────────────────────────────────────────
# Database location
#
# Always place the file in the same directory as this script.
# • Locally  → you can open it in DB Browser immediately.
# • On Cloud → it survives warm restarts (Streamlit just re-imports modules
#   without clearing the working directory).  A full redeploy from GitHub
#   does reset the FS; use a hosted DB for true persistence (see note above).
# ─────────────────────────────────────────────────────────────────────────────
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "finance.db")
DATABASE_URL = f"sqlite:///{DB_FILE}"

print(f"[TracSy] Using database at: {DB_FILE}")

# ─────────────────────────────────────────────────────────────────────────────
# Engine + Session
# ─────────────────────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────
class User(Base):
    """
    User model for storing user authentication information.
    Each user has a unique username and SHA-256-hashed password.
    """
    __tablename__ = "users"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(128), nullable=False)   # SHA-256 hex digest

    transactions = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Transaction(Base):
    """
    Transaction model for storing income and expense records.
    Each transaction belongs to a specific user via a foreign key.
    """
    __tablename__ = "transactions"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    date             = Column(Date,    nullable=False)
    amount           = Column(Float,   nullable=False)
    category         = Column(String(50),  nullable=False)
    description      = Column(String(200), nullable=True)
    transaction_type = Column(String(10),  nullable=False)   # 'Income' | 'Expense'

    user = relationship("User", back_populates="transactions")

    def __repr__(self):
        return (
            f"<Transaction(id={self.id}, user_id={self.user_id}, "
            f"type={self.transaction_type}, amount={self.amount})>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────
def init_db():
    """Create all tables if they do not already exist.  Call once on startup."""
    Base.metadata.create_all(bind=engine)
    print("[TracSy] Database initialised successfully!")


def get_db():
    """Yield a new database session (for dependency-injection style usage)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_by_username(username: str):
    """Fetch a User row by username.  Returns None if not found."""
    db = SessionLocal()
    try:
        return db.query(User).filter(User.username == username).first()
    finally:
        db.close()
