from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from typing import Any

from ..core.firebase_config import db, DB_MODE
from ..database import get_db
from ..models.schema import Usuario, AdminSecretaria, StatusUsuario
from sqlalchemy.orm import Session
from ..models.pydantic_schemas import UsuarioCreate, UsuarioResponse, Token, ForgotPasswordRequest
from ..core.security import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from ..core.auth_deps import get_current_user

router = APIRouter()

@router.post("/register", response_model=UsuarioResponse)
def register(user_in: UsuarioCreate, db_sql: Session = Depends(get_db)) -> Any:
    if DB_MODE == "firestore":
        # Check if user exists in Firestore
        email_exists = db.collection("usuarios").where("email", "==", user_in.email).limit(1).get()
        cpf_exists = db.collection("usuarios").where("cpf", "==", user_in.cpf).limit(1).get()
        if email_exists or cpf_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um usuário registrado com este CPF ou E-mail")
        
        hashed_password = get_password_hash(user_in.senha)
        user_data = {
            "nome": user_in.nome, "cpf": user_in.cpf, "email": user_in.email,
            "senha_hash": hashed_password, "tipo_usuario": "cidadao", 
            "status": StatusUsuario.ativo, "criado_em": datetime.utcnow()
        }
        doc_ref = db.collection("usuarios").document()
        doc_ref.set(user_data)
        user_data["id"] = doc_ref.id
        return user_data
    else:
        # SQL Fallback (MySQL/SQLite)
        user_email = db_sql.query(Usuario).filter(Usuario.email == user_in.email).first()
        user_cpf = db_sql.query(Usuario).filter(Usuario.cpf == user_in.cpf).first()
        if user_email or user_cpf:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um usuário registrado com este CPF ou E-mail")
        hashed_password = get_password_hash(user_in.senha)
        db_user = Usuario(
            nome=user_in.nome, cpf=user_in.cpf, email=user_in.email, 
            senha_hash=hashed_password, status=StatusUsuario.ativo
        )
        db_sql.add(db_user)
        db_sql.commit()
        db_sql.refresh(db_user)
        return db_user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db_sql: Session = Depends(get_db)) -> Any:
    user_data = None
    user_type = "cidadao"

    if DB_MODE == "firestore":
        user_docs = db.collection("usuarios").where("email", "==", form_data.username).limit(1).get()
        if user_docs:
            user_data = user_docs[0].to_dict()
            user_data["id"] = user_docs[0].id
        else:
            admin_docs = db.collection("admin_secretarias").where("email", "==", form_data.username).limit(1).get()
            if admin_docs:
                user_data = admin_docs[0].to_dict()
                user_data["id"] = admin_docs[0].id
                user_type = "subadmin"
    else:
        # SQLite Fallback
        user = db_sql.query(Usuario).filter(Usuario.email == form_data.username).first()
        if user:
            user_type = user.tipo_usuario
            if hasattr(user_type, "value"):
                user_type = user_type.value
            else:
                user_type = str(user_type)
                if "." in user_type: user_type = user_type.split(".")[-1]
            
            user_data = {"email": user.email, "senha_hash": user.senha_hash, "id": user.id, "status": user.status}
        else:
            user = db_sql.query(AdminSecretaria).filter(AdminSecretaria.email == form_data.username).first()
            if user:
                user_data = {"email": user.email, "senha_hash": user.senha_hash, "id": user.id, "status": getattr(user, "status", "Ativo")}
                user_type = "subadmin"

    if not user_data or not verify_password(form_data.password, user_data.get("senha_hash")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active (Subadmins need approval, Citizens are auto-active except if rejected)
    user_status = user_data.get("status")
    if hasattr(user_status, "value"): user_status = user_status.value
    
    if user_type == "cidadao":
        if str(user_status).lower() == "rejeitado" or user_status == StatusUsuario.rejeitado:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sua solicitação de acesso foi rejeitada."
            )
    elif user_type == "subadmin":
        if str(user_status).lower() != "ativo" and user_status != StatusUsuario.ativo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sua conta de administrador está aguardando ativação ou foi suspensa."
            )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data["email"], "type": user_type, "id": str(user_data["id"])}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db_sql: Session = Depends(get_db)):
    import secrets, string, re
    from ..utils.sms_service import send_password_sms
    
    # 1. Normalize identifier (if CPF)
    raw_id = data.identifier.strip()
    # If it's mostly digits and has dots/dashes, strip them
    if re.match(r'^[0-9.\-\s/]+$', raw_id) and len(re.sub(r'\D', '', raw_id)) >= 11:
        clean_id = re.sub(r'\D', '', raw_id)
    else:
        clean_id = raw_id

    # 2. Find user by email or CPF
    user = db_sql.query(Usuario).filter((Usuario.email == clean_id) | (Usuario.cpf == clean_id)).first()
    if not user:
        # Check sub-admins too
        user = db_sql.query(AdminSecretaria).filter((AdminSecretaria.email == clean_id) | (AdminSecretaria.cpf == clean_id)).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado com os dados informados.")
    
    # 3. Generate random password (8 chars)
    alphabet = string.ascii_letters + string.digits
    new_pw = ''.join(secrets.choice(alphabet) for _ in range(8))
    
    # 4. Update in DB
    user.senha_hash = get_password_hash(new_pw)
    db_sql.commit()
    
    # 5. Mask destination for feedback
    masked_dest = ""
    if data.method == "sms":
        phone = getattr(user, 'telefone', '')
        if not phone:
            raise HTTPException(status_code=400, detail="Número de telefone não cadastrado.")
        
        # Format for SMS and masking
        clean_phone = re.sub(r'\D', '', phone)
        masked_dest = f"({clean_phone[:2]}) *****-{clean_phone[-4:]}"
        send_password_sms(phone, new_pw)
    else:
        email = user.email
        parts = email.split('@')
        masked_dest = f"{parts[0][0]}***@{parts[1]}"
        
        # Email (simulated)
        print(f"--- EMAIL SIMULADO PARA {email} ---")
        print(f"Sua nova senha é: {new_pw}")
        print(f"----------------------------------------")
    
    return {"message": f"Uma nova senha foi gerada e enviada para {masked_dest} via {data.method.upper()}."}

@router.get("/me", response_model=UsuarioResponse)
def read_users_me(current_user = Depends(get_current_user)):
    tipo = getattr(current_user, "tipo_usuario_verificado", "admin")
    
    # Extract status correctly handling Enum if necessary
    status_val = getattr(current_user, "status", "Ativo")
    if hasattr(status_val, "value"):
        status_val = status_val.value
        
    return {
        "id": int(current_user.id) if str(current_user.id).isdigit() else current_user.id,
        "nome": current_user.nome,
        "email": current_user.email,
        "cpf": getattr(current_user, "cpf", ""),
        "telefone": getattr(current_user, "telefone", ""),
        "endereco": getattr(current_user, "endereco", ""),
        "tipo_usuario": tipo,
        "status": status_val,
        "secretaria_id": getattr(current_user, "secretaria_id", None)
    }
