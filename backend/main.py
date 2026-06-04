from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from pydantic import BaseModel
import os
import csv
import io
from fpdf import FPDF

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

@app.get("/api/events/export/csv")
def export_events_csv(db: Session = Depends(get_db)):
    events = db.query(models.Event).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Date", "Budget", "Status", "Description"])
    
    for event in events:
        writer.writerow([event.id, event.title, event.date, event.budget, event.status, event.description])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=events_export.csv"}
    )

@app.get("/api/events/export/pdf")
def export_events_pdf(db: Session = Depends(get_db)):
    events = db.query(models.Event).all()
    
    pdf = FPDF()
    pdf.add_page()
    # Use 'helvetica' which is built-in to fpdf2 and avoids font issues
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "CyberX Activity Report", ln=True, align="C")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 10, f"Generated on: {date.today()}", ln=True, align="C")
    pdf.ln(10)
    
    # Table Header
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(30, 10, "Date", 1, 0, "C", True)
    pdf.cell(70, 10, "Title", 1, 0, "C", True)
    pdf.cell(30, 10, "Status", 1, 0, "C", True)
    pdf.cell(30, 10, "Budget", 1, 1, "C", True)
    
    # Table Content
    pdf.set_font("helvetica", "", 10)
    total_budget = 0
    for event in events:
        pdf.cell(30, 10, str(event.date), 1)
        pdf.cell(70, 10, event.title, 1)
        pdf.cell(30, 10, event.status, 1)
        pdf.cell(30, 10, f"${event.budget:,.2f}", 1, 1, "R")
        total_budget += event.budget
        
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"Total Planned Budget: ${total_budget:,.2f}", ln=True, align="R")
    
    return StreamingResponse(
        io.BytesIO(pdf.output()),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=events_report.pdf"}
    )

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
