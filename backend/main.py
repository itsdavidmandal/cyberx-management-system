from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
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
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int

    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    date: date
    budget: float = 0.0
    status: str = "To-Do"
    completed: bool = False
    project_id: Optional[int] = None

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int

    class Config:
        from_attributes = True

# API Endpoints

# Projects
@app.post("/api/projects/", response_model=Project)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@app.get("/api/projects/", response_model=List[Project])
def read_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(db_project)
    db.commit()
    return {"message": "Project deleted"}

# Tasks (Mapped to /api/events/ for frontend compatibility)
@app.post("/api/events/", response_model=Task)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    data = task.model_dump()
    if "status" in data and data["status"]:
        data["status"] = data["status"].strip().title()
    db_task = models.Task(**data)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/api/events/", response_model=List[Task])
def read_tasks(db: Session = Depends(get_db)):
    return db.query(models.Task).all()

@app.get("/api/events/export/csv")
def export_tasks_csv(db: Session = Depends(get_db)):
    tasks = db.query(models.Task).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Date", "Budget", "Status", "Completed", "Description"])
    
    for task in tasks:
        writer.writerow([task.id, task.title, task.date, task.budget, task.status, task.completed, task.description])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tasks_export.csv"}
    )

@app.get("/api/events/export/pdf")
def export_tasks_pdf(db: Session = Depends(get_db)):
    tasks = db.query(models.Task).all()
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "CyberX Activity Report", ln=True, align="C")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 10, f"Generated on: {date.today()}", ln=True, align="C")
    pdf.ln(10)
    
    # Table Header
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(25, 10, "Date", 1, 0, "C", True)
    pdf.cell(65, 10, "Title", 1, 0, "C", True)
    pdf.cell(25, 10, "Status", 1, 0, "C", True)
    pdf.cell(25, 10, "Done", 1, 0, "C", True)
    pdf.cell(30, 10, "Budget", 1, 1, "C", True)
    
    # Table Content
    pdf.set_font("helvetica", "", 10)
    total_budget = 0
    for task in tasks:
        pdf.cell(25, 10, str(task.date), 1)
        pdf.cell(65, 10, task.title, 1)
        pdf.cell(25, 10, task.status, 1)
        pdf.cell(25, 10, "Yes" if task.completed else "No", 1, 0, "C")
        pdf.cell(30, 10, f"${task.budget:,.2f}", 1, 1, "R")
        total_budget += task.budget
        
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"Total Planned Budget: ${total_budget:,.2f}", ln=True, align="R")
    
    return StreamingResponse(
        io.BytesIO(pdf.output()),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=tasks_report.pdf"}
    )

@app.put("/api/events/{task_id}", response_model=Task)
def update_task(task_id: int, task: TaskCreate, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    for var, value in task.model_dump().items():
        setattr(db_task, var, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task

@app.patch("/api/events/{task_id}/toggle")
def toggle_task_completion(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db_task.completed = not db_task.completed
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/api/events/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()
    return {"message": "Task deleted"}

# Serve Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")
