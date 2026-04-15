import pandas as pd
from langchain_ollama import OllamaLLM

# 1. A tisztított adatok beolvasása
df = pd.read_csv('cleaned_reviews.csv')

# 2. Az első 20 vélemény összefűzése egy blokkba (hogy beleférjen a kontextusba)
# A 'Review_Text' oszlopot használjuk, amit az előző lépésben hoztunk létre
context_text = "\n".join(df['Review_Text'].astype(str).head(20).tolist())

# 3. Ollama beállítása (Gemma 3:12b használatával)
# Győződj meg róla, hogy az Ollama fut a háttérben!
llm = OllamaLLM(model="gemma3:12b")

# 4. A feladat meghatározása (Prompt)
prompt = f"""
Te egy profi üzleti elemző vagy. Elemezd az alábbi vízvezeték-szerelői véleményeket:
---
{context_text}
---

Kérlek, készíts egy rövid jelentést az alábbiak szerint:
1. Mi az a 3 legfőbb pozitívum, amit az ügyfelek kiemelnek? (pl. pontosság, tisztaság)
2. Melyik szolgáltatást dicsérik a legtöbbször?
3. Milyen az általános hangulat (Sentiment)?
4. Írj egy 1 mondatos "Marketing szlogent", amit a vélemények alapján a weboldalra tehetnénk.

Magyarul válaszolj, tömör pontokba szedve.
"""

print("Az AI (Gemma 3:12b) éppen elemzi a véleményeket... Kérlek várj.")

try:
    response = llm.invoke(prompt)
    print("\n" + "="*40)
    print("AI ÜZLETI JELENTÉS")
    print("="*40)
    print(response)
    
    # Elmentjük az eredményt egy szöveges fájlba is
    with open('business_report.txt', 'w', encoding='utf-8') as f:
        f.write(response)
    print("\nJelentés elmentve: business_report.txt")

except Exception as e:
    print(f"Hiba történt az elemzés során: {e}")