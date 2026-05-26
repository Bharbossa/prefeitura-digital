import sys
sys.path.insert(0, r'c:\Users\55829\OneDrive\Desktop\sites\Leopoldina.D\backend')
from app.database import engine
from sqlalchemy import text
with engine.connect() as con:
    res = con.execute(text("SELECT id, usuario_id, protocolo FROM agendamentos WHERE protocolo='COL-2026-AQ8PB'")).fetchall()
    print('Agendamento:', res)
    if res:
        uid = res[0][1]
        u = con.execute(text(f"SELECT id, nome, endereco FROM usuarios WHERE id={uid}")).fetchall()
        print('Usuario:', u)
