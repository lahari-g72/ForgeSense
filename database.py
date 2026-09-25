import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Make sure it didn't fail to load
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing. Check your .env file!")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  
    pool_recycle=300,    
    max_overflow=10      
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()