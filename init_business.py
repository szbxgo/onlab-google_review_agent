import os
from database import SessionLocal
import models

db = SessionLocal()
# Ellenőrizzük, van-e már ilyen
if not db.query(models.Business).filter(models.Business.id == 1).first():
    uj_ceg = models.Business(
        id=1,
        name="Jóri István",
        email="istvan@pelda.hu", 
        style_guideline="Barátságos, tegező, szakmai de közérthető."
    )
    db.add(uj_ceg)
    db.commit()
    print("Jóri István üzleti profilja létrehozva!")
db.close()