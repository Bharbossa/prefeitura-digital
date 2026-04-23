from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base, get_db
import os

app = FastAPI(title="Colônia Digital API", version="6.0.0-CORS_MAX")

# 1. CORS - CONFIGURAÇÃO TOTALMENTE ABERTA (MODO EMERGÊNCIA)
# Nota: Quando allow_origins=["*"], allow_credentials deve ser False.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS tipo_usuario VARCHAR(20) DEFAULT 'cidadao'",
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ativo'"
            ]:
                try: 
                    conn.execute(text(cmd))
                    conn.commit()
                except: pass
    except Exception as e: print(f"DB Init Error: {e}")

from .routes import auth, ocorrencias, secretarias, chat_ia, admin_users, agendamentos, admin_metrics
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(ocorrencias.router, prefix="/api/ocorrencias", tags=["ocorrencias"])
app.include_router(secretarias.router, prefix="/api/secretarias", tags=["secretarias"])
app.include_router(chat_ia.router, prefix="/api/chat-ia", tags=["chat_ia"])
app.include_router(admin_users.router, prefix="/api/admin/users", tags=["admin_users"])
app.include_router(agendamentos.router, prefix="/api/agendamentos", tags=["agendamentos"])
app.include_router(admin_metrics.router, prefix="/api/admin/metrics", tags=["admin_metrics"])

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "6.0.0-ULTRA_LIBERADO"}

if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
