from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from ..core.utils import get_brasilia_time
from typing import Any

from ..core.firebase_config import db, DB_MODE
from ..database import get_db
from ..models.schema import Usuario, AdminSecretaria, StatusUsuario
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.pydantic_schemas import UsuarioCreate, UsuarioResponse, Token, ForgotPasswordRequest, ChangePasswordRequest, UpdateNameRequest, UpdateAddressRequest, UpdatePhoneRequest
from ..core.security import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, validate_password_complexity
from ..core.auth_deps import get_current_user

router = APIRouter()

@router.post("/register", response_model=UsuarioResponse)
def register(user_in: UsuarioCreate, db_sql: Session = Depends(get_db)) -> Any:
    validate_password_complexity(user_in.senha)
    
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
            "status": StatusUsuario.ativo, "criado_em": get_brasilia_time(),
            "genero": user_in.genero,
            "botao_panico_autorizado": 1 if user_in.genero and user_in.genero.lower() == 'feminino' else 0
        }
        doc_ref = db.collection("usuarios").document()
        doc_ref.set(user_data)
        user_data["id"] = doc_ref.id
        return user_data
    else:
        # SQL Fallback (MySQL/SQLite)
        # Normalize email/cpf before check
        normalized_email = user_in.email.lower().strip()
        user_email = db_sql.query(Usuario).filter(Usuario.email == normalized_email).first()
        user_cpf = db_sql.query(Usuario).filter(Usuario.cpf == user_in.cpf.strip()).first()
        if user_email or user_cpf:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um usuário registrado com este CPF ou E-mail")
        hashed_password = get_password_hash(user_in.senha)
        db_user = Usuario(
            nome=user_in.nome, cpf=user_in.cpf.strip(), email=normalized_email,
            telefone=user_in.telefone, whatsapp=user_in.whatsapp, 
            endereco=user_in.endereco,
            senha_hash=hashed_password, status=StatusUsuario.ativo,
            genero=user_in.genero,
            botao_panico_autorizado=1 if user_in.genero and user_in.genero.lower() == 'feminino' else 0
        )
        db_sql.add(db_user)
        db_sql.commit()
        db_sql.refresh(db_user)
        
        # Log de Auditoria para Cidadão
        from ..models.schema import LogAuditoria
        log = LogAuditoria(
            usuario_id=db_user.id,
            usuario_tipo="cidadao",
            acao="cadastro_usuario_cidadao",
            detalhes=f"Novo cidadão cadastrado: {db_user.nome} ({db_user.email})"
        )
        db_sql.add(log)
        db_sql.commit()
        
        return db_user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db_sql: Session = Depends(get_db)) -> Any:
    user_data = None
    user_type = "cidadao"

    if DB_MODE == "firestore":
        user_docs = db.collection("usuarios").where("email", "==", form_data.username).limit(1).get()
        admin_docs = db.collection("admin_secretarias").where("email", "==", form_data.username).limit(1).get()
        
        user_data = None
        user_type = "cidadao"
        
        # 1. Try to match subadmin first if they exist and password matches
        if admin_docs:
            admin_data = admin_docs[0].to_dict()
            admin_data["id"] = admin_docs[0].id
            if verify_password(form_data.password, admin_data.get("senha_hash")):
                user_data = admin_data
                user_type = "subadmin"
                
        # 2. Try to match citizen / admin
        if not user_data and user_docs:
            cidadao_data = user_docs[0].to_dict()
            cidadao_data["id"] = user_docs[0].id
            if verify_password(form_data.password, cidadao_data.get("senha_hash")):
                user_data = cidadao_data
                user_type = cidadao_data.get("tipo_usuario", "cidadao")
                
        # 3. Fallback if password didn't match either but we found records (for standard failure path)
        if not user_data:
            if admin_docs:
                user_data = admin_docs[0].to_dict()
                user_data["id"] = admin_docs[0].id
                user_type = "subadmin"
            elif user_docs:
                user_data = user_docs[0].to_dict()
                user_data["id"] = user_docs[0].id
                user_type = user_docs[0].to_dict().get("tipo_usuario", "cidadao")
    else:
        # SQLite / MySQL Fallback
        clean_username = form_data.username.lower().strip()
        
        # Check if the username is a CPF
        import re
        is_cpf = False
        clean_cpf = re.sub(r'\D', '', clean_username)
        if len(clean_cpf) == 11 and re.match(r'^[0-9.\-\s]+$', form_data.username.strip()):
            is_cpf = True

        # Check both tables
        user_cidadao = None
        user_subadmin = None
        
        if is_cpf:
            cpf_fmt = f"{clean_cpf[:3]}.{clean_cpf[3:6]}.{clean_cpf[6:9]}-{clean_cpf[9:]}"
            user_cidadao = db_sql.query(Usuario).filter((Usuario.cpf == clean_cpf) | (Usuario.cpf == cpf_fmt) | (Usuario.cpf == form_data.username.strip())).first()
            user_subadmin = db_sql.query(AdminSecretaria).filter((AdminSecretaria.cpf == clean_cpf) | (AdminSecretaria.cpf == cpf_fmt) | (AdminSecretaria.cpf == form_data.username.strip())).first()
        else:
            user_cidadao = db_sql.query(Usuario).filter(func.lower(Usuario.email) == clean_username).first()
            user_subadmin = db_sql.query(AdminSecretaria).filter(func.lower(AdminSecretaria.email) == clean_username).first()

        user = None
        user_type = None

        # 1. Try to match subadmin first if password matches
        if user_subadmin and verify_password(form_data.password, user_subadmin.senha_hash):
            user = user_subadmin
            user_type = "subadmin"
        # 2. Try to match citizen / admin
        elif user_cidadao and verify_password(form_data.password, user_cidadao.senha_hash):
            user = user_cidadao
            user_type = user_cidadao.tipo_usuario
            if hasattr(user_type, "value"):
                user_type = user_type.value
            else:
                user_type = str(user_type)
                if "." in user_type: user_type = user_type.split(".")[-1]
        # 3. Fallback if password didn't match either (so standard failure path works)
        else:
            if user_subadmin:
                user = user_subadmin
                user_type = "subadmin"
            elif user_cidadao:
                user = user_cidadao
                user_type = user_cidadao.tipo_usuario
                if hasattr(user_type, "value"):
                    user_type = user_type.value
                else:
                    user_type = str(user_type)
                    if "." in user_type: user_type = user_type.split(".")[-1]

        if user:
            user_data = {
                "email": user.email, 
                "senha_hash": user.senha_hash, 
                "id": user.id, 
                "status": getattr(user, "status", "Ativo") if user_type == "subadmin" else user.status
            }

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
    
    # 1. Normalize identifier (if email, lowercase it; if CPF, strip formatting)
    raw_id = data.identifier.strip()
    if "@" in raw_id:
        clean_id = raw_id.lower()
    elif re.match(r'^[0-9.\-\s/]+$', raw_id) and len(re.sub(r'\D', '', raw_id)) >= 11:
        clean_id = re.sub(r'\D', '', raw_id)
    else:
        clean_id = raw_id

    # 2. Find user by email or CPF - case insensitive for email
    if re.match(r'^[0-9]+$', clean_id) and len(clean_id) == 11:
        cpf_fmt = f"{clean_id[:3]}.{clean_id[3:6]}.{clean_id[6:9]}-{clean_id[9:]}"
        user_cidadao = db_sql.query(Usuario).filter((Usuario.cpf == clean_id) | (Usuario.cpf == cpf_fmt) | (Usuario.cpf == raw_id)).first()
        user_subadmin = db_sql.query(AdminSecretaria).filter((AdminSecretaria.cpf == clean_id) | (AdminSecretaria.cpf == cpf_fmt) | (AdminSecretaria.cpf == raw_id)).first()
    else:
        user_cidadao = db_sql.query(Usuario).filter(func.lower(Usuario.email) == clean_id).first()
        user_subadmin = db_sql.query(AdminSecretaria).filter(func.lower(AdminSecretaria.email) == clean_id).first()
    
    if not user_cidadao and not user_subadmin:
        raise HTTPException(status_code=404, detail="Usuário não encontrado com os dados informados.")
    
    # Choose primary user record for notification & rate limiting
    user = user_subadmin if user_subadmin else user_cidadao
    tipo_usu = "subadmin" if user_subadmin else "cidadao"

    # Rate limiting: impedir múltiplos disparos em curto intervalo (cooldown de 2 minutos)
    from datetime import timedelta
    from ..models.schema import LogRecuperacaoSenha, get_brasilia_time
    agora = get_brasilia_time()
    limite_tempo = agora - timedelta(minutes=2)
    
    log_recente = db_sql.query(LogRecuperacaoSenha).filter(
        LogRecuperacaoSenha.usuario_nome == user.nome,
        LogRecuperacaoSenha.data_solicitacao >= limite_tempo
    ).first()
    
    if log_recente:
        raise HTTPException(
            status_code=429, 
            detail="Uma nova senha já foi enviada recentemente por SMS. Por favor, aguarde 2 minutos antes de solicitar novamente."
        )

    # 3. Generate random password (8 chars)
    alphabet = string.ascii_letters + string.digits
    new_pw = ''.join(secrets.choice(alphabet) for _ in range(8))
    
    # 4. Update in DB (Sincronizado se existir em ambos para evitar conflitos!)
    hashed_pw = get_password_hash(new_pw)
    
    if user_cidadao:
        user_cidadao.senha_hash = hashed_pw
    if user_subadmin:
        user_subadmin.senha_hash = hashed_pw
        
    db_sql.commit()
    
    if DB_MODE == "firestore":
        if user_cidadao:
            user_docs = db.collection("usuarios").where("email", "==", clean_id).limit(1).get()
            if not user_docs:
                user_docs = db.collection("usuarios").where("cpf", "==", clean_id).limit(1).get()
            if user_docs:
                db.collection("usuarios").document(user_docs[0].id).update({"senha_hash": hashed_pw})
        if user_subadmin:
            admin_docs = db.collection("admin_secretarias").where("email", "==", clean_id).limit(1).get()
            if not admin_docs:
                admin_docs = db.collection("admin_secretarias").where("cpf", "==", clean_id).limit(1).get()
            if admin_docs:
                db.collection("admin_secretarias").document(admin_docs[0].id).update({"senha_hash": hashed_pw})
    
    # Choose primary user record for notification purposes
    user = user_subadmin if user_subadmin else user_cidadao
    
    # 5. Mask destination for feedback
    masked_dest = ""
    sucesso_envio = False
    metodo_envio = "sms" # Forçar sempre SMS

    phone = (getattr(user, 'telefone', '') or getattr(user, 'whatsapp', '') or '').strip()
    
    # Fallback to Firestore if phone not in SQL model
    if not phone and DB_MODE == "firestore" and db is not None:
        try:
            user_docs = db.collection("usuarios").where("email", "==", clean_id).limit(1).get()
            if not user_docs:
                user_docs = db.collection("usuarios").where("cpf", "==", clean_id).limit(1).get()
            if user_docs:
                f_data = user_docs[0].to_dict()
                phone = (f_data.get("telefone") or f_data.get("whatsapp") or "").strip()
        except Exception as e:
            print("Error looking up Firestore phone:", e)

    if not phone:
        raise HTTPException(status_code=400, detail="Número de telefone/WhatsApp não cadastrado no seu perfil.")
    
    # Format for SMS and masking
    clean_phone = re.sub(r'\D', '', phone)
    if len(clean_phone) < 10:
        raise HTTPException(status_code=400, detail="Número de telefone inválido no seu perfil.")
        
    masked_dest = f"({clean_phone[-11:-9] if len(clean_phone) >= 11 else clean_phone[:2]}) *****-{clean_phone[-4:]}"
    
    # Enviar SMS via Twilio
    sucesso_envio = send_password_sms(phone, new_pw)
    
    if not sucesso_envio:
        raise HTTPException(status_code=500, detail="Falha ao disparar SMS de recuperação. Verifique se o número possui DDD e WhatsApp/SMS ativo.")
    
    # 6. Log the attempt
    from ..models.schema import LogRecuperacaoSenha
    tipo_usu = "subadmin" if user_subadmin else "cidadao"
    novo_log = LogRecuperacaoSenha(
        usuario_nome=user.nome,
        usuario_tipo=tipo_usu,
        metodo=metodo_envio,
        sucesso=1 if sucesso_envio else 0
    )
    db_sql.add(novo_log)
    db_sql.commit()
    
    return {"message": f"Uma nova senha foi gerada e enviada via SMS para {masked_dest} com sucesso!"}

@router.get("/password-resets")
def get_password_resets(current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    from ..models.schema import LogRecuperacaoSenha
    if current_user.tipo_usuario_verificado != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado.")
    
    logs = db_sql.query(LogRecuperacaoSenha).order_by(LogRecuperacaoSenha.data_solicitacao.desc()).all()
    return [{"id": l.id, "usuario_nome": l.usuario_nome, "usuario_tipo": l.usuario_tipo, "metodo": l.metodo, "sucesso": l.sucesso, "data_solicitacao": l.data_solicitacao} for l in logs]


@router.patch("/change-password")
def change_password(data: ChangePasswordRequest, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    validate_password_complexity(data.nova_senha)
    from ..models.schema import Usuario, AdminSecretaria
    
    if current_user.tipo_usuario_verificado == "subadmin":
        user_db = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == current_user.id).first()
    else:
        user_db = db_sql.query(Usuario).filter(Usuario.id == current_user.id).first()
        
    if not user_db:
        # Check Firestore directly if not found in SQL
        if DB_MODE == "firestore":
            if current_user.tipo_usuario_verificado == "subadmin":
                admin_docs = db.collection("admin_secretarias").where("email", "==", current_user.email).limit(1).get()
                if not admin_docs:
                    raise HTTPException(status_code=404, detail="Usuário não encontrado.")
                admin_doc = admin_docs[0]
                if not verify_password(data.senha_atual, admin_doc.to_dict().get("senha_hash")):
                    raise HTTPException(status_code=401, detail="Senha atual incorreta.")
                db.collection("admin_secretarias").document(admin_doc.id).update({"senha_hash": get_password_hash(data.nova_senha)})
            else:
                user_docs = db.collection("usuarios").where("email", "==", current_user.email).limit(1).get()
                if not user_docs:
                    raise HTTPException(status_code=404, detail="Usuário não encontrado.")
                user_doc = user_docs[0]
                if not verify_password(data.senha_atual, user_doc.to_dict().get("senha_hash")):
                    raise HTTPException(status_code=401, detail="Senha atual incorreta.")
                db.collection("usuarios").document(user_doc.id).update({"senha_hash": get_password_hash(data.nova_senha)})
        else:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    else:
        if not verify_password(data.senha_atual, user_db.senha_hash):
            raise HTTPException(status_code=401, detail="Senha atual incorreta.")
        
        new_hash = get_password_hash(data.nova_senha)
        user_db.senha_hash = new_hash
        db_sql.commit()
        
        if DB_MODE == "firestore":
            if current_user.tipo_usuario_verificado == "subadmin":
                admin_docs = db.collection("admin_secretarias").where("email", "==", current_user.email).limit(1).get()
                if admin_docs:
                    db.collection("admin_secretarias").document(admin_docs[0].id).update({"senha_hash": new_hash})
            else:
                user_docs = db.collection("usuarios").where("email", "==", current_user.email).limit(1).get()
                if user_docs:
                    db.collection("usuarios").document(user_docs[0].id).update({"senha_hash": new_hash})
    
    # Audit log
    from ..models.schema import LogAuditoria
    log = LogAuditoria(
        usuario_id=current_user.id,
        usuario_tipo="admin" if current_user.tipo_usuario_verificado in ["admin", "subadmin"] else "cidadao",
        acao="self_change_password",
        detalhes=f"Usuário {current_user.email} alterou sua própria senha"
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {"message": "Senha alterada com sucesso!"}


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
        "whatsapp": getattr(current_user, "whatsapp", ""),
        "endereco": getattr(current_user, "endereco", ""),
        "tipo_usuario": tipo,
        "status": status_val,
        "secretaria_id": getattr(current_user, "secretaria_id", None),
        "secretaria_nome": getattr(current_user, "secretaria_nome", None),
        "foto_perfil": getattr(current_user, "foto_perfil", None),
        "botao_panico_autorizado": getattr(current_user, "botao_panico_autorizado", 0)
    }
@router.post("/update-photo")
async def update_photo(
    file: UploadFile = File(...), 
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    # 1. Validar extensão
    ext = file.filename.split('.')[-1].lower()
    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
        raise HTTPException(status_code=400, detail="Formato de imagem inválido. Use JPG, PNG ou WEBP.")
    
    # 2. Ler conteúdo do arquivo e limitar em 2MB
    file_content = await file.read()
    if len(file_content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="A imagem é muito grande. O limite máximo é de 2 MB.")
        
    # 3. Converter para base64 Data URI
    import base64
    base64_encoded = base64.b64encode(file_content).decode('utf-8')
    mime_type = f"image/{ext if ext != 'jpg' else 'jpeg'}"
    base64_data_uri = f"data:{mime_type};base64,{base64_encoded}"
    
    # 4. Atualizar no Banco de Dados
    from ..models.schema import Usuario, AdminSecretaria
    if current_user.tipo_usuario_verificado == "subadmin":
        user_db = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == current_user.id).first()
    else:
        user_db = db_sql.query(Usuario).filter(Usuario.id == current_user.id).first()
        
    if not user_db:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
    # Limpar foto legada em disco se ela existir (apenas para manter o servidor limpo de arquivos antigos)
    if user_db.foto_perfil and not user_db.foto_perfil.startswith('data:'):
        import os
        legacy_path = user_db.foto_perfil.replace('/uploads/', 'uploads/')
        if os.path.exists(legacy_path):
            try: os.remove(legacy_path)
            except: pass
            
    user_db.foto_perfil = base64_data_uri
    db_sql.commit()
    
    return {"url": user_db.foto_perfil}


@router.patch("/update-name")
def update_name(data: UpdateNameRequest, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    from ..models.schema import Usuario, AdminSecretaria
    
    if current_user.tipo_usuario_verificado == "subadmin":
        user_db = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == current_user.id).first()
    else:
        user_db = db_sql.query(Usuario).filter(Usuario.id == current_user.id).first()
        
    if not user_db:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    old_name = user_db.nome
    user_db.nome = data.nome
    db_sql.commit()
    
    # Audit log
    from ..models.schema import LogAuditoria
    log = LogAuditoria(
        usuario_id=current_user.id,
        usuario_tipo="admin" if current_user.tipo_usuario_verificado in ["admin", "subadmin"] else "cidadao",
        acao="update_name",
        detalhes=f"Usuário {current_user.email} alterou nome de '{old_name}' para '{data.nome}'"
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {"message": "Nome atualizado com sucesso!", "nome": data.nome}

@router.patch("/update-address")
def update_address(data: UpdateAddressRequest, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    from ..models.schema import Usuario, AdminSecretaria
    
    if current_user.tipo_usuario_verificado == "subadmin":
        user_db = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == current_user.id).first()
    else:
        user_db = db_sql.query(Usuario).filter(Usuario.id == current_user.id).first()
        
    if not user_db:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    old_address = user_db.endereco
    user_db.endereco = data.endereco
    db_sql.commit()
    
    # Audit log
    from ..models.schema import LogAuditoria
    log = LogAuditoria(
        usuario_id=current_user.id,
        usuario_tipo="admin" if current_user.tipo_usuario_verificado in ["admin", "subadmin"] else "cidadao",
        acao="update_address",
        detalhes=f"Usuário {current_user.email} alterou endereço de '{old_address}' para '{data.endereco}'"
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {"message": "Endereço atualizado com sucesso!", "endereco": data.endereco}

@router.patch("/update-phone")
def update_phone(data: UpdatePhoneRequest, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    from ..models.schema import Usuario, AdminSecretaria
    
    if current_user.tipo_usuario_verificado == "subadmin":
        user_db = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == current_user.id).first()
    else:
        user_db = db_sql.query(Usuario).filter(Usuario.id == current_user.id).first()
        
    if not user_db:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    # Strip any non-numeric characters before saving, like the SMS service expects or standard formats
    import re
    clean_phone = re.sub(r'\D', '', data.telefone)
    
    old_phone = user_db.telefone
    user_db.telefone = clean_phone
    db_sql.commit()
    
    # Audit log
    from ..models.schema import LogAuditoria
    log = LogAuditoria(
        usuario_id=current_user.id,
        usuario_tipo="admin" if current_user.tipo_usuario_verificado in ["admin", "subadmin"] else "cidadao",
        acao="update_phone",
        detalhes=f"Usuário {current_user.email} alterou telefone de '{old_phone}' para '{clean_phone}'"
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {"message": "Telefone atualizado com sucesso!", "telefone": clean_phone}
