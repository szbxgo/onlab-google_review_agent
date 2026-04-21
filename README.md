# onlab-google_review_agent
Önálló Labor Projekt Megoldás

Review Agent – AI-alapú Véleménykezelő Rendszer 

Software as a Service

Rövid leírás: 
Ez a projekt egy automatizált, RAG (Retrieval-Augmented Generation) alapú megoldás Google Business vélemények professzionális megválaszolására és elemzésére.
A rendszer képes tanulni a korábbi válaszok stílusából, és egyedi hangnemben generálni releváns reakciókat.

Fejlődési Mérföldkövek: 
A projekt egy lokális Python scriptként indult, és mára egy modern, skálázható SaaS architektúrává fejlődött:

- MVP fázis: Ollama + Gemma 3:12b lokális futtatás, Streamlit UI.
- Prototípus: Qdrant Cloud integráció és ngrok alagút a távoli eléréshez.
- SaaS Refaktor: Átállás FastAPI backendre, Tailwind CSS frontendre és Google Gemini 1.5 Flash API-ra.

Technológiai Stack:

- AI és AdatkezelésLLM: Google Gemini 1.5 Flash (felhő alapú) – a gyorsabb válaszidő és alacsonyabb hardverigény érdekében. (Korábban: Gemma 3:12b lokálisan ).
- Vektor Adatbázis: Qdrant Cloud (ReviewAgent Free Cluster).
- Embedding: sentence-transformers (all-MiniLM-L6-v2) – 384 dimenziós vektorok előállításához.
- Adattárolás: PostgreSQL (Multi-tenant struktúra: Users, Businesses, Reviews táblák).

Backend & Frontend
- Keretrendszer: FastAPI (Python 3.12).
- Frontend: HTML5 & Tailwind CSS (Reszponzív Dashboard és Analytics modul Chart.js-szel).
- Hosting: GitHub Pages (Frontend)  + Render/Railway (Backend előkészítés).

Multi-tenant Architektúra
A rendszer támogatja több különböző vállalkozás egyidejű kiszolgálását:
- Payload Filtering: A Qdrant keresés során a rendszer user_id alapján szűri a vektorokat, így az AI csak az adott ügyfél releváns múltbéli adatait látja.
- Dinamikus Promptok: Minden vállalkozás saját stílusirányelvet (Style Guideline) állíthat be, amit a rendszer válaszgeneráláskor figyelembe vesz.
- Google Business API: Automatikus szinkronizáció a manuális CSV feltöltés helyett.

Telepítés és Futtatás (Fejlesztői mód)

Követelmények telepítése:
pip install pandas langchain-community qdrant-client sentence-transformers fastapi uvicorn google-generativeai

Lokális Streamlit Dashboard (Legacy mód):
streamlit run app.py --server.enableCORS=false --server.enableXsrfProtection=false

Elérhetőségek:

Weboldal: review-agent.agency 
Kapcsolat: info@review-agent.agency
Qdrant Konzolon: ReviewAgent Cluster


A projekt működéséhez elengedhetetlenek a következő szoftverek:
Ollama: A lokális LLM futtatásához szükséges keretrendszer.
Modellek: A fejlesztés során a Gemma 3:12b bizonyult a leghatékonyabbnak a magyar nyelvű válaszokhoz , de korábban tesztelve volt a DeepSeek-R1:8B és a Qwen3:8B is. Később Gemini 
Python könyvtárak: A terminálban a következő csomagok telepítése szükséges:
- pandas: Az adatok tisztításához és kezeléséhez.
- langchain_ollama / langchain_community: Az LLM és a kód összekapcsolásához.
- ollama: A Python-alapú modellhívásokhoz.
- sentence-transformers: A szöveges vélemények 384 dimenziós vektorokká alakításához (all-MiniLM-L6-v2 modell).
- qdrant-client: A felhő alapú vektoradatbázishoz való csatlakozáshoz.
- pip install streamlit: Streamlit telepítése a gépemre.
VS Code: A fejlesztéshez használt kódszerkesztő környezet.
Python: A projekt 3.12-es Python verziót használ.
Qdrant Cloud: Futó Free Cluster ReviewAgent néven a vektorok tárolásához.

Qdrant Cloud website: https://cloud.qdrant.io/accounts/ec856db9-3436-42e9-b33d-6e70cb006096/clusters/8b1ea742-86f3-4e19-a534-329ee60572d7/overview
website: https://review-agent.agency/
mail: 	info@review-agent.agency
domain kezelő oldal: https://ap.www.namecheap.com/dashboard
ngronk authtoken: 3B85p0ZYDXasR99E2ILRaM3Fidt_2kLEVwNyyrMi7ewEJiim
streamlit run app.py --server.enableCORS=false --server.enableXsrfProtection=false

