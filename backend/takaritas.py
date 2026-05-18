import os
from dotenv import load_dotenv
from database import SessionLocal
import models
from qdrant_client import QdrantClient
from qdrant_client.http import models as q_models

load_dotenv()

print("--- TÉVES ADATOK TÖRLÉSE (BUSINESS_ID = 1) ---")

# 1. Törlés a Render PostgreSQL adatbázisból
db = SessionLocal()
deleted_sql = db.query(models.Review).filter(models.Review.business_id == 1).delete()
db.commit()
db.close()
print(f"-> {deleted_sql} db vélemény sikeresen törölve a PostgreSQL adatbázisból.")

# 2. Törlés a Qdrant Cloud felhőből
q_client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
q_client.delete(
    collection_name="reviews",
    points_selector=q_models.Filter(
        must=[
            q_models.FieldCondition(
                key="business_id",
                match=q_models.MatchValue(value=1),
            )
        ]
    ),
)
print("-> A vektorok sikeresen törölve a Qdrant felhőből az 1-es ID szűrővel.")
print("--- TAKARÍTÁS KÉSZ! ---")