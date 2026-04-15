import torch
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from langchain_ollama import OllamaLLM

# 1. Beállítások - Használd a saját adataidat!
URL = "https://8b1ea742-86f3-4e19-a534-329ee60572d7.eu-central-1-0.aws.cloud.qdrant.io"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.-0df-CLPC0u4MOKoOAS8aGb7MZpb8zkCYCfDW-zM0Mw"
COLLECTION_NAME = "first_reviews"

# 2. Inicializálás
print("Rendszer indítása...")
client = QdrantClient(url=URL, api_key=API_KEY)
embed_model = SentenceTransformer('all-MiniLM-L6-v2')
llm = OllamaLLM(model="gemma3:12b")

def get_answer(new_review):
    print(f"\nÚj vélemény érkezett: '{new_review}'")
    
    # A. Vektorizálás
    query_vector = embed_model.encode(new_review).tolist()
    
    # B. Keresés a Qdrant-ban - Próbáljuk a modernebb query_points-al vagy a search-el
    try:
        # Próbáljuk meg a legfrissebb metódust
        search_result = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=2
        ).points
    except AttributeError:
        # Ha a te verziód még a search_points-ot használja
        search_result = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=2
        )
    
    # C. Kontextus összeállítása
    context = ""
    for res in search_result:
        # Fontos: query_points esetén res.payload, search esetén res.payload
        context += f"\n- Korábbi vélemény: {res.payload.get('review', 'Nincs szöveg')}\n"
    
    # D. Prompt küldése a Gemmának
    prompt = f"""
    Te Jóri István vízvezeték-szerelő AI asszisztense vagy. 
    A feladatod, hogy udvarias, szakmai választ írj az új ügyfél véleményére.
    
    HASZNÁLD EZT A KONTEXTUST (hasonló korábbi esetek):
    {context}
    
    ÚJ VÉLEMÉNY, AMIRE VÁLASZOLNOD KELL:
    "{new_review}"
    
    A válaszod legyen barátságos, tegeződj (vagy magázódj, ha a stílus megköveteli), 
    és köszönd meg az értékelést István nevében. Magyarul válaszolj!
    """
    
    print("AI válasz generálása...")
    response = llm.invoke(prompt)
    return response

# TESZT: Próbáljuk ki egy új szituációval!
new_input = input("\nÍrj be egy teszt véleményt (pl. Nagyon gyorsan kijöttél megjavítani a csapot): ")
valasz = get_answer(new_input)

print("\n" + "="*50)
print("ISTVÁN AI VÁLASZA:")
print("="*50)
print(valasz)