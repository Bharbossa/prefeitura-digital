from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.schema import Usuario, AdminSecretaria
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
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        tipo: str = payload.get("type")
        if email is None or tipo is None:
            raise credentials_exception
        token_data = TokenData(email=email, type=tipo)
    except JWTError:
        raise credentials_exception
    
    # SQLite Implementation (Neon/Postgres use this too via DB_MODE != "firestore")
    # Try User table (Citizen or Admin)
    user = db_sql.query(Usuario).filter(Usuario.email == token_data.email).first()
    if not user:
        # Try AdminSecretaria table (Sub-admin)
        user = db_sql.query(AdminSecretaria).filter(AdminSecretaria.email == token_data.email).first()
    
    if user:
        # Determine actual verified type
        if isinstance(user, Usuario):
            # cidadao or admin
            role = str(user.tipo_usuario).split('.')[-1] # Handle enum
        else:
            # AdminSecretaria is always subadmin
            role = "subadmin"
        
        # Security check: Does token type match database role?
        # If token says 'admin', but user is 'cidadao', reject.
        if tipo == "admin" and role != "admin":
            user = None
        elif tipo == "subadmin" and role != "subadmin":
            user = None
        elif tipo == "cidadao" and role != "cidadao":
            user = None
        
        if user:
            # Create a uniform object for routes
            from types import SimpleNamespace
            is_subadmin = isinstance(user, AdminSecretaria)
            
            user_out = SimpleNamespace(
                id=user.id,
                email=user.email,
                nome=user.nome,
                cpf=user.cpf,
                telefone=user.telefone,
                endereco=user.endereco,
                status=getattr(user, 'status', StatusUsuario.ativo if is_subadmin else user.status),
                secretaria_id=getattr(user, 'secretaria_id', None),
                tipo_usuario_verificado=role # "cidadao", "subadmin", "admin"
            )
            return user_out

    raise credentials_exception

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

