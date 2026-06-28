from sqlalchemy import Column, Integer, String, Float, Date, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    budget = Column(Float, default=0.0)
    archived = Column(Boolean, default=False)

    tasks = relationship("Task", back_populates="project")
    expenses = relationship("Expense", back_populates="project")
    budget_logs = relationship("BudgetLog", back_populates="project")
    guests = relationship("Guest", back_populates="project", cascade="all, delete-orphan")
    attendees = relationship("Attendance", back_populates="project", cascade="all, delete-orphan")

class BudgetLog(Base):
    __tablename__ = "budget_logs"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    change_date = Column(DateTime, default=func.now())
    project_id = Column(Integer, ForeignKey("projects.id"))

    project = relationship("Project", back_populates="budget_logs")

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    amount = Column(Float)
    date = Column(Date)
    receipt_path = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"))

    project = relationship("Project", back_populates="expenses")

class Task(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    date = Column(Date)
    budget = Column(Float, default=0.0)
    status = Column(String, default="To-Do")
    completed = Column(Boolean, default=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    project = relationship("Project", back_populates="tasks")

class Idea(Base):
    __tablename__ = "ideas"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)

class Guest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    status = Column(String, default="Pending")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    project = relationship("Project", back_populates="guests")

class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    student_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    attendances = relationship("Attendance", back_populates="person", cascade="all, delete-orphan")

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    attended = Column(Boolean, default=False)
    registered_at = Column(DateTime, default=func.now())

    person = relationship("Person", back_populates="attendances")
    project = relationship("Project", back_populates="attendees")
