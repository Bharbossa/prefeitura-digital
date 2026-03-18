from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base
import os

# Tables are created via database/schema.sql
# Auto-create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Leopoldina Digital API",
    description="API for Leopoldina Digital platform - Citizen Urban Occurrences",
    version="1.0.0"
)

# CORS configuration
origins = [
    "http://localhost",
    "http://localhost:5500",
    "http://localhost:8000",
    "http://localhost:10000",
    "http://127.0.0.1",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:10000",
    "http://prefeitura-digital-teste:10000",
    "https://leopoldina-digital-1b75e.web.app",
    "https://leopoldina-digital-1b75e.firebaseapp.com",
    "https://prefeitura-digital.onrender.com",
    "https://prefeitura-digital-backend.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes import auth, ocorrencias, secretarias, chat_ia

@app.get("/")
def read_root():
    return {"message": "Welcome to Leopoldina Digital API"}

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(ocorrencias.router, prefix="/api/ocorrencias", tags=["ocorrencias"])
app.include_router(secretarias.router, prefix="/api/secretarias", tags=["secretarias"])
app.include_router(chat_ia.router, prefix="/api/chat-ia", tags=["chat_ia"])

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
