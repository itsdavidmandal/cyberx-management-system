from sqlalchemy import Column, Integer, String, Float, Date, Text
from .database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    date = Column(Date)
    budget = Column(Float, default=0.0)
    status = Column(String, default="To-Do")
