import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://neondb_owner:npg_9gGs8ZPRMUnS@ep-wild-river-ancnt251-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

def add_procuradoria():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT id FROM secretarias WHERE nome = 'PROCURADORIA'"))
        if res.fetchone():
            print("PROCURADORIA already exists.")
        else:
            conn.execute(text("INSERT INTO secretarias (nome) VALUES ('PROCURADORIA')"))
            conn.commit()
            print("PROCURADORIA added successfully.")

if __name__ == "__main__":
    add_procuradoria()
