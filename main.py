from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from google import genai
import pandas as pd
import os

app = FastAPI()

# Fontos: Ez engedi meg a HTML oldaladnak, hogy beszélgessen a Pythonnal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Élesben ide a domainjeidet írjuk majd
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Konfiguráció ---
URL = "https://8b1ea742-86f3-4e19-a534-329ee60572d7.eu-central-1-0.aws.cloud.qdrant.io"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.-0df-CLPC0u4MOKoOAS8aGb7MZpb8zkCYCfDW-zM0Mw"
COLLECTION_NAME = "first_reviews"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Hiba: Nincs beállítva Gemini API Kulcs környezeti változója.")
    
# Modellek betöltése egyszer az induláskor
client = QdrantClient(url=URL, api_key=API_KEY)
embed_model = SentenceTransformer('all-MiniLM-L6-v2')
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

class ReviewRequest(BaseModel):
    review_text: str

@app.post("/generate")
async def generate_response(request: ReviewRequest):
    try:
        # A. Vektorizálás
        query_vector = embed_model.encode(request.review_text).tolist()
        
        # B. KERESÉS - Itt a javítás! query_points-ot használunk .points-al a végén
        search_result = client.query_points(
            collection_name=COLLECTION_NAME, 
            query=query_vector, 
            limit=2
        ).points
        
        # C. Kontextus építése
        context = ""
        for res in search_result:
            context += f"\n- Korábbi vélemény: {res.payload.get('review', 'Nincs szöveg')}\n"
        
        # D. Gemini Generálás
        prompt = f"Te Jóri István AI asszisztense vagy. Kontextus:\n{context}\nÚj vélemény: {request.review_text}"
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        
        return {"answer": response.text}
    except Exception as e:
        print(f"Hiba a szerveren: {e}") # Ezt látod a terminálban
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    df = pd.read_csv('cleaned_reviews.csv')
    # Vegyük az utolsó 5 véleményt egy gyors elemzéshez
    recent_text = " ".join(df['Review_Text'].tail(5).tolist())
    
    analysis = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Mondd meg egy mondatban, milyen a hangulata ezeknek a véleményeknek: {recent_text}"
    )
    
    return {
        "total_reviews": len(df),
        "sentiment": analysis.text,
        "average_rating": 4.9
    }

@app.get("/all-reviews")
async def get_all_reviews():
    try:
        # Beolvassuk a CSV-t
        df = pd.read_csv('cleaned_reviews.csv')
        # JSON formátumba alakítjuk, hogy a weboldal megértse
        # Csak az első 50-et küldjük el, hogy ne lassuljon be az oldal
        data = df.head(50).to_dict(orient='records')
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/analytics")
async def get_analytics():
    try:
        df = pd.read_csv('cleaned_reviews.csv')
        
        # 1. Alapstatisztikák a grafikonhoz
        rating_counts = df['Review_Rating'].value_counts().sort_index().to_dict()
        
        # 2. AI Elemzés: Vegyük a legfrissebb véleményeket
        sample_reviews = "\n".join(df['Review_Text'].tail(15).astype(str).tolist())
        
        analysis_prompt = f"""
        Elemezd az alábbi véleményeket üzleti szempontból:
        {sample_reviews}
        Készíts egy rövid jelentést: 
        1. Mi a legfőbb erősségünk?
        2. Mi a leggyakoribb panasz vagy fejlesztendő terület?
        3. Egy mondatos jövőbeli javaslat.
        Magyarul, professzionális stílusban válaszolj!
        """
        
        report = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=analysis_prompt,
        )
        
        return {
            "ratings": rating_counts,
            "ai_report": report.text,
            "total": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    import uvicorn
    import os
    # A Render automatikusan beállítja a PORT környezeti változót
    port = int(os.environ.get("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)