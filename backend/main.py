from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from pydantic import BaseModel
import os

from . import models, database
from .database import engine, get_db

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Planning API")

# Pydantic Schemas
class EventBase(BaseModel):
    title: str
    description: str = None
    date: date
    budget: float = 0.0
    status: str = "To-Do"

class EventCreate(EventBase):
    pass

class Event(EventBase):
    id: int

    class Config:
        from_attributes = True

# API Endpoints
@app.post("/api/events/", response_model=Event)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    db_event = models.Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@app.get("/api/events/", response_model=List[Event])
def read_events(db: Session = Depends(get_db)):
    return db.query(models.Event).all()

@app.put("/api/events/{event_id}", response_model=Event)
def update_event(event_id: int, event: EventCreate, db: Session = Depends(get_db)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    
    for var, value in event.model_dump().items():
        setattr(db_event, var, value)
    
    db.commit()
    db.refresh(db_event)
    return db_event

@app.delete("/api/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(db_event)
    db.commit()
    return {"message": "Event deleted"}

# Serve Static Files
# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")
