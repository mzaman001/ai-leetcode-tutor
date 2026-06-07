import sqlite3
import os
import streamlit as st
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lessons.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initializes the local SQLite database for storing lessons."""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_text TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def save_lesson_to_db(lesson_text: str) -> int:
    """Saves a verified lesson to the local database and returns its ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO lessons (lesson_text) VALUES (?)', (lesson_text,))
        conn.commit()
        cursor.execute('SELECT id FROM lessons WHERE lesson_text = ?', (lesson_text,))
        row = cursor.fetchone()
        return row[0] if row else -1

def remove_lesson_from_db(lesson_id: int):
    """Removes a lesson by its primary key ID."""
    with get_db() as conn:
        conn.execute('DELETE FROM lessons WHERE id = ?', (lesson_id,))
        conn.commit()

@st.cache_data(ttl=30)
def get_lessons_context() -> str:
    """Retrieves up to 5 recent lessons from the local database."""
    if not os.path.exists(DB_PATH):
        init_db()
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT lesson_text FROM lessons ORDER BY created_at DESC LIMIT 5')
        rows = cursor.fetchall()
    
    if not rows:
        return ""
    
    # Reverse to put oldest first among the 5 recent
    lessons = [row[0] for row in reversed(rows)]
    return "\n\nLESSONS FROM YOUR MEMORY (avoid repeating past mistakes):\n" + "\n".join(f"- {l}" for l in lessons)
