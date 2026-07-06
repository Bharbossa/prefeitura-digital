import sys, os
from dotenv import load_dotenv
load_dotenv('backend/.env')
sys.path.append(os.getcwd() + '/backend')
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res1 = conn.execute(text("SELECT id, email, tipo_usuario FROM usuarios WHERE email = 'bharbossa@gmail.com'")).fetchall()
    print('In usuarios:', res1)
    res2 = conn.execute(text("SELECT id, email FROM admin_secretarias WHERE email = 'bharbossa@gmail.com'")).fetchall()
    print('In admin_secretarias:', res2)
