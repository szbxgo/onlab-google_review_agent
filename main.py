import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http import models as q_models
from google import genai  
from sqlalchemy.orm import Session
from database import get_db, engine
import models
models.Base.metadata.create_all(bind=engine)

import requests
from fastapi.responses import RedirectResponse

from jose import jwt
from datetime import datetime, timedelta

app = FastAPI()

load_dotenv()

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

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))


# JWT token generálása
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 4. ÚJ VÉGPONT: Jelenlegi vállalkozás azonosító lekérése a tokenből (minden védett végpont ezt használja majd)
async def get_current_business_id(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Nincs token!")
    try:
        token = authorization.split(" ")[1] # "Bearer <token>" formátum
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except:
        raise HTTPException(status_code=401, detail="Érvénytelen token!")

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
        model="gemini-embedding-001", 
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
async def get_stats(business_id: int, current_id: int = Depends(get_current_business_id), db: Session = Depends(get_db)):
    if business_id != current_id:
        raise HTTPException(status_code=403, detail="Nincs jogosultságod ehhez a céghez!")
    
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


# A Google visszahívási végpont (ide érkezik meg a felhasználó) a main.py végén található, mert oda tartozik logikailag.
# 2. Google visszahívási végpont (ide érkezik meg a felhasználó)
@app.get("/auth/google/callback")
async def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    business_id = int(state)
    
    # Itt váltjuk be a kódot tokenekre
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    
    res = requests.post(token_url, data=data).json()
    
    # Mentjük a tokeneket az adatbázisba
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    if business:
        business.google_refresh_token = res.get("refresh_token")
        db.commit()
        
        # 3. GENERÁLUNK EGY SAJÁT JWT TOKENT
        access_token = create_access_token(data={"sub": str(business.id)})
        
        # 4. Visszaküldjük a frontendnek a tokent az URL-ben
        return RedirectResponse(url=f"http://127.0.0.1:5500/dashboard.html?token={access_token}&id={business.id}")


# --- GOOGLE OAUTH2 FOLYAMAT ---
# 1. Átirányítás a Google bejelentkezéshez
@app.get("/auth/google/{business_id}")
async def auth_google(business_id: int):
    # Itt mondjuk meg a Google-nek, hogy mihez kérünk hozzáférést (scope)
    # A 'business_management' kell a véleményekhez
    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/business.manage"
    ]
    scope_param = " ".join(scopes)

    google_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&scope={scope_param}&access_type=offline&prompt=consent&state={business_id}"
    )
    print(f"---GENERÁLT LINK: {google_url}")
    return RedirectResponse(google_url)


#
# 3. ÚJ VÉGPONT: Vélemények kézi frissítése a Google-ből
@app.post("/sync-google-reviews/{business_id}")
async def sync_reviews(business_id: int, db: Session = Depends(get_db)):
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    if not business or not business.google_refresh_token:
        raise HTTPException(status_code=400, detail="Nincs Google kapcsolat.")
    
    # ITT FOG MEGTÖRTÉNNI A VARÁZSLAT:
    # 1. Access token frissítése a refresh_tokennel
    # 2. Vélemények letöltése a Google API-ról
    # 3. db_feltoltes.py-ban lévő logic meghívása (vektorizálás + Qdrant)
    
    return {"message": "Szinkronizáció elindítva!"}

