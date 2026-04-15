import streamlit as st
import pandas as pd
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from google import genai # Új, hivatalos Google SDK

# 1. Konfiguráció és Qdrant Kulcsok
URL = "https://8b1ea742-86f3-4e19-a534-329ee60572d7.eu-central-1-0.aws.cloud.qdrant.io"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.-0df-CLPC0u4MOKoOAS8aGb7MZpb8zkCYCfDW-zM0Mw"
COLLECTION_NAME = "first_reviews"
# A modell pontos neve az új rendszerben
GEMINI_MODEL_ID = "gemini-2.5-flash"

# UI Elrendezés
st.title("Review Agent - Dashboard")
st.subheader("AI alapú válaszgenerátor (Gemini Powered)")

# Modell betöltése (st.cache_resource)
@st.cache_resource
def load_models():
    client = QdrantClient(url=URL, api_key=API_KEY)
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    # Az új kliens inicializálása a titkosított kulccsal
    gemini_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    return client, embed_model, gemini_client

client, embed_model, gemini_client = load_models()

# Bemeneti mező az új véleménynek
new_review = st.text_area("Írd be az új ügyfél véleményét:", placeholder="Pl.: Nagyon gyorsan kijöttél megjavítani a csapot, köszi!")

if st.button("Válasz generálása"):
    if new_review:
        with st.spinner("A Gemini AI éppen gondolkozik a válaszon..."):
            try:
                # A. Vektorizálás és Keresés a Qdrantban
                query_vector = embed_model.encode(new_review).tolist()
                search_result = client.search(collection_name=COLLECTION_NAME, query_vector=query_vector, limit=2)
                
                # B. Kontextus építése
                context = ""
                for res in search_result:
                    context += f"\n- Korábbi vélemény: {res.payload.get('review', 'Nincs szöveg')}\n"
                
                # C. Prompt és Generálás (ÚJ Gemini API hívás)
                prompt = f"Te Jóri István AI asszisztense vagy. Kontextus:\n{context}\nÚj vélemény: {new_review}"
                response = gemini_client.models.generate_content(
                    model=GEMINI_MODEL_ID,
                    contents=prompt,
                )
                
                # D. Megjelenítés szerkeszthető formában
                st.success("Elkészült a javaslat!")
                final_answer = st.text_area("Szerkeszd vagy hagyd jóvá a választ:", value=response.text, height=200)
                
                if st.button("Jóváhagyás és Küldés"):
                    st.info("A válasz készen áll a kiküldésre a Google-re!")
            
            except Exception as e:
                st.error(f"Hiba történt a generálás során: {e}")
    else:
        st.warning("Kérlek, írj be egy véleményt!")

st.divider() # Vizuális elválasztó
st.header("Üzleti Jelentés & Elemzés")

if st.button("Friss riport generálása"):
    with st.spinner("A Gemini AI éppen elemzi az összes véleményt..."):
        try:
            # 1. Adatok betöltése
            df = pd.read_csv('cleaned_reviews.csv')
            all_reviews = "\n".join(df['Review_Text'].astype(str).head(20).tolist())
            
            # 2. Elemző prompt
            analysis_prompt = f"""
            Elemezd az alábbi véleményeket:
            {all_reviews}
            Készíts riportot: 3 legfőbb pozitívum, általános hangulat (Sentiment), 
            és egy marketing szlogen. Magyarul válaszolj!
            """
            
            # 3. ÚJ Gemini hívás
            report_response = gemini_client.models.generate_content(
                model=GEMINI_MODEL_ID,
                contents=analysis_prompt,
            )
            report = report_response.text
            
            # 4. Megjelenítés oszlopokban
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Összes vélemény", len(df))
                st.metric("Adatforrás", "Google Maps")
            with col2:
                st.info("AI Marketing Tipp:")
                st.write(report)
                
        except FileNotFoundError:
            st.error("Nem találom a 'cleaned_reviews.csv' fájlt. Győződj meg róla, hogy a mappában van!")
        except Exception as e:
            st.error(f"Hiba történt az elemzés során: {e}")