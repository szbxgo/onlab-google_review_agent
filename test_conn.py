import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")

print(f"Tesztelés ezzel az URL-lel: {url[:20]}...")

try:
    # Megpróbálunk direktben csatlakozni a psycopg2-vel, SQLAlchemy nélkül
    conn = psycopg2.connect(url)
    print("Siker! A hálózati kapcsolat és a jelszó is JÓ.")
    conn.close()
except Exception as e:
    print("\nHIBA RÉSZLETEI:")
    print(e)