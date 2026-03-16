from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
import datetime

Base = declarative_base()

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    info = Column(Text, nullable=True)
    location = Column(String, nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True) # Normalized start datetime
    time = Column(String, nullable=True) # E.g., '19:00' or 'Doors 18:30'
    ticket_prices = Column(String, nullable=True) # Normalized string e.g., '€15 - €30'
    student_discounts_eligible = Column(Boolean, default=False)
    link = Column(String, nullable=False, unique=True) # URL of the event
    scraped_at = Column(DateTime, default=datetime.datetime.utcnow)

class TargetURL(Base):
    __tablename__ = "target_urls"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    active = Column(Boolean, default=True)

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    default_location = Column(String, nullable=False, default="Berlin")
    # For a simple setup, storing config as JSON might be an alternative,
    # but since target_urls has its own table, we just store global scalar settings here.

# Example synchronous engine setup for simplicity, can be updated to async
# engine = create_engine("sqlite:///./events.db", connect_args={"check_same_thread": False})
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base.metadata.create_all(bind=engine)
