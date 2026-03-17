import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.database import SessionLocal
from app.models.schema import Secretaria, Usuario, TipoUsuario

def seed_db():
    db = SessionLocal()
    try:
        print("Checking and inserting initial secretarias...")
        secretarias_nomes = [
            'Secretaria de Obras',
            'Secretaria de Saúde',
            'Secretaria de Educação',
            'Secretaria de Meio Ambiente',
            'Iluminação Pública',
            'Limpeza Urbana',
            'Guarda Municipal',
            'Secretaria da Mulher'
        ]
        
        for nome in secretarias_nomes:
            if not db.query(Secretaria).filter(Secretaria.nome == nome).first():
                print(f"Adding {nome}")
                db.add(Secretaria(nome=nome))
        
        print("Checking and inserting default admin user...")
        # Admin user
        admin_email = 'admin@leopoldina.gov.br'
        if not db.query(Usuario).filter(Usuario.email == admin_email).first():
            print("Adding Admin user (admin@leopoldina.gov.br)...")
            admin = Usuario(
                nome='Administrador Geral',
                cpf='000.000.000-00',
                email=admin_email,
                senha_hash='$2b$12$2dP4FQ7Ly6GlQcwrKE7tY.dU1yAdh7uyPDgGylHifEpHatqZz9Ori',
                tipo_usuario=TipoUsuario.admin
            )
            db.add(admin)
        else:
            print("Admin user already exists.")
            
        db.commit()
        print("Database seeded successfully!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
