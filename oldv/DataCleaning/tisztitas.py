import pandas as pd
import re

def process_reviews(input_file, output_file):
    # 1. Beolvasás próbálkozás több kódolással
    try:
        # A legtöbb magyar CSV 'latin2' vagy 'cp1250' kódolású
        df = pd.read_csv(input_file, sep=';', encoding='latin2')
    except UnicodeDecodeError:
        # Ha a latin2 nem működik, próbáljuk meg a windows-1250-et
        df = pd.read_csv(input_file, sep=';', encoding='cp1250')
    except Exception as e:
        return f"Hiba a beolvasáskor: {e}"

    # 2. Segédfüggvény a név kinyeréséhez (levágja a 'X vélemény' részt)
    def extract_name(text):
        if pd.isna(text):
            return "Névtelen"
        # Megkeresi a szöveg elejét a "X vélemény" részig
        match = re.search(r'^(.*?)\s+\d+\s+vélemény', text)
        if match:
            return match.group(1).strip()
        return text.strip()

    # 3. Segédfüggvény az alapvető kategorizáláshoz kulcsszavak alapján
    def categorize_service(text):
        if pd.isna(text):
            return "Egyéb"
        text = text.lower()
        if any(word in text for word in ["fürdőszoba", "kád", "zuhany"]):
            return "Fürdőszoba felújítás"
        elif any(word in text for word in ["wc", "toalett"]):
            return "WC szerelés"
        elif "dugulás" in text:
            return "Duguláselhárítás"
        elif any(word in text for word in ["csap", "mosogató", "mosdó"]):
            return "Csap/Szerelvényezés"
        elif any(word in text for word in ["cső", "vezeték", "vízvezeték"]):
            return "Vízvezeték szerelés"
        else:
            return "Általános vízvezetékszerelés"

    # 4. Adatok átalakítása
    # Vásárló neve a 'd4r55' oszlopból
    df['Customer_Name'] = df['d4r55'].apply(extract_name)
    # Vélemény szövege a 'wiI7pd' oszlopból
    df['Review_Text'] = df['wiI7pd']
    # Kategória létrehozása a szövegből
    df['Service_Category'] = df['Review_Text'].apply(categorize_service)

    # 5. Csak a szükséges oszlopok megtartása
    cleaned_df = df[['Customer_Name', 'Review_Text', 'Service_Category']].copy()

    # Üres vélemények törlése
    cleaned_df = cleaned_df.dropna(subset=['Review_Text'])

    # 6. Mentés az új fájlba
    cleaned_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    return f"Kész! A tisztított adatok elmentve: {output_file}"

# Program futtatása
status = process_reviews('1.csv', 'cleaned_reviews.csv')
print(status)