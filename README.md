# CyberX Management System 🛡️

> A centralized command center for the CyberX college cybersecurity club — bringing event coordination, budget control, attendance tracking, and people management into one clean, real-time platform.

---

## What It Does

**Kanban Command Board** — Drag-and-drop task management across projects. Each project (event/workshop) gets its own swimlane with To-Do / In Progress / Done columns. Finished projects? Archive them with one click — they tuck away in a collapsible section, data intact.

**Live Attendance Tracking** — Pull up any event, see exactly who registered, check them in live, and watch the attendance percentage tick in real-time. Export a clean PDF report with full name/email/presence table and summary stats.

**Budget & Finance Ledger** — Log expenses with receipt uploads (image validation built in). Every budget revision is timestamped for an audit trail. Generate a full financial PDF report with expense breakdown, budget history, and embedded receipt images.

**People Directory** — Single source of truth for every member. Bulk import from Google Sheets (name, email, phone, student ID) — duplicates are detected and merged automatically. Filter by project, see attendance history per person, bulk delete.

---

## Key Technologies

| Layer | Stack |
|-------|-------|
| Backend | **FastAPI** (Python 3.12) |
| ORM | **SQLAlchemy** |
| Database | **SQLite** |
| Frontend | **Vanilla JS** + **Tailwind CSS** |
| PDF | **FPDF** |
| Icons | **Lucide** |
| Auth | N/A (club-internal deployment) |

---

## Quick Start

```bash
git clone https://github.com/itsdavidmandal/cyberx-management-system.git
cd cyberx-management-system
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

## Screenshots

_(Add your screenshots here)_

---

That description for LinkedIn:

> Built a full-stack event command center for my college's cybersecurity club — a live Kanban board with drag-and-drop task management, real-time attendance tracking with percentage counters, automated PDF financial reports with receipt embedding, bulk member import with smart duplicate detection, and one-click project archiving. Think Trello + a club treasurer in one dashboard.
>
> **Tech:** FastAPI, SQLAlchemy, SQLite, Vanilla JS, Tailwind CSS, FPDF.
>