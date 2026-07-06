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
