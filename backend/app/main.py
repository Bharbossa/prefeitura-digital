from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base, get_db
import os

app = FastAPI(title="Colônia Digital API", version="6.1.0-FIXED_CORS")

# 1. CORS - Configuração Robusta
# Usando origens explícitas para permitir Credentials se necessário, 
# mas garantindo que o cabeçalho Authorization seja aceito.
origins = [
    "https://leopoldina-digital-1b75e.web.app",
    "https://leopoldina-digital-1b75e.firebaseapp.com",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Voltando para * para maior compatibilidade, mas sem credentials
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["*"],
)

# =========================================================
# AGENTE DE SEGURANÇA E FIREWALL INTELIGENTE (WAF)
# Proteção contra SQL Injection, XSS, Brute Force e Scrapers
# =========================================================
import re
import time
from collections import defaultdict
from fastapi import BackgroundTasks
from .utils.sms_service import notify_admin_security_alert_background

# Controle de frequência (Rate Limit por IP: máximo 90 requisições por minuto)
IP_REQUEST_HISTORY = defaultdict(list)
IP_BLOCKED_UNTIL = {}
FAILED_LOGIN_ATTEMPTS = defaultdict(list)

# Padrões conhecidos de invasão (SQL Injection, XSS, Path Traversal)
ATTACK_PATTERNS = [
    r"(?i)\b(select|union|insert|delete|drop|alter|exec|system|cmd)\b.*(from|into|where|table|database)",
    r"(?i)<script\b[^>]*>",
    r"(?i)javascript:",
    r"(?i)onload\s*=",
    r"(?i)onerror\s*=",
    r"(?i)\.\./\.\./",
    r"(?i)/etc/passwd",
    r"(?i)1=1",
    r"(?i)'\s*or\s*'",
    r"(?i)\"--",
]

@app.middleware("http")
async def security_firewall_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "desconhecido"
    current_time = time.time()

    # Resposta rápida para requisições de pre-flight CORS OPTIONS
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Origin, X-Requested-With",
                "Access-Control-Max-Age": "86400"
            }
        )

    # 1. Verifica se IP está temporariamente banido
    if client_ip in IP_BLOCKED_UNTIL:
        if current_time < IP_BLOCKED_UNTIL[client_ip]:
            return Response(
                content="Acesso bloqueado temporariamente por motivo de segurança.",
                status_code=403,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        else:
            del IP_BLOCKED_UNTIL[client_ip]

    # 2. Proteção contra Ataques de Força Bruta / Ddos (Rate Limit)
    IP_REQUEST_HISTORY[client_ip] = [t for t in IP_REQUEST_HISTORY[client_ip] if current_time - t < 60]
    IP_REQUEST_HISTORY[client_ip].append(current_time)

    if len(IP_REQUEST_HISTORY[client_ip]) > 120: # Mais de 120 requisições em 1 minuto
        IP_BLOCKED_UNTIL[client_ip] = current_time + 1800 # Banir IP por 30 minutos
        bg = BackgroundTasks()
        bg.add_task(notify_admin_security_alert_background, "Ataque de Força Bruta / Rate Limit (DDoS)", client_ip, "Mais de 120 requisições/minuto bloqueadas.")
        return Response(
            content="Taxa de requisições excedida. IP Bloqueado.",
            status_code=429,
            background=bg,
            headers={"Access-Control-Allow-Origin": "*"}
        )

    # 3. Inspeção de payload da URL e Query Parameters (SQLi, XSS, Path Traversal)
    full_url = str(request.url)
    for pattern in ATTACK_PATTERNS:
        if re.search(pattern, full_url):
            IP_BLOCKED_UNTIL[client_ip] = current_time + 3600 # Banir por 1 hora
            bg = BackgroundTasks()
            bg.add_task(notify_admin_security_alert_background, "Ataque de Injeção de Código (SQLi/XSS)", client_ip, f"Padrão detectado na URL: {pattern}")
            return Response(
                content="Tentativa de vulnerabilidade detectada e bloqueada pelo Agente de Segurança.",
                status_code=400,
                background=bg,
                headers={"Access-Control-Allow-Origin": "*"}
            )

    try:
        response = await call_next(request)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return Response(
            content=f'{{"detail": "Erro interno do servidor: {str(exc)}"}}',
            status_code=500,
            media_type="application/json",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Origin, X-Requested-With"
            }
        )

    # 4. Monitoramento de tentativas falhas de login (Brute Force em senhas)
    if request.url.path.endswith("/auth/login") and response.status_code == 401:
        FAILED_LOGIN_ATTEMPTS[client_ip] = [t for t in FAILED_LOGIN_ATTEMPTS[client_ip] if current_time - t < 300]
        FAILED_LOGIN_ATTEMPTS[client_ip].append(current_time)

        if len(FAILED_LOGIN_ATTEMPTS[client_ip]) >= 5: # 5 tentativas erradas de login seguidas
            IP_BLOCKED_UNTIL[client_ip] = current_time + 1800 # Banir por 30 minutos
            bg = BackgroundTasks()
            bg.add_task(notify_admin_security_alert_background, "Tentativa de Invasão de Conta (Força Bruta no Login)", client_ip, "5 logins falhos consecutivos a partir deste IP.")
            response.background = bg

    # Headers de Segurança e CORS Garantidos
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data:;"
    
    return response

@app.on_event("startup")
def startup_db_init():
    try:
        Base.metadata.create_all(bind=engine)
        from sqlalchemy import text
        with engine.connect() as conn:
            # Tabelas mínimas e colunas vitais
            for cmd in [
                "ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS protocolo VARCHAR(20)",
                "ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS foto VARCHAR(255)",
                "ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS avaliacao_nota INTEGER",
                "ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS avaliacao_comentario TEXT",
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS tipo_usuario VARCHAR(20) DEFAULT 'cidadao'",
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ativo'",
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS genero VARCHAR(50)",
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS tentativas_login_falhas INTEGER DEFAULT 0",
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS bloqueado_ate TIMESTAMP",
                "ALTER TABLE admins_secretaria ADD COLUMN IF NOT EXISTS tentativas_login_falhas INTEGER DEFAULT 0",
                "ALTER TABLE admins_secretaria ADD COLUMN IF NOT EXISTS bloqueado_ate TIMESTAMP",
                "ALTER TABLE agendamentos ADD COLUMN IF NOT EXISTS senha VARCHAR(10)",

                "ALTER TABLE agendamentos ADD COLUMN IF NOT EXISTS avaliacao_nota INTEGER",
                "ALTER TABLE agendamentos ADD COLUMN IF NOT EXISTS avaliacao_comentario TEXT"
            ]:
                try: 
                    conn.execute(text(cmd))
                    conn.commit()
                except: pass
                
            try:
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS logs_instalacao_pwa (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER,
                    usuario_nome VARCHAR(150),
                    usuario_cpf VARCHAR(20),
                    dispositivo VARCHAR(50) NOT NULL,
                    user_agent TEXT,
                    ip_address VARCHAR(45),
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """))
                conn.commit()
            except Exception as e: print(f"Error creating logs_instalacao_pwa table: {e}")

            try:
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS avisos (
                    id SERIAL PRIMARY KEY,
                    titulo VARCHAR(200) NOT NULL,
                    mensagem TEXT NOT NULL,
                    tipo VARCHAR(50) DEFAULT 'info',
                    ativo INTEGER DEFAULT 1,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    autor_id INTEGER
                )
                """))
                conn.commit()
            except Exception as e: print(f"Error creating avisos table: {e}")

            try:
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS logs_invasao_seguranca (
                    id SERIAL PRIMARY KEY,
                    tipo_ataque VARCHAR(100) NOT NULL,
                    ip_origem VARCHAR(50),
                    detalhes TEXT,
                    bloqueado INTEGER DEFAULT 1,
                    alerta_sms_enviado INTEGER DEFAULT 0,
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """))
                conn.commit()
            except Exception as e: print(f"Error creating logs_invasao_seguranca table: {e}")
            
    except Exception as e: print(f"DB Init Error: {e}")

from .routes import auth, ocorrencias, secretarias, chat_ia, admin_users, agendamentos, admin_metrics, avisos, files, panico
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(ocorrencias.router, prefix="/api/ocorrencias", tags=["ocorrencias"])
app.include_router(secretarias.router, prefix="/api/secretarias", tags=["secretarias"])
app.include_router(chat_ia.router, prefix="/api/chat-ia", tags=["chat_ia"])
app.include_router(admin_users.router, prefix="/api/admin/users", tags=["admin_users"])
app.include_router(agendamentos.router, prefix="/api/agendamentos", tags=["agendamentos"])
app.include_router(admin_metrics.router, prefix="/api/admin/metrics", tags=["admin_metrics"])
app.include_router(avisos.router, prefix="/api/avisos", tags=["avisos"])
app.include_router(panico.router, prefix="/api/panico", tags=["panico"])

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "6.3.0-FINAL_V3"}

if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
