import os
import pandas as pd
import uuid
from google import genai
from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv

load_dotenv()

# --- Konfiguráció ---
# Az új SDK-hoz Client objektumot használunk genai.configure helyett
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
COLLECTION_NAME = "reviews"
EMBED_MODEL = "gemini-embedding-001"

# 1. Központi funkció: Ez az összeköttetés a CSV és az API között
# Vektorizálja a véleményt a Gemini API-val, majd feltölti a Qdrant-ba egy payload szűréssel, hogy később RAG-nél biztonságosan lehessen használni[cite: 199, 201].
def process_and_upload(review_text, author, rating, business_id):
    """
    Vektorizálja a szöveget és feltölti a Qdrant-ba a 'business_id' metaadattal.
    Ez a business_id biztosítja, hogy az ügyfelek adatai ne keveredjenek (Payload Filtering)[cite: 198, 201].
    """
    # Vektorizálás az új SDK-val (768 dimenzió)
    result = gemini_client.models.embed_content(
        model=EMBED_MODEL,
        contents=review_text
    )
    
    # Az új SDK-ban így érjük el a vektor értékeket
    embedding = result.embeddings[0].values

    # Feltöltés a Qdrant-ba
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=str(uuid.uuid4()), # Generálunk egy egyedi ID-t
                vector=embedding,
                payload={
                    "business_id": business_id, # Ez alapján fogunk szűrni a RAG-nél [cite: 201]
                    "review": review_text,
                    "author": author,
                    "rating": rating
                }
            )
        ]
    )

# ADATFORRÁSOK 2.1 CSV fájl (cleaned_reviews.csv) - Ez a jelenlegi forrásunk, amíg a Google API-t nem implementáljuk [cite: 98]
# --- FORRÁS A: CSV Betöltés (JELENLEG EZ FUT) ---
def upload_from_csv(file_path, business_id):
    print(f"Adatok betöltése CSV-ből a(z) {business_id} ID-hoz...")
    df = pd.read_csv(file_path)
    for _, row in df.iterrows():
        # Ellenőrizzük, hogy a szöveg nem üres-e a hiba elkerülése végett
        text = str(row['Review_Text']).strip()
        if text:
            process_and_upload(
                review_text=text,
                author=row.get('Author', 'Ismeretlen'),
                rating=row.get('Review_Rating', 5),
                business_id=business_id
            )
    print("CSV feltöltés kész!")

# ADATFORRÁSOK 2.2 Google Business API - Ez a jövőbeni tervünk, hogy közvetlenül a Google-tól szedjük az adatokat [cite: 100, 205]
# --- FORRÁS B: Google Business API ---

# def upload_from_google_api(access_token, business_id):
#     print(f"--- Google API szinkronizáció (Business ID: {business_id}) ---")
#     # 1. Itt hívjuk meg a Google API-t az access_tokennel [cite: 207]
#     # headers = {"Authorization": f"Bearer {access_token}"}
#     # response = requests.get(f"https://mybusiness.googleapis.com/v4/accounts/.../locations/.../reviews", headers=headers)
#     # google_reviews = response.json().get('reviews', [])

#     # 2. Végigmennél a kapott JSON válaszokon
#     # for g_review in google_reviews:
#     #     process_and_upload(
#     #         review_text=g_review['comment'],
#     #         author=g_review['reviewer']['displayName'],
#     #         rating=g_review['starRating'],
#     #         business_id=business_id # Az adatbázisból kapott egyedi ID 
#     #     )
#     # print("Google API szinkronizáció kész.")

if __name__ == "__main__":
    # --- JELENLEGI MŰKÖDÉS (CSV) ---
    # Ha új ügyfelet (business_id) töltesz be, csak add meg az ID-t és a fájlját [cite: 189]
    upload_from_csv('cleaned_reviews.csv', business_id=1) 
    
    # --- JÖVŐBELI MŰKÖDÉS (GOOGLE API) ---
    # Ha kész a Google OAuth2[cite: 205, 206], csak ezt hívod meg a CSV helyett:
    # upload_from_google_api(access_token="...", business_id=1)