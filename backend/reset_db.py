from database import engine, Base
import models as models  # Fontos: be kell tölteni a modelleket, hogy a Base lássa őket!
from sqlalchemy import text

def reset_database():
    print("--- ADATBÁZIS RESET INDÍTÁSA ---")
    
    try:
        # 1. Kapcsolat tesztelése
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("Siker! Kapcsolat az adatbázissal rendben.")

        # 2. Táblák törlése
        print("Régi táblák törlése...")
        Base.metadata.drop_all(bind=engine)

        # 3. Táblák létrehozása
        print("Új táblák létrehozása (Google Business mezőkkel)...")
        Base.metadata.create_all(bind=engine)

        print("--- KÉSZ! Az adatbázis sikeresen frissítve. ---")

    except Exception as e:
        print(f"\nHIBA TÖRTÉNET: \n{e}")
        print("\nPróbáld meg ellenőrizni a jelszót az .env fájlban!")

if __name__ == "__main__":
    reset_database()