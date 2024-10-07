import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Boolean, DateTime

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



class Availability(Base):
    __tablename__ = "availabilities"

    id = Column(Integer, primary_key=True, index=True)
    date_slot = Column(String, index=True)
    specialization = Column(String, index=True)
    specialist_name = Column(String, index=True)
    is_available = Column(Boolean, default=True)
    client_to_attend = Column(Integer, nullable=True)
    event_id = Column(String, nullable=True)