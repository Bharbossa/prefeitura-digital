from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# We use SQLite for local development; in production Postgres URI can be provided via DATABASE_URL
# SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///../database/leopoldina.db")
# Neon Postgres Connection String
# For production, this should ideally be set in the environment variables (e.g., Render Dashboard)
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_9gGs8ZPRMUnS@ep-wild-river-ancnt251-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"
)

# Format for MySQL: mysql+pymysql://user:pass@host:port/db
if SQLALCHEMY_DATABASE_URL.startswith("mysql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

# Prevent SQLite multithreading error (only applies if DATABASE_URL is explicitly set to sqlite)
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
