import sys, os
from dotenv import load_dotenv
load_dotenv('backend/.env')
sys.path.append(os.getcwd() + '/backend')
from app.database import engine
from sqlalchemy import text
from app.core.security import get_password_hash

new_pw = 'ColoniaDigital2026'
hashed = get_password_hash(new_pw)

with engine.begin() as conn:
    res = conn.execute(
        text("UPDATE usuarios SET senha_hash = :hash WHERE email = 'bharbossa@gmail.com'"),
        {'hash': hashed}
    )
    print("Rows updated:", res.rowcount)
