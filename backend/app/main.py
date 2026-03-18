from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base
import os

# Tables are created via database/schema.sql
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Leopoldina Digital API",
    description="API for Leopoldina Digital platform - Citizen Urban Occurrences",
    version="1.0.0"
)

# CORS configuration
origins = [
    "http://localhost",
    "http://localhost:5500",
    "http://127.0.0.1",
    "http://127.0.0.1:5500",
    "http://prefeitura-digital-teste:10000",
    "https://leopoldina-digital-1b75e.web.app",
    "https://leopoldina-digital-1b75e.firebaseapp.com"
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
