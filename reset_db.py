from database import engine
import models

print("Táblák törlése...")
models.Base.metadata.drop_all(bind=engine)
print("Táblák újralétrehozása az új oszlopokkal...")
models.Base.metadata.create_all(bind=engine)
print("Kész!")