import sys, os
from dotenv import load_dotenv
load_dotenv('backend/.env')
sys.path.append(os.getcwd() + '/backend')
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("SELECT id, email, senha_hash FROM admins_secretaria WHERE email = 'bharbossa@gmail.com'")).fetchall()
    print('Admins:', res)
