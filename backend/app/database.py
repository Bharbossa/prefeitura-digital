from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# We use SQLite for local development; in production Postgres URI can be provided via DATABASE_URL
# SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///../database/leopoldina.db")
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    # Get the absolute path to the 'database' directory relative to the project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "database", "leopoldina.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

# Format for MySQL: mysql+pymysql://user:pass@host:port/db
if SQLALCHEMY_DATABASE_URL.startswith("mysql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

# Format for MySQL: mysql+pymysql://user:pass@host:port/db
# Prevent SQLite multithreading error
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
