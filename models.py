from sqlalchemy import Column, Integer, String, ForeignKey, Text, Float, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    
    # --- GOOGLE BUSINESS PROFILE ADATOK ---
    # A refresh_token a legfontosabb, az access_token lejár 1 óra után
    google_refresh_token = Column(String, nullable=True)
    google_account_id = Column(String, nullable=True) # A Google belső azonosítója a céghez
    google_location_id = Column(String, nullable=True) # A konkrét üzlethelyiség azonosítója
    # ------------------------------        

    email = Column(String, unique=True, index=True)    
    style_guideline = Column(Text) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))

    # --- ÚJ MEZŐK A SZINKRONIZÁLÁSHOZ ---
    google_review_id = Column(String, unique=True) # Fontos: hogy ne mentsük el ugyanazt kétszer!
    author = Column(String)
    text = Column(Text, nullable=False)
    rating = Column(Integer)


    # Kezeljük, hogy válaszoltunk-e már rá
    is_replied = Column(Boolean, default=False)
    reply_text = Column(Text, nullable=True) # Az AI által generált vagy jóváhagyott válasz
    
    category = Column(String) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())