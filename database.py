import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# A Renderen beállított DATABASE_URL-t olvassuk be
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if SQLALCHEMY_DATABASE_URL is None:
    raise ValueError("HIBA: A DATABASE_URL nincs beállítva a .env fájlban!")

# A SQLAlchemy-nek PostgreSQL esetén postgresql:// kezdet kell
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Engine létrehozása
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Munkamenet (Session) létrehozása a lekérdezésekhez
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Alaposztály a modelleknek
Base = declarative_base()

# Függőség az API végpontokhoz
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()