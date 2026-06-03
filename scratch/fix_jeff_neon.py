import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://neondb_owner:npg_9gGs8ZPRMUnS@ep-wild-river-ancnt251-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    cultura_id = 28  # Explicit ID for SECRETARIA MUNICIPAL DE CULTURA E ESPORTE
    print(f"Setting secretaria_id to {cultura_id} for Jeff")
    conn.execute(text("UPDATE admins_secretaria SET secretaria_id = :sid WHERE email='jefftenocava@gmail.com'"), {"sid": cultura_id})
    conn.commit()
    print("Jeff updated successfully to Cultura e Esporte!")
