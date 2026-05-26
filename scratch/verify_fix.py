import sys
sys.path.insert(0, r'c:\Users\55829\OneDrive\Desktop\sites\Leopoldina.D\backend')
from app.database import engine
from sqlalchemy import text

with engine.connect() as con:
    wrong = con.execute(text(
        "SELECT id, protocolo, secretaria_id FROM agendamentos WHERE tipo = 'Concurso' AND secretaria_id != 28"
    )).fetchall()
    
    print(f"Concursos with wrong secretaria remaining: {len(wrong)}")
    for r in wrong:
        print(f"  ID={r[0]} Proto={r[1]} SecID={r[2]}")
    
    correct = con.execute(text(
        "SELECT COUNT(*) FROM agendamentos WHERE tipo = 'Concurso' AND secretaria_id = 28"
    )).fetchone()
    print(f"Concursos correctly assigned to Cultura e Esporte (ID=28): {correct[0]}")
