from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base
import os

# FastAPI Application for Colônia Digital
# Using Neon Postgres as the primary database

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .core.rate_limit import limiter
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(
    title="Colônia Digital API",
    description="API for Colônia Digital platform - Citizen Urban Occurrences",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-eval' 'unsafe-inline' https:; img-src 'self' data: https: blob:; connect-src 'self' https: wss:;"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Database initialization on startup
@app.on_event("startup")
def startup_db_init():
    try:
        # Auto-create tables if they don't exist
        print("Initializing database...")
        Base.metadata.create_all(bind=engine)
        
        # Sincronizar colunas novas (Migração Manual para MySQL/Render)
        from sqlalchemy import text
        with engine.begin() as conn:
            # Ocorrencias
            for col in [
                "ADD COLUMN protocolo VARCHAR(20)",
                "ADD COLUMN foto VARCHAR(255)",
                "ADD COLUMN video VARCHAR(255)"
            ]:
                try: conn.execute(text(f"ALTER TABLE ocorrencias {col}"))
                except Exception: pass
                
            for col in [
                "ADD COLUMN protocolo VARCHAR(20)",
                "ADD COLUMN motivo TEXT",
                "ADD COLUMN acompanhante VARCHAR(100)",
                "ADD COLUMN cartao_sus VARCHAR(50)",
                "ADD COLUMN anexo VARCHAR(255)",
                "ADD COLUMN criado_em DATETIME"
            ]:
                try: conn.execute(text(f"ALTER TABLE agendamentos {col}"))
                except Exception: pass
            
            # Reset de Senha Temporário (Produção)
            from .core.security import get_password_hash
            email_res = "alexandregilberto1994@gmail.com"
            hashed = get_password_hash("123456")
            try:
                conn.execute(text("UPDATE usuarios SET senha = :h WHERE email = :e"), {"h": hashed, "e": email_res})
                conn.execute(text("UPDATE secretaria_admins SET senha = :h WHERE email = :e"), {"h": hashed, "e": email_res})
            except Exception: pass
        
        # Seed secretarias if empty
        from .database import SessionLocal
        from .models.schema import Secretaria
        db = SessionLocal()
        try:
            if db.query(Secretaria).count() == 0:
                print("Seeding secretarias...")
                sec_names = ["Obras", "Saúde", "Educação", "Transporte", "Meio Ambiente", "Limpeza Urbana"]
                for name in sec_names:
                    db.add(Secretaria(nome=f"Secretaria de {name}" if "Limpeza" not in name else name))
                db.commit()
                print("Seeding complete.")
        finally:
            db.close()
    except Exception as e:
        print(f"Error initializing database: {e}")

# CORS configuration
origins = [
    "https://leopoldina-digital-1b75e.web.app",
    "https://leopoldina-digital-1b75e.firebaseapp.com",
    "https://prefeitura-digital.onrender.com",
    "https://prefeitura-digital-backend.onrender.com",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "null",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .routes import auth, ocorrencias, secretarias, chat_ia, admin_users, agendamentos, admin_metrics

@app.get("/")
def read_root():
    return {"message": "Welcome to Colônia Digital API"}

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(ocorrencias.router, prefix="/api/ocorrencias", tags=["ocorrencias"])
app.include_router(secretarias.router, prefix="/api/secretarias", tags=["secretarias"])
app.include_router(chat_ia.router, prefix="/api/chat-ia", tags=["chat_ia"])
app.include_router(admin_users.router, prefix="/api/admin/users", tags=["admin_users"])
app.include_router(agendamentos.router, prefix="/api/agendamentos", tags=["agendamentos"])
app.include_router(admin_metrics.router, prefix="/api/admin/metrics", tags=["admin_metrics"])


# Mount the 'uploads' directory to serve files (photos/videos)
if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Serve the frontend files
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    # Optional: print warning if frontend not found where expected
    print(f"Warning: Frontend path not found at {frontend_path}")
