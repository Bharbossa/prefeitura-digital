from app.database import SessionLocal
from app.models.schema import Usuario, AdminSecretaria
from app.core.security import get_password_hash

def reset():
    db = SessionLocal()
    email = 'alexandregilberto1994@gmail.com'
    new_pass = '123456'
    hashed = get_password_hash(new_pass)
    
    u = db.query(Usuario).filter(Usuario.email == email).first()
    if u:
        u.senha = hashed
        db.commit()
        print(f'Cidadão {email} atualizado para {new_pass}')
        return
        
    a = db.query(AdminSecretaria).filter(AdminSecretaria.email == email).first()
    if a:
        a.senha = hashed
        db.commit()
        print(f'Sub-Admin {email} atualizado para {new_pass}')
        return
        
    print('Usuário não encontrado')

if __name__ == "__main__":
    reset()
