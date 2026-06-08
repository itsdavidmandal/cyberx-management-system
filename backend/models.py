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

    tasks = relationship("Task", back_populates="project")
    expenses = relationship("Expense", back_populates="project")
    budget_logs = relationship("BudgetLog", back_populates="project")

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
