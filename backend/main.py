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
import models as models
models.Base.metadata.create_all(bind=engine)

import requests
from fastapi.responses import RedirectResponse
from fastapi import BackgroundTasks
from db_feltoltes import process_and_upload
from fastapi import Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from jose import jwt
from datetime import datetime, timedelta

app = FastAPI()

load_dotenv()

origins = [
    "https://review-agent.agency", # Az új domained www nélkül
    "https://www.review-agent.agency", # És www-vel is biztos ami biztos
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
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

# Átírjuk a jogosultság-ellenőrző függvényt
async def get_current_business_id(request: Request):
    # 1. Megpróbáljuk kiolvasni a tokent a biztonságos sütiből
    token = request.cookies.get("access_token")
    
    # (Opcionális: Visszafelé kompatibilitás a régi módszerhez tesztelésnél)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(status_code=401, detail="Nincs token (nem vagy bejelentkezve)!")
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except:
        raise HTTPException(status_code=401, detail="Érvénytelen vagy lejárt token!")
    
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
async def generate_response(
    request: ReviewRequest, 
    current_id: int = Depends(get_current_business_id), 
    db: Session = Depends(get_db)):

    if request.business_id != current_id:
        raise HTTPException(status_code=403, detail="Nincs jogosultságod ehhez a céghez!")
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
async def get_all_reviews(
    business_id: int, 
    current_id: int = Depends(get_current_business_id), 
    db: Session = Depends(get_db)):

    if business_id != current_id:
        raise HTTPException(status_code=403, detail="Nincs jogosultságod ehhez a céghez!")
    
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
async def get_analytics(
    business_id: int, 
    current_id: int = Depends(get_current_business_id), 
    db: Session = Depends(get_db)):
    
    if business_id != current_id:
        raise HTTPException(status_code=403, detail="Nincs jogosultságod ehhez a céghez!")
    
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    reviews = db.query(models.Review).filter(models.Review.business_id == business_id).all()
    
    # 1. Új Access Token kérése a Refresh Tokennel
    # (A Google Access Token csak 1 órát él, ezért mindig frissíteni kell)
    
    # 2. Account ID lekérése
    # GET https://mybusinessbusinessinformation.googleapis.com/v1/accounts
    
    # 3. Location ID lekérése
    # GET https://mybusinessbusinessinformation.googleapis.com/v1/accounts/{acc_id}/locations
    
    # 4. Vélemények lekérése
    # GET https://mybusiness.googleapis.com/v1/accounts/{acc_id}/locations/{loc_id}/reviews

    token = business.google_refresh_token
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
    
    access_token = res.get("access_token")
    refresh_token = res.get("refresh_token")
    business_id = int(state)
    # Mentjük a tokeneket az adatbázisba
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    if business:
        if res.get("refresh_token"):
            business.google_refresh_token = res.get("refresh_token")

        if access_token:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            try:
                # 1. Fiókok (Accounts) lekérése
                acc_url = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
                acc_data = requests.get(acc_url, headers=headers).json()
                
                # Ha van fiók, kiválasztjuk az elsőt (MVP szinten ez tökéletes)
                if 'accounts' in acc_data and len(acc_data['accounts']) > 0:
                    # A Google "accounts/12345" formátumban adja vissza, nekünk csak a szám kell
                    raw_acc_name = acc_data['accounts'][0]['name']
                    account_id = raw_acc_name.split('/')[-1] 
                    business.google_account_id = account_id
                    
                    # 2. Helyszínek (Locations) lekérése az adott fiókhoz
                    loc_url = f"https://mybusinessbusinessinformation.googleapis.com/v1/accounts/{account_id}/locations?readMask=name"
                    loc_data = requests.get(loc_url, headers=headers).json()
                    
                    if 'locations' in loc_data and len(loc_data['locations']) > 0:
                        raw_loc_name = loc_data['locations'][0]['name']
                        location_id = raw_loc_name.split('/')[-1]
                        business.google_location_id = location_id
                        
            except Exception as e:
                print(f"Hiba a Google ID-k lekérésekor: {e}")
        
        db.commit()
        
        # 2. Átirányítás a dashboardra (NINCS TOKEN AZ URL-BEN!)
        response = RedirectResponse(url="/dashboard.html")
        
        # 3. JWT beállítása HttpOnly sütiként (Javascript nem látja, nem lopható)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,  # Kiemelten fontos XSS védelem!
            secure=True,    # Csak HTTPS kapcsolaton keresztül működik
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        # 4. Business ID beállítása sima sütiként (hogy a frontend JS lássa, hol vagyunk)
        response.set_cookie(
            key="business_id",
            value=str(business.id),
            httponly=False
        )
        
        return response


def ingest_review_to_rag(review_text, business_id):
    # 1. Gemini Embedding hívása
    embedding = genai.embed_content(
        model="models/embedding-001",
        content=review_text,
        task_type="retrieval_document"
    )
    
    # 2. Feltöltés Qdrant-ba
    qdrant_client.upsert(
        collection_name="reviews",
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding['embedding'],
                payload={"business_id": business_id, "text": review_text}
            )
        ]
    )

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
async def sync_reviews(
    business_id: int, 
    background_tasks: BackgroundTasks, # Háttérfolyamat kezelő
    current_id: int = Depends(get_current_business_id), 
    db: Session = Depends(get_db)):

    # 1. Jogosultság ellenőrzése (javított indentációval)
    if business_id != current_id:
        raise HTTPException(status_code=403, detail="Nincs jogosultságod ehhez a céghez!")

    business = db.query(models.Business).filter(models.Business.id == business_id).first()

    if not business or not business.google_refresh_token:
        raise HTTPException(status_code=400, detail="Nincs Google kapcsolat.")
    
    # 2. Szinkronizáció indítása a háttérben
    background_tasks.add_task(perform_google_sync, business, db)
    
    return {"message": "Szinkronizáció elindítva a háttérben!"}

# --- SEGÉDFÜGGVÉNY A SZINKRONIZÁCIÓHOZ ---
def perform_google_sync(business, db: Session):
    try:
        # 1. Access Token frissítése
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": business.google_refresh_token,
            "grant_type": "refresh_token",
        }
        token_res = requests.post(token_url, data=data).json()
        access_token = token_res.get("access_token")

        # 2. Vélemények lekérése a Google-től 
        # (Feltételezve, hogy a google_account_id és location_id már megvan)
        acc_id = business.google_account_id
        loc_id = business.google_location_id
        
        if not acc_id or not loc_id:
            print(f"Hiba: Hiányzó Google azonosítók a cégnél: {business.id}")
            return

        reviews_url = f"https://mybusiness.googleapis.com/v1/accounts/{acc_id}/locations/{loc_id}/reviews"
        headers = {"Authorization": f"Bearer {access_token}"}
        reviews_res = requests.get(reviews_url, headers=headers).json()
        google_reviews = reviews_res.get('reviews', [])

        for g_review in google_reviews:
            g_id = g_review['reviewId']
            
            # Csak akkor mentjük, ha még nincs benne (google_review_id alapján)
            exists = db.query(models.Review).filter(models.Review.google_review_id == g_id).first()
            if not exists:
                # SQL mentés
                new_review = models.Review(
                    business_id=business.id,
                    google_review_id=g_id,
                    author=g_review['reviewer']['displayName'],
                    text=g_review['comment'],
                    rating=g_review['starRating']
                )
                db.add(new_review)
                db.commit()

                # Vektorizálás és Qdrant feltöltés a meglévő logikáddal
                process_and_upload(
                    review_text=new_review.text,
                    author=new_review.author,
                    rating=new_review.rating,
                    business_id=business.id
                )
        print(f"Sikeres szinkronizáció: {business.name}")
        
    except Exception as e:
        print(f"Hiba a szinkronizáció során: {e}")

# --- FRONTEND KISZOLGÁLÁSA ---
# Minden egyéb végpont (API) után kell definiálni!
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

# A gyökér URL (/) kiszolgálja az index.html-t
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# Minden más oldalt (pl. /dashboard.html) közvetlenül a frontend mappából adunk vissza
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)




