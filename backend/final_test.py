import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
url = os.getenv("DATABASE_URL")

print(f"DEBUG: Az URL eleje: {url[:25]}...")
if "-a" in url:
    print("HIBA: Még mindig a belső (-a) URL-t próbálod használni!")

try:
    print("Csatlakozás...")
    conn = psycopg2.connect(url, sslmode='require')
    print("SIKER! Az adatbázis elérhető.")
    conn.close()
except Exception as e:
    print(f"HIBA: {e}")