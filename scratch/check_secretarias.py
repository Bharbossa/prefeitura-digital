import sys
sys.path.insert(0, r'c:\Users\55829\OneDrive\Desktop\sites\Leopoldina.D\backend')
from app.database import engine
from sqlalchemy import text

with engine.connect() as con:
    # 1. List all secretarias
    print("=== SECRETARIAS ===")
    res = con.execute(text("SELECT id, nome FROM secretarias ORDER BY id")).fetchall()
    for r in res:
        print(f"  ID={r[0]}: {r[1]}")
    
    # 2. Check concurso agendamentos and which secretaria they are linked to
    print("\n=== AGENDAMENTOS DE CONCURSO ===")
    res = con.execute(text("SELECT a.id, a.protocolo, a.secretaria_id, s.nome as sec_nome, a.assunto FROM agendamentos a LEFT JOIN secretarias s ON a.secretaria_id = s.id WHERE a.tipo = 'Concurso' LIMIT 10")).fetchall()
    for r in res:
        print(f"  ID={r[0]} Proto={r[1]} SecID={r[2]} Sec={r[3]} Assunto={r[4]}")
