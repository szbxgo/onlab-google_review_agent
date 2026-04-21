import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from database import Base # A korábban megbeszélt database.py-ból
import models # A korábban megbeszélt models.py-ból

# 1. Környezeti változók betöltése
load_dotenv()
db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("HIBA: A DATABASE_URL nem található a környezeti változók között!")
else:
    try:
        # 2. Kapcsolódás (SQLAlchemy-nek kell a +psycopg2 a PostgreSQL elé)
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        
        # SSL mód kényszerítése a külső kapcsolathoz
        if "?sslmode=require" not in db_url:
            db_url += "?sslmode=require"

        engine = create_engine(db_url)
        
        # 3. Táblák létrehozása
        print("Kapcsolódás és táblák létrehozása folyamatban...")
        Base.metadata.create_all(bind=engine)
        
        print("SIKER! Az adatbázis szerkezete létrejött a Renderen.")
        
    except Exception as e:
        print(f"HIBA történt a kapcsolódás során: {e}")