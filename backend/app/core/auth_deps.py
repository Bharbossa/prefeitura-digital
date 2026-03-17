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
            print(f"DEBUG: Missing payload fields. Email: {email}, Tipo: {tipo}")
            raise credentials_exception
        token_data = TokenData(email=email, type=tipo)
    except JWTError as e:
        print(f"DEBUG: JWT Decode Error: {e}")
        raise credentials_exception
    
    if DB_MODE == "firestore":
        if tipo == "admin":
            # Check AdminSecretaria then fallback to general docs if needed
            docs = db.collection("admin_secretarias").where("email", "==", token_data.email).limit(1).get()
            if not docs:
                docs = db.collection("usuarios").where("email", "==", token_data.email).where("tipo_usuario", "==", "admin").limit(1).get()
        else:
            docs = db.collection("usuarios").where("email", "==", token_data.email).limit(1).get()

        if docs:
            user_data = docs[0].to_dict()
            user_data["id"] = docs[0].id
            from types import SimpleNamespace
            user = SimpleNamespace(**user_data)
        else:
            user = None
    else:
        # SQLite Fallback
        # Try both tables in order of probability
        user = db_sql.query(Usuario).filter(Usuario.email == token_data.email).first()
        if not user:
            user = db_sql.query(AdminSecretaria).filter(AdminSecretaria.email == token_data.email).first()
        
        if user:
            # Ensure it matches the expected type in the token
            u_type = str(user.tipo_usuario).split('.')[-1] if hasattr(user, 'tipo_usuario') else 'admin'
            
            # Simple check: if token says admin, user must be admin (either in usuarios or admins_secretaria table)
            if tipo == "admin" and u_type == "cidadao":
                 user = None
            else:
                # Also attach type to avoid re-checking
                try:
                    user.tipo_usuario_verificado = tipo
                except:
                    # If SQLAlchemy object is immutable, create a wrapper
                    from types import SimpleNamespace
                    user = SimpleNamespace(
                        id=str(user.id),
                        email=user.email,
                        nome=user.nome,
                        tipo_usuario_verificado=tipo
                    )

    if user is None:
        raise credentials_exception
    
    return user

def get_current_admin(current_user = Depends(get_current_user)):
    if current_user.tipo_usuario_verificado != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
