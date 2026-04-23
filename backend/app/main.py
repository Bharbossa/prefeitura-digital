from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base, get_db
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
import os

# FastAPI Application for Colônia Digital
app = FastAPI(
    title="Colônia Digital API",
    description="API for Colônia Digital platform",
    version="1.0.0"
)

# 1. DATABASE INITIALIZATION
@app.on_event("startup")
def startup_db_init():
    try:
        Base.metadata.create_all(bind=engine)
        from sqlalchemy import text
        
        # Sync columns
        tables_cols = {
            "ocorrencias": ["protocolo VARCHAR(20)", "foto VARCHAR(255)", "video VARCHAR(255)", "documento VARCHAR(255)"],
            "usuarios": ["telefone VARCHAR(20)", "status VARCHAR(20)", "whatsapp VARCHAR(20)"],
            "agendamentos": ["protocolo VARCHAR(20)", "motivo TEXT", "acompanhante VARCHAR(100)", "cartao_sus VARCHAR(50)", "anexo VARCHAR(255)", "criado_em DATETIME"]
        }
        
        for table, cols in tables_cols.items():
            for col in cols:
                try:
                    with engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col}"))
                        conn.commit()
                except Exception: pass

        # Emergency Reset
        from .core.security import get_password_hash
        email_res = "alexandregilberto1994@gmail.com"
        hashed = get_password_hash("123456")
        try:
            with engine.connect() as conn:
                conn.execute(text("UPDATE usuarios SET senha_hash = :h, status = 'ativo' WHERE LOWER(email) = LOWER(:e)"), {"h": hashed, "e": email_res})
                conn.execute(text("UPDATE admins_secretaria SET senha_hash = :h WHERE LOWER(email) = LOWER(:e)"), {"h": hashed, "e": email_res})
                conn.commit()
        except Exception: pass
            
    except Exception as e:
        print(f"Error initializing database: {e}")

# 2. ROUTES
from .routes import auth, ocorrencias, secretarias, chat_ia, admin_users, agendamentos, admin_metrics

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(ocorrencias.router, prefix="/api/ocorrencias", tags=["ocorrencias"])
app.include_router(secretarias.router, prefix="/api/secretarias", tags=["secretarias"])
app.include_router(chat_ia.router, prefix="/api/chat-ia", tags=["chat_ia"])
app.include_router(admin_users.router, prefix="/api/admin/users", tags=["admin_users"])
app.include_router(agendamentos.router, prefix="/api/agendamentos", tags=["agendamentos"])
app.include_router(admin_metrics.router, prefix="/api/admin/metrics", tags=["admin_metrics"])

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "5.0.0-CLEAN_STABLE"}

# 3. MIDDLEWARES (Ordem: O último adicionado é o primeiro a processar o request)

# Security Headers (Sem CSP restritivo por enquanto)
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# CORS (DEVE SER O ÚLTIMO ADICIONADO PARA FUNCIONAR O PREFLIGHT)
origins = [
    "https://leopoldina-digital-1b75e.web.app",
    "https://leopoldina-digital-1b75e.firebaseapp.com",
    "https://prefeitura-digital.onrender.com",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. STATIC FILES
if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
