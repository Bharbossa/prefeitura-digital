from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://neondb_owner:npg_9gGs8ZPRMUnS@ep-wild-river-ancnt251-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(DATABASE_URL)
engine = engine.execution_options(isolation_level="AUTOCOMMIT")

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TYPE statusocorrencia ADD VALUE IF NOT EXISTS 'cancelado'"))
        print("Enum altered successfully.")
    except Exception as e:
        print(f"Error altering enum (maybe it already exists?): {e}")
