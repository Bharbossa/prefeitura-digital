import sys, os
from dotenv import load_dotenv
load_dotenv('backend/.env')
sys.path.append(os.getcwd() + '/backend')
from app.database import engine
from sqlalchemy import text
from app.core.security import verify_password

with engine.connect() as conn:
    res = conn.execute(text("SELECT id, email, senha_hash FROM usuarios WHERE email = 'bharbossa@gmail.com'")).fetchone()
    print('User in DB:', res)
    if res:
        is_valid = verify_password('ColoniaDigital2026', res[2])
        print('Password valid?', is_valid)
