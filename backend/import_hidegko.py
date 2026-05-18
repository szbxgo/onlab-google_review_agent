import uuid
import pandas as pd
from dotenv import load_dotenv
from database import SessionLocal
import models

# Importáljuk a te kész AI feltöltődet!
from db_feltoltes import process_and_upload 

# 1. Beállítások
FILE_PATH = "hidegko_reviews.csv"
BUSINESS_ID = 1 

load_dotenv()
db = SessionLocal()

# Ellenőrizzük, hogy létezik-e a cég
business = db.query(models.Business).filter(models.Business.id == BUSINESS_ID).first()
if not business:
    print(f"HIBA: Nincs ilyen cég a(z) {BUSINESS_ID} ID-val!")
    exit()

print(f"--- Adatok betöltése a(z) {business.name} profilhoz ---")

# 2. A nyers CSV beolvasása
df = pd.read_csv(FILE_PATH, on_bad_lines='skip')

success_count = 0
for idx, row in df.iterrows():
    try:
        # A. Adatok kinyerése az Apify/Scraper oszlopokból
        # 0. oszlop: Név, 3. oszlop: Szöveg
        author = str(row.iloc[0]).strip()
        if author == "nan": 
            author = "Anonim Vendég"

        raw_text = str(row.iloc[3]).strip()
        review_text = raw_text if raw_text != "nan" and raw_text else "Csak értékelés (szöveg nélkül)"

        # Csillagok (a raw CSV-ből nehéz kinyerni, a demóhoz 5-öst kapnak)
        rating = 5 
        
        # Generálunk egy kamu Google azonosítót, hogy ne legyen SQL hiba
        g_id = f"csv_import_{uuid.uuid4().hex[:8]}"

        # B. Mentés a Render PostgreSQL adatbázisba
        new_review = models.Review(
            business_id=BUSINESS_ID,
            google_review_id=g_id,
            author=author,
            text=review_text,
            rating=rating
        )
        db.add(new_review)
        db.commit()

        # C. Vektorizálás és feltöltés a Qdrant Cloudba
        process_and_upload(
            review_text=review_text,
            author=author,
            rating=rating,
            business_id=BUSINESS_ID
        )
        
        success_count += 1
        print(f"[{success_count}] SIKER: {author} véleménye feldolgozva.")

    except Exception as e:
        print(f"Hiba a(z) {idx}. sornál: {e}")

db.close()
print(f"--- KÉSZ! {success_count} vélemény sikeresen a rendszerben! ---")