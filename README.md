# CyberX Activity Planner

A centralized event and activity management system designed for the **CyberX** college cybersecurity club. This platform helps club leads and members organize events, track budgets, and manage tasks efficiently.

## 🚀 Features
- **Event Dashboard:** At-a-glance view of all upcoming club activities.
- **Kanban Board:** Intuitive task management with "To-Do", "In Progress", and "Done" statuses.
- **Urgency Tracking:** Real-time countdowns for event deadlines.
- **Budget Management:** Keep track of financial resources for workshops and competitions.

## 🛠️ Tech Stack
- **Backend:** FastAPI (Python)
- **Database:** SQLite with SQLAlchemy ORM
- **Frontend:** Vanilla HTML/CSS/JS (Static Hosting)

## 🏁 Getting Started

### Prerequisites
- Python 3.12+
- Virtual environment (recommended)

### Installation
1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd cyberx-planner
   ```

2. **Set up the virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/bin/activate  # On Linux/macOS
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

### Running the App
From the root directory, run:
```bash
python3 -m uvicorn backend.main:app --reload
```

Then, open your browser and go to: `http://127.0.0.1:8000`

## 📂 Project Structure
- `backend/`: FastAPI application, models, and database configuration.
- `static/`: Frontend assets (HTML, CSS, JavaScript).
- `planning.db`: Persistent SQLite database (auto-generated).
