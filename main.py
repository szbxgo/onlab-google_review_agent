import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http import models as q_models
from google import genai  
from sqlalchemy.orm import Session
from database import get_db, engine
import models
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Konfiguráció ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "reviews"

# Kliensek inicializálása az új módon
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
q_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

class LoginRequest(BaseModel):
    email: str

class ReviewRequest(BaseModel):
    review_text: str
    business_id: int


def get_embedding(text):
    """Vektorizálás a 3072 dimenziós modellel"""
    # Ugyanaz a modell, amit a feltöltésnél használtál!
    result = gemini_client.models.embed_content(
        model="gemini-embedding-2-preview", 
        contents=text
    )
    return result.embeddings[0].values

# --- BEJELENTKEZÉS ---
@app.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    business = db.query(models.Business).filter(models.Business.email == request.email).first()
    if not business:
        raise HTTPException(status_code=401, detail="Nincs regisztrált vállalkozás ezzel az email címmel.")
    return {"business_id": business.id, "business_name": business.name}

@app.post("/generate")
async def generate_response(request: ReviewRequest, db: Session = Depends(get_db)):
    try:
        # 1. Cégadatok lekérése SQL-ből
        business = db.query(models.Business).filter(models.Business.id == request.business_id).first()
        
        if not business:
            raise HTTPException(status_code=404, detail="Cég nem található.")

        # 2. Új vélemény vektorizálása
        res = gemini_client.models.embed_content(model="gemini-embedding-2-preview", contents=request.review_text)
        query_vector = res.embeddings[0].values

        # 3. RAG keresés a reviews gyűjteményben business_id szűréssel
        search_result = q_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=q_models.Filter(
                must=[
                    q_models.FieldCondition(
                        key="business_id",
                        match=q_models.MatchValue(value=request.business_id),
                    )
                ]
            ),
            limit=3
        )
        
        # 4. Kontextus összefűzése
        context = ""
        for res in search_result:
            context += f"\n- Korábbi eset: {res.payload.get('review', '')}\n"
        
        # 5. Válasz generálása (Flash modellel a sebességért)
        prompt = f"""
        Te {business.name} AI asszisztense vagy. 
        Irányelv: {business.style_guideline}
        Segítség (múltbéli válaszok): {context}
        
        Ügyfél véleménye: {request.review_text}
        Írj egy profi választ magyarul!
        """
        
        # Generálás az új SDK szerint
        response = gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        
        return {"answer": response.text}

    except Exception as e:
        print(f"Hiba: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 1. Statisztikák (Dashboard-hoz)
@app.get("/stats/{business_id}")
async def get_stats(business_id: int, db: Session = Depends(get_db)):
    total = db.query(models.Review).filter(models.Review.business_id == business_id).count()
    # Itt fix értékeket adunk, amíg nincs több adatunk
    return {
        "total_reviews": total,
        "ai_ratio": "92%",
        "rating": "4.9 ★"
    }


# 2. Összes vélemény listázása (Reviews oldalhoz)
@app.get("/all-reviews/{business_id}")
async def get_all_reviews(business_id: int, db: Session = Depends(get_db)):
    reviews = db.query(models.Review).filter(models.Review.business_id == business_id).all()
    # Átalakítjuk a frontend által várt formátumra
    return [
        {
            "Author_Name": r.author or "Vendég",
            "Review_Text": r.review_text,
            "Review_Rating": r.rating
        } for r in reviews
    ]


# 3. Analytics (Analytics oldalhoz)
@app.get("/analytics/{business_id}")
async def get_analytics(business_id: int, db: Session = Depends(get_db)):
    reviews = db.query(models.Review).filter(models.Review.business_id == business_id).all()
    
    # Értékelések eloszlása a grafikonhoz
    ratings_count = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in reviews:
        ratings_count[r.rating] = ratings_count.get(r.rating, 0) + 1

    # AI összefoglaló generálása
    sample = "\n".join([r.review_text for r in reviews[-5:]])
    model = gemini_client.models.generate_content(
        model="gemini-1.5-flash",
        contents=f"Írj egy rövid, 3 mondatos üzleti elemzést ezek alapján: {sample}"
    )

    return {
        "ai_report": model.text,
        "ratings": ratings_count
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)