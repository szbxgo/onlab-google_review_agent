# onlab-google_review_agent
Önálló Labor Projekt Megoldása

A projekt működéséhez elengedhetetlenek a következő szoftverek:

Ollama: A lokális LLM futtatásához szükséges keretrendszer.
Modellek: A fejlesztés során a Gemma 3:12b bizonyult a leghatékonyabbnak a magyar nyelvű válaszokhoz , de korábban tesztelve volt a DeepSeek-R1:8B és a Qwen3:8B is.
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


Session Status                online
Account                       szbxgo (Plan: Free)
Update                        update available (version 3.37.2, Ctrl-U to update)
Version                       3.36.1-msix-stable
Region                        Europe (eu)
Latency                       27ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://unshuttered-unsolaced-asia.ngrok-free.dev -> http://localhost:8501

Connections                   ttl     opn     rt1     rt5     p50     p90     
                              0       0       0.00    0.00    0.00    0.00   


