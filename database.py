import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Connects to the local PostgreSQL database defined in docker-compose
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://routine_user:routine_password@127.0.0.1/routine_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get a database session in our FastAPI routes later
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()