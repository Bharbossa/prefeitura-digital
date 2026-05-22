from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.schema import Usuario, AdminSecretaria, StatusUsuario
from ..core.firebase_config import db, DB_MODE
from ..models.pydantic_schemas import TokenData
from .security import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db_sql: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    import traceback
    from sqlalchemy import func
    
    def log_auth(msg):
        try:
            with open("uploads/debug.log", "a") as f:
                f.write(f"[{datetime.datetime.now()}] {msg}\n")
        except: pass
    
    import datetime
    log_auth(f"AUTH START: Token received: {token[:10]}...")

    try:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            tipo: str = payload.get("type")
            log_auth(f"JWT OK: Email={email}, Tipo={tipo}")
            if email is None or tipo is None:
                log_auth("ERR: Payload incomplete")
                raise credentials_exception
            token_data = TokenData(email=email, type=tipo)
        except JWTError as e:
            log_auth(f"ERR: JWT Decode: {str(e)}")
            raise credentials_exception
        
        # User lookup - Case-insensitive based on token type
        if token_data.type == "subadmin":
            user = db_sql.query(AdminSecretaria).filter(func.lower(AdminSecretaria.email) == func.lower(token_data.email)).first()
            if not user:
                user = db_sql.query(Usuario).filter(func.lower(Usuario.email) == func.lower(token_data.email)).first()
        else:
            user = db_sql.query(Usuario).filter(func.lower(Usuario.email) == func.lower(token_data.email)).first()
            if not user:
                user = db_sql.query(AdminSecretaria).filter(func.lower(AdminSecretaria.email) == func.lower(token_data.email)).first()
        
        if user:
            log_auth(f"User Found in DB: {user.email}")
            if isinstance(user, Usuario):
                raw_role = str(user.tipo_usuario).split('.')[-1]
                role = "admin" if raw_role == "admin" else "cidadao"
            else:
                role = "subadmin"
            
            # Role validation
            valid = False
            if tipo == "admin" and role == "admin": valid = True
            elif tipo == "subadmin" and role == "subadmin": valid = True
            elif tipo == "cidadao" and role == "cidadao": valid = True
            elif tipo == "user" and role == "cidadao": valid = True
            
            if valid:
                log_auth(f"Auth Success: role={role}")
                sec_nome = None
                if role == "subadmin" and hasattr(user, 'secretaria') and user.secretaria:
                    sec_nome = user.secretaria.nome
                    
                from types import SimpleNamespace
                return SimpleNamespace(
                    id=int(user.id),
                    email=user.email,
                    nome=user.nome,
                    cpf=user.cpf,
                    telefone=getattr(user, 'telefone', ""),
                    whatsapp=getattr(user, 'whatsapp', ""),
                    endereco=getattr(user, 'endereco', ""),
                    status=getattr(user, 'status', "ativo"),
                    secretaria_id=getattr(user, 'secretaria_id', None),
                    secretaria_nome=sec_nome,
                    foto_perfil=getattr(user, 'foto_perfil', None),
                    tipo_usuario_verificado=role
                )
            else:
                log_auth(f"ERR: Role mismatch. Token={tipo}, DB={role}")

        log_auth(f"ERR: User not found or rejected: {token_data.email}")
        raise credentials_exception

    except HTTPException as he:
        log_auth(f"AUTH RAISED: {he.detail}")
        raise he
    except Exception as e:
        log_auth(f"CRITICAL AUTH: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Auth system error: {str(e)}")

def get_current_admin(current_user = Depends(get_current_user)):
    if current_user.tipo_usuario_verificado not in ["admin", "subadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores."
        )
    return current_user

def get_general_admin(current_user = Depends(get_current_user)):
    if current_user.tipo_usuario_verificado != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito ao Administrador Geral."
        )
    return current_user
