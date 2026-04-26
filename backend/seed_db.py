from database import SessionLocal
import models as models

def seed_data():
    db = SessionLocal()
    
    # Ellenőrizzük, létezik-e már
    existing_business = db.query(models.Business).filter(models.Business.email == "pelda@gmail.com").first()
    
    if not existing_business:
        new_business = models.Business(
            id=1, # Ez legyen 1, mert a Qdrant-ba is így töltöttük fel!
            name="Jóri István",
            email="pelda@gmail.com",
            style_guideline="Barátságos, tegező, szakmai és segítőkész stílus."
        )
        db.add(new_business)
        db.commit()
        print("✅ Jóri István sikeresen regisztrálva az adatbázisba!")
    else:
        print("ℹ️ Ez az email már regisztrálva van.")
    
    db.close()

if __name__ == "__main__":
    seed_data()