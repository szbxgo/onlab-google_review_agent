import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

# 1. Beállítások
URL = "https://8b1ea742-86f3-4e19-a534-329ee60572d7.eu-central-1-0.aws.cloud.qdrant.io"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.-0df-CLPC0u4MOKoOAS8aGb7MZpb8zkCYCfDW-zM0Mw"
COLLECTION_NAME = "first_reviews"

# 2. Kapcsolódás
client = QdrantClient(url=URL, api_key=API_KEY)

# 3. Modell betöltése
model = SentenceTransformer('all-MiniLM-L6-v2')

# 4. Adatok betöltése és tisztítása a repülés előtt
df = pd.read_csv('cleaned_reviews.csv')
# Ha maradt volna üres sor, azt most kőkeményen töröljük
df = df.dropna(subset=['Review_Text'])

# 5. Gyűjtemény létrehozása (a deprecated figyelmeztetés javításával)
if not client.collection_exists(collection_name=COLLECTION_NAME):
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=384, 
            distance=models.Distance.COSINE 
        )
    )
    print(f"Új gyűjtemény '{COLLECTION_NAME}' létrehozva.")
else:
    print(f"A '{COLLECTION_NAME}' gyűjtemény már létezik, folytatjuk a feltöltést.")

print("Vektorizálás és feltöltés indul...")

# 6. Adatok vektorizálása és feltöltése
points = []
for idx, row in df.iterrows():
    # Kényszerítjük, hogy szöveg legyen (megelőzzük a float hibát)
    text_content = str(row['Review_Text']).strip()
    
    if text_content and text_content != "nan": # Csak ha nem üres
        vector = model.encode(text_content).tolist()
        
        points.append(models.PointStruct(
            id=idx,
            vector=vector,
            payload={
                "customer": str(row['Customer_Name']),
                "review": text_content,
                "category": str(row['Service_Category'])
            }
        ))

# Feltöltés a felhőbe
if points:
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    print(f"Siker! {len(points)} vélemény sikeresen feltöltve a Qdrant Cloud-ba.")
else:
    print("Nem találtam feltölthető adatot.")