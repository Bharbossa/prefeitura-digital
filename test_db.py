import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv(os.path.join("backend", ".env"))
db_url = os.getenv("RENDER_DB_URL") or os.getenv("DATABASE_URL")
base_url = "mysql+pymysql://prefeituradigital_user:w3P5Xh4n98e9u0192hR2d0V1d9p1@dpg-cv20h5i3r3ds73e04v10-a.oregon-postgres.render.com/prefeituradigital"

engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

from backend.app.models.schema import AdminSecretaria
print("Sub-Admins:")
for admin in db.query(AdminSecretaria).all():
    print(admin.email, admin.status)
