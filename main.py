from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
from datetime import date
import os

app = FastAPI()

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
def init_db():
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS habits (id INTEGER PRIMARY KEY, title TEXT, is_active BOOLEAN)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS habit_logs (id INTEGER PRIMARY KEY, habit_id INTEGER, log_date TEXT, status BOOLEAN)''')
    conn.commit()
    conn.close()

init_db()

class HabitCreate(BaseModel):
    title: str

# --- API Endpoints ---

@app.post("/api/habits")
def create_habit(habit: HabitCreate):
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO habits (title, is_active) VALUES (?, ?)", (habit.title, True))
    conn.commit()
    conn.close()
    return {"message": "Habit created"}

@app.get("/api/today")
def get_today_logs():
    today = str(date.today())
    conn = sqlite3.connect("habits.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Check if logs exist for today. If not, create them.
    cursor.execute("SELECT * FROM habit_logs WHERE log_date = ?", (today,))
    if not cursor.fetchall():
        cursor.execute("SELECT id FROM habits WHERE is_active = 1")
        active_habits = cursor.fetchall()
        for h in active_habits:
            cursor.execute("INSERT INTO habit_logs (habit_id, log_date, status) VALUES (?, ?, ?)", (h['id'], today, False))
        conn.commit()

    # 2. Fetch and return today's to-do list
    cursor.execute('''
        SELECT habit_logs.id as log_id, habits.title, habit_logs.status 
        FROM habit_logs 
        JOIN habits ON habit_logs.habit_id = habits.id 
        WHERE habit_logs.log_date = ?
    ''', (today,))
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs

@app.put("/api/toggle/{log_id}")
def toggle_log(log_id: int):
    conn = sqlite3.connect("habits.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE habit_logs SET status = NOT status WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    return {"message": "Status updated"}

# --- Serve Frontend Files ---

# Mount the frontend folder to serve static assets (like sw.js and manifest.json)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Serve the main HTML file when someone visits the root URL
@app.get("/")
def serve_home():
    return FileResponse("frontend/index.html")