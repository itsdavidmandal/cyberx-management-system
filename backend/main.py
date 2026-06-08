from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date
from pydantic import BaseModel
import os
import csv
import io
import shutil
import uuid
from fpdf import FPDF

from . import models, database
from .database import engine, get_db

# Create tables
models.Base.metadata.create_all(bind=engine)

UPLOAD_DIR = "static/uploads/receipts"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Planning API")

# Pydantic Schemas
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: float = 0.0

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int

    class Config:
        from_attributes = True

class ExpenseBase(BaseModel):
    name: str
    amount: float
    date: date

class Expense(ExpenseBase):
    id: int
    receipt_path: Optional[str] = None
    project_id: int

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
    
    # Unassign all tasks from this project before deleting
    db.query(models.Task).filter(models.Task.project_id == project_id).update({models.Task.project_id: None})
    
    # Delete associated expenses and their files
    expenses = db.query(models.Expense).filter(models.Expense.project_id == project_id).all()
    for exp in expenses:
        if exp.receipt_path and os.path.exists(exp.receipt_path):
            os.remove(exp.receipt_path)
        db.delete(exp)
    
    db.delete(db_project)
    db.commit()
    return {"message": "Project deleted, tasks unassigned, and expenses cleared"}

# Expenses
@app.post("/api/projects/{project_id}/expenses/", response_model=Expense)
async def create_expense(
    project_id: int,
    name: str = Form(...),
    amount: float = Form(...),
    date: date = Form(...),
    receipt: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    receipt_path = None
    if receipt:
        file_ext = os.path.splitext(receipt.filename)[1]
        file_name = f"{uuid.uuid4()}{file_ext}"
        receipt_path = os.path.join(UPLOAD_DIR, file_name)
        with open(receipt_path, "wb") as buffer:
            shutil.copyfileobj(receipt.file, buffer)
    
    db_expense = models.Expense(
        name=name,
        amount=amount,
        date=date,
        receipt_path=receipt_path,
        project_id=project_id
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@app.get("/api/projects/{project_id}/expenses/", response_model=List[Expense])
def read_expenses(project_id: int, db: Session = Depends(get_db)):
    return db.query(models.Expense).filter(models.Expense.project_id == project_id).all()

@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    db_expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if db_expense.receipt_path and os.path.exists(db_expense.receipt_path):
        os.remove(db_expense.receipt_path)
        
    db.delete(db_expense)
    db.commit()
    return {"message": "Expense deleted"}

# Project Report Generation
@app.get("/api/projects/{project_id}/report")
def generate_project_report(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    expenses = db.query(models.Expense).filter(models.Expense.project_id == project_id).all()
    total_spent = sum(exp.amount for exp in expenses)
    
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("helvetica", "B", 24)
    pdf.set_text_color(28, 80, 112) # brand-dark
    pdf.cell(0, 20, f"Project Financial Report", ln=True, align="C")
    
    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(56, 56, 56) # brand-gray
    pdf.cell(0, 10, project.name, ln=True, align="C")
    
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 10, f"Timeline: {project.start_date or 'N/A'} to {project.end_date or 'N/A'}", ln=True, align="C")
    pdf.ln(10)
    
    # Financial Summary
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "  Financial Summary", 0, 1, "L", True)
    pdf.set_font("helvetica", "", 11)
    pdf.cell(90, 10, f"Total Budget: ${project.budget:,.2f}", 0, 0)
    pdf.cell(90, 10, f"Total Spent: ${total_spent:,.2f}", 0, 1)
    pdf.set_font("helvetica", "B", 11)
    remaining = project.budget - total_spent
    pdf.set_text_color(174, 0, 1) if remaining < 0 else pdf.set_text_color(0, 128, 0)
    pdf.cell(0, 10, f"Remaining Balance: ${remaining:,.2f}", 0, 1)
    pdf.set_text_color(56, 56, 56)
    pdf.ln(10)
    
    # Expense Table
    pdf.set_fill_color(28, 80, 112)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(100, 10, " Item Name", 1, 0, "L", True)
    pdf.cell(40, 10, " Date", 1, 0, "C", True)
    pdf.cell(50, 10, " Amount", 1, 1, "R", True)
    
    pdf.set_text_color(56, 56, 56)
    pdf.set_font("helvetica", "", 10)
    for exp in expenses:
        pdf.cell(100, 10, f" {exp.name}", 1)
        pdf.cell(40, 10, f" {exp.date}", 1, 0, "C")
        pdf.cell(50, 10, f"${exp.amount:,.2f} ", 1, 1, "R")
    
    # Receipts Gallery
    if any(exp.receipt_path for exp in expenses):
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 20, "Appendix: Receipt Proofs", ln=True, align="C")
        
        for exp in expenses:
            if exp.receipt_path and os.path.exists(exp.receipt_path):
                pdf.ln(10)
                pdf.set_font("helvetica", "B", 12)
                pdf.cell(0, 10, f"Receipt for: {exp.name} (${exp.amount:,.2f} on {exp.date})", ln=True)
                # Embed image - keep it within page bounds (roughly 190mm wide)
                try:
                    pdf.image(exp.receipt_path, x=10, w=180)
                except Exception as e:
                    pdf.set_font("helvetica", "I", 10)
                    pdf.cell(0, 10, f"[Image load failed: {str(e)}]", ln=True)
    
    return StreamingResponse(
        io.BytesIO(pdf.output()),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Project_Report_{project_id}.pdf"}
    )

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

@app.patch("/api/events/{task_id}/status")
def update_task_status(task_id: int, status: str, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Normalize status string
    status = status.strip().title()
    if status == "In Progress":
        status = "In Progress"
    
    db_task.status = status
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
