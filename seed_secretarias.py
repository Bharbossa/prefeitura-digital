import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.database import SessionLocal
from backend.app.models.schema import Secretaria

def seed():
    db = SessionLocal()
    secretarias_nomes = [
        "COLONIAPREV",
        "PROCURADORIA-GERAL DO MUNICÍPIO",
        "SECRETARIA DE FINANÇAS",
        "SECRETARIA DE INFRAESTRUTURA",
        "SECRETARIA MUNICIPAL DE ADMINISTRAÇÃO",
        "SECRETARIA MUNICIPAL DE AGRICULTURA",
        "SECRETARIA MUNICIPAL DE ASSISTÊNCIA SOCIAL",
        "SECRETARIA MUNICIPAL DE EDUCAÇÃO",
        "SECRETARIA MUNICIPAL DE SAÚDE"
    ]
    
    for nome in secretarias_nomes:
        existente = db.query(Secretaria).filter(Secretaria.nome == nome).first()
        if not existente:
            nova = Secretaria(nome=nome)
            db.add(nova)
            print(f"Adicionando {nome}")
        else:
            print(f"Já existe {nome}")
            
    db.commit()
    db.close()
    print("Concluído!")

if __name__ == "__main__":
    seed()
