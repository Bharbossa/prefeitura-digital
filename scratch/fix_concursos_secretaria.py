import sys
sys.path.insert(0, r'c:\Users\55829\OneDrive\Desktop\sites\Leopoldina.D\backend')
from app.database import engine
from sqlalchemy import text

with engine.connect() as con:
    # Find the correct Cultura e Esporte secretaria ID
    cultura = con.execute(text("SELECT id FROM secretarias WHERE nome ILIKE '%CULTURA%ESPORTE%'")).fetchone()
    if not cultura:
        print("ERROR: Secretaria de Cultura e Esporte not found!")
        sys.exit(1)
    
    cultura_id = cultura[0]
    print(f"Secretaria de Cultura e Esporte ID: {cultura_id}")
    
    # Find all Concurso agendamentos NOT linked to Cultura e Esporte
    wrong = con.execute(text(
        "SELECT id, protocolo, secretaria_id, assunto FROM agendamentos WHERE tipo = 'Concurso' AND secretaria_id != :cid"
    ), {"cid": cultura_id}).fetchall()
    
    print(f"\nFound {len(wrong)} concurso agendamentos with wrong secretaria:")
    for r in wrong:
        print(f"  ID={r[0]} Proto={r[1]} SecID={r[2]}")
    
    if wrong:
        # Fix them
        result = con.execute(text(
            "UPDATE agendamentos SET secretaria_id = :cid WHERE tipo = 'Concurso' AND secretaria_id != :cid"
        ), {"cid": cultura_id})
        con.commit()
        print(f"\n✅ Fixed {result.rowcount} agendamentos - moved to Secretaria de Cultura e Esporte (ID={cultura_id})")
    else:
        print("\n✅ All concurso agendamentos are already correctly assigned!")
