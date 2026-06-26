from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel
import os
import csv
import io
import shutil
import uuid
from fpdf import FPDF
from PIL import Image

from . import models, database
from .database import engine, get_db

# Create tables
models.Base.metadata.create_all(bind=engine)

UPLOAD_DIR = "uploads/receipts"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

def validate_receipt(file: UploadFile):
    # Check extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Extension {ext} not allowed.")
    
    # Check MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"MIME type {file.content_type} not allowed.")

    # Check file size
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5MB).")

    # Verify image integrity
    try:
        with Image.open(file.file) as img:
            img.verify()
        file.file.seek(0)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

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

class ProjectUpdate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int

    class Config:
        from_attributes = True

class BudgetLogBase(BaseModel):
    amount: float
    change_date: datetime

class BudgetLog(BudgetLogBase):
    id: int
    project_id: int

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

class IdeaBase(BaseModel):
    title: str
    description: Optional[str] = None

class IdeaCreate(IdeaBase):
    pass

class Idea(IdeaBase):
    id: int

    class Config:
        from_attributes = True

class GuestBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None
    status: str = "Pending"

class GuestCreate(GuestBase):
    project_id: Optional[int] = None

class Guest(GuestBase):
    id: int
    project_id: Optional[int] = None

    class Config:
        from_attributes = True

class PersonBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    student_id: Optional[str] = None

class PersonCreate(PersonBase):
    pass

class Person(PersonBase):
    id: int
    created_at: datetime
    project_count: int = 0
    attended_count: int = 0
    project_ids: List[int] = []

    class Config:
        from_attributes = True

class AttendanceBase(BaseModel):
    attended: bool = False

class AttendanceCreate(AttendanceBase):
    person_id: int
    project_id: int

class Attendance(AttendanceBase):
    id: int
    person_id: int
    project_id: int
    registered_at: datetime
    person_name: Optional[str] = None
    person_email: Optional[str] = None
    person_phone: Optional[str] = None
    person_student_id: Optional[str] = None

    class Config:
        from_attributes = True

class BulkImportRequest(BaseModel):
    text: str
    project_id: Optional[int] = None

class BulkAddToProjectRequest(BaseModel):
    person_ids: List[int]

# API Endpoints

# Projects
@app.post("/api/projects/", response_model=Project)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # Log initial budget
    if db_project.budget > 0:
        log = models.BudgetLog(amount=db_project.budget, project_id=db_project.id)
        db.add(log)
        db.commit()
        
    return db_project

@app.get("/api/projects/", response_model=List[Project])
def read_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()

@app.put("/api/projects/{project_id}", response_model=Project)
def update_project(project_id: int, project: ProjectUpdate, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = project.model_dump()
    
    # Log budget change if amount differs
    if update_data["budget"] != db_project.budget:
        log = models.BudgetLog(amount=update_data["budget"], project_id=project_id)
        db.add(log)
    
    for var, value in update_data.items():
        setattr(db_project, var, value)
    
    db.commit()
    db.refresh(db_project)
    return db_project

@app.get("/api/projects/{project_id}/budget-logs", response_model=List[BudgetLog])
def read_budget_logs(project_id: int, db: Session = Depends(get_db)):
    return db.query(models.BudgetLog).filter(models.BudgetLog.project_id == project_id).order_by(models.BudgetLog.change_date.desc()).all()

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Unassign all tasks from this project before deleting
    db.query(models.Task).filter(models.Task.project_id == project_id).update({models.Task.project_id: None})
    
    # Delete associated budget logs
    db.query(models.BudgetLog).filter(models.BudgetLog.project_id == project_id).delete()
    
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
        validate_receipt(receipt)
        file_ext = os.path.splitext(receipt.filename)[1].lower()
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

@app.get("/api/receipts/{filename}")
async def get_receipt(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Receipt not found")
    return FileResponse(file_path)

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
    pdf.ln(5)

    # Budget History
    logs = db.query(models.BudgetLog).filter(models.BudgetLog.project_id == project_id).order_by(models.BudgetLog.change_date.asc()).all()
    if logs:
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 10, "Budget Revision History:", ln=True)
        pdf.set_font("helvetica", "I", 9)
        for log in logs:
            pdf.cell(0, 8, f" - Set to ${log.amount:,.2f} on {log.change_date.strftime('%Y-%m-%d %H:%M')}", ln=True)
    
    pdf.ln(5)
    
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

# Ideas
@app.get("/api/ideas/", response_model=List[Idea])
def read_ideas(db: Session = Depends(get_db)):
    return db.query(models.Idea).all()

@app.post("/api/ideas/", response_model=Idea)
def create_idea(idea: IdeaCreate, db: Session = Depends(get_db)):
    db_idea = models.Idea(**idea.model_dump())
    db.add(db_idea)
    db.commit()
    db.refresh(db_idea)
    return db_idea

@app.put("/api/ideas/{idea_id}", response_model=Idea)
def update_idea(idea_id: int, idea: IdeaCreate, db: Session = Depends(get_db)):
    db_idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not db_idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    for var, value in idea.model_dump().items():
        setattr(db_idea, var, value)
    db.commit()
    db.refresh(db_idea)
    return db_idea

@app.delete("/api/ideas/{idea_id}")
def delete_idea(idea_id: int, db: Session = Depends(get_db)):
    db_idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not db_idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    db.delete(db_idea)
    db.commit()
    return {"ok": True}

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

# Guests
@app.get("/api/guests/", response_model=List[Guest])
def read_all_guests(db: Session = Depends(get_db)):
    return db.query(models.Guest).all()

@app.post("/api/guests/", response_model=Guest)
def create_guest(guest: GuestCreate, db: Session = Depends(get_db)):
    db_guest = models.Guest(**guest.model_dump())
    db.add(db_guest)
    db.commit()
    db.refresh(db_guest)
    return db_guest

@app.get("/api/projects/{project_id}/guests/", response_model=List[Guest])
def read_project_guests(project_id: int, db: Session = Depends(get_db)):
    return db.query(models.Guest).filter(models.Guest.project_id == project_id).all()

@app.put("/api/guests/{guest_id}", response_model=Guest)
def update_guest(guest_id: int, guest: GuestCreate, db: Session = Depends(get_db)):
    db_guest = db.query(models.Guest).filter(models.Guest.id == guest_id).first()
    if db_guest is None:
        raise HTTPException(status_code=404, detail="Guest not found")
    
    for var, value in guest.model_dump().items():
        setattr(db_guest, var, value)
    
    db.commit()
    db.refresh(db_guest)
    return db_guest

@app.delete("/api/guests/{guest_id}")
def delete_guest(guest_id: int, db: Session = Depends(get_db)):
    db_guest = db.query(models.Guest).filter(models.Guest.id == guest_id).first()
    if db_guest is None:
        raise HTTPException(status_code=404, detail="Guest not found")
    db.delete(db_guest)
    db.commit()
    return {"message": "Guest removed"}

# People
@app.get("/api/people/", response_model=List[Person])
def read_people(db: Session = Depends(get_db)):
    people = db.query(models.Person).order_by(models.Person.name).all()
    # Attach project count, attended count, and IDs for each person
    for p in people:
        p.project_count = len(p.attendances)
        p.attended_count = sum(1 for a in p.attendances if a.attended)
        p.project_ids = [a.project_id for a in p.attendances]
    return people

@app.post("/api/people/", response_model=Person)
def create_person(person: PersonCreate, db: Session = Depends(get_db)):
    # Check for existing person by email or student_id
    existing = None
    if person.email:
        existing = db.query(models.Person).filter(models.Person.email == person.email).first()
    if not existing and person.student_id:
        existing = db.query(models.Person).filter(models.Person.student_id == person.student_id).first()
    if existing:
        # Update fields if new values provided
        if person.name:
            existing.name = person.name
        if person.phone:
            existing.phone = person.phone
        if person.email and not existing.email:
            existing.email = person.email
        if person.student_id and not existing.student_id:
            existing.student_id = person.student_id
        db.commit()
        db.refresh(existing)
        existing.project_count = len(existing.attendances)
        existing.attended_count = sum(1 for a in existing.attendances if a.attended)
        existing.project_ids = [a.project_id for a in existing.attendances]
        return existing

    db_person = models.Person(**person.model_dump())
    db.add(db_person)
    db.commit()
    db.refresh(db_person)
    db_person.project_count = 0
    db_person.attended_count = 0
    db_person.project_ids = []
    return db_person

@app.put("/api/people/{person_id}", response_model=Person)
def update_person(person_id: int, person: PersonCreate, db: Session = Depends(get_db)):
    db_person = db.query(models.Person).filter(models.Person.id == person_id).first()
    if not db_person:
        raise HTTPException(status_code=404, detail="Person not found")
    for var, value in person.model_dump().items():
        setattr(db_person, var, value)
    db.commit()
    db.refresh(db_person)
    db_person.project_count = len(db_person.attendances)
    db_person.attended_count = sum(1 for a in db_person.attendances if a.attended)
    db_person.project_ids = [a.project_id for a in db_person.attendances]
    return db_person

@app.delete("/api/people/{person_id}")
def delete_person(person_id: int, db: Session = Depends(get_db)):
    db_person = db.query(models.Person).filter(models.Person.id == person_id).first()
    if not db_person:
        raise HTTPException(status_code=404, detail="Person not found")
    db.delete(db_person)
    db.commit()
    return {"message": "Person and associated attendance records removed"}

# Bulk Import People
def _parse_person_line(line: str):
    """Parse a single line from pasted text into (name, email, phone, student_id).
    Supports tab, comma, or space-delimited (with email detection) formats."""
    # Tab-delimited
    if "\t" in line:
        parts = [p.strip() for p in line.split("\t")]
    # Comma-delimited
    elif "," in line:
        parts = [p.strip() for p in line.split(",")]
    else:
        # Space-delimited: try to split by email detection
        tokens = line.strip().split()
        # Heuristic: if a token looks like an email, split around it
        email_token = None
        for i, tok in enumerate(tokens):
            if "@" in tok and "." in tok.split("@")[-1]:
                email_token = i
                break
        if email_token is not None:
            name = " ".join(tokens[:email_token])
            rest = tokens[email_token + 1:]
            parts = [name, tokens[email_token]] + rest
        else:
            parts = [line.strip()]

    name = parts[0] if parts else line.strip()
    email = parts[1] if len(parts) > 1 and parts[1] else None
    phone = parts[2] if len(parts) > 2 and parts[2] else None
    student_id = parts[3] if len(parts) > 3 and parts[3] else None
    return name, email, phone, student_id

@app.post("/api/people/bulk-import")
def bulk_import_people(data: BulkImportRequest, db: Session = Depends(get_db)):
    """Parse pasted text (one name per line, or CSV with name,email,phone,student_id)
    and create or update Person records. Optionally register them for a project.
    Duplicates are detected by email or student_id."""
    lines = [line.strip() for line in data.text.strip().split("\n") if line.strip()]
    created = []
    matched = 0
    skipped = 0

    for line in lines:
        name, email, phone, student_id = _parse_person_line(line)
        if not name:
            skipped += 1
            continue

        # Try to find existing person by email or student_id
        if email:
            existing = db.query(models.Person).filter(models.Person.email == email).first()
        if not existing and student_id:
            existing = db.query(models.Person).filter(models.Person.student_id == student_id).first()

        if existing:
            # Update fields if new values provided
            if name:
                existing.name = name
            if phone:
                existing.phone = phone
            if email and not existing.email:
                existing.email = email
            if student_id and not existing.student_id:
                existing.student_id = student_id
            person = existing
            matched += 1
        else:
            person = models.Person(
                name=name,
                email=email,
                phone=phone,
                student_id=student_id
            )
            db.add(person)
            db.flush()
            created.append({"id": person.id, "name": person.name})

        # If a project is specified, register attendance
        if data.project_id:
            project_exists = db.query(models.Project).filter(models.Project.id == data.project_id).first()
            if project_exists:
                # Check for duplicate attendance
                existing_att = db.query(models.Attendance).filter(
                    models.Attendance.person_id == person.id,
                    models.Attendance.project_id == data.project_id
                ).first()
                if not existing_att:
                    db_attendance = models.Attendance(
                        person_id=person.id,
                        project_id=data.project_id
                    )
                    db.add(db_attendance)

    db.commit()
    msg_parts = []
    if created:
        msg_parts.append(f"Imported {len(created)} new people")
    if matched:
        msg_parts.append(f"Updated {matched} existing people")
    if skipped:
        msg_parts.append(f"Skipped {skipped} empty lines")
    return {
        "message": ", ".join(msg_parts) if msg_parts else "No changes made",
        "count": len(created) + matched,
        "people": created
    }

# Attendance
@app.get("/api/projects/{project_id}/attendance/", response_model=List[Attendance])
def read_project_attendance(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    records = db.query(models.Attendance).filter(
        models.Attendance.project_id == project_id
    ).order_by(models.Attendance.registered_at.desc()).all()

    # Attach person details
    result = []
    for rec in records:
        attendance_data = {
            "id": rec.id,
            "person_id": rec.person_id,
            "project_id": rec.project_id,
            "attended": rec.attended,
            "registered_at": rec.registered_at,
            "person_name": rec.person.name if rec.person else None,
            "person_email": rec.person.email if rec.person else None,
            "person_phone": rec.person.phone if rec.person else None,
            "person_student_id": rec.person.student_id if rec.person else None,
        }
        result.append(attendance_data)

    return result

@app.post("/api/projects/{project_id}/attendance/")
def add_people_to_project(
    project_id: int,
    data: BulkAddToProjectRequest,
    db: Session = Depends(get_db)
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    added = []
    for person_id in data.person_ids:
        person = db.query(models.Person).filter(models.Person.id == person_id).first()
        if not person:
            continue

        # Check if already registered
        existing = db.query(models.Attendance).filter(
            models.Attendance.person_id == person_id,
            models.Attendance.project_id == project_id
        ).first()
        if existing:
            continue

        db_attendance = models.Attendance(person_id=person_id, project_id=project_id)
        db.add(db_attendance)
        added.append(person.name)

    db.commit()
    return {"message": f"Added {len(added)} people to project", "added": added}

@app.post("/api/projects/{project_id}/attendance/bulk")
def bulk_add_attendance(
    project_id: int,
    data: BulkImportRequest,
    db: Session = Depends(get_db)
):
    """Bulk import people from pasted text AND register them for this project in one call.
    Duplicates are detected by email or student_id — the person record is reused."""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    lines = [line.strip() for line in data.text.strip().split("\n") if line.strip()]
    added = 0
    already_registered = 0

    for line in lines:
        name, email, phone, student_id = _parse_person_line(line)
        if not name:
            continue

        # Try to find existing person by email or student_id
        existing = None
        if email:
            existing = db.query(models.Person).filter(models.Person.email == email).first()
        if not existing and student_id:
            existing = db.query(models.Person).filter(models.Person.student_id == student_id).first()

        if existing:
            # Update fields if new values provided
            if name:
                existing.name = name
            if phone:
                existing.phone = phone
            if email and not existing.email:
                existing.email = email
            if student_id and not existing.student_id:
                existing.student_id = student_id
            person = existing
        else:
            person = models.Person(
                name=name,
                email=email,
                phone=phone,
                student_id=student_id
            )
            db.add(person)
            db.flush()

        # Check for duplicate attendance
        existing_att = db.query(models.Attendance).filter(
            models.Attendance.person_id == person.id,
            models.Attendance.project_id == project_id
        ).first()
        if existing_att:
            already_registered += 1
            continue

        db_attendance = models.Attendance(person_id=person.id, project_id=project_id)
        db.add(db_attendance)
        added += 1

    db.commit()
    msg = f"Added {added} people to project attendance"
    if already_registered:
        msg += f", {already_registered} already registered"
    return {"message": msg, "count": added}

@app.put("/api/attendance/{attendance_id}")
def update_attendance(attendance_id: int, data: AttendanceBase, db: Session = Depends(get_db)):
    db_attendance = db.query(models.Attendance).filter(models.Attendance.id == attendance_id).first()
    if not db_attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    db_attendance.attended = data.attended
    db.commit()
    db.refresh(db_attendance)
    return {
        "id": db_attendance.id,
        "attended": db_attendance.attended,
        "person_name": db_attendance.person.name if db_attendance.person else None
    }

@app.delete("/api/attendance/{attendance_id}")
def delete_attendance(attendance_id: int, db: Session = Depends(get_db)):
    db_attendance = db.query(models.Attendance).filter(models.Attendance.id == attendance_id).first()
    if not db_attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    db.delete(db_attendance)
    db.commit()
    return {"message": "Person removed from project attendance"}

# Serve Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")
