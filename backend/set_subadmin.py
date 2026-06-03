import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def assign_subadmin(email: str, exact_secretaria_name: str):
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("DATABASE_URL não configurada.")
        return
    
    engine = create_engine(db_url)
    with engine.connect() as conn:
        # Busca ID exato para evitar erros como Agricultura vs Cultura
        res = conn.execute(
            text("SELECT id FROM secretarias WHERE nome = :nome LIMIT 1"),
            {"nome": exact_secretaria_name}
        )
        sec = res.fetchone()
        if not sec:
            print(f"Secretaria '{exact_secretaria_name}' não encontrada.")
            return
        
        sec_id = sec[0]
        
        res_admin = conn.execute(
            text("SELECT id FROM admins_secretaria WHERE email = :email LIMIT 1"),
            {"email": email}
        )
        admin = res_admin.fetchone()
        if not admin:
            print(f"Sub-administrador '{email}' não encontrado.")
            return
            
        conn.execute(
            text("UPDATE admins_secretaria SET secretaria_id = :sid WHERE email = :email"),
            {"sid": sec_id, "email": email}
        )
        conn.commit()
        print(f"Sucesso! {email} agora é administrador de '{exact_secretaria_name}'.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Uso: python set_subadmin.py <email> <nome_exato_secretaria>")
    else:
        assign_subadmin(sys.argv[1], sys.argv[2])
