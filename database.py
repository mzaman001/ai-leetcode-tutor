import sqlite3
import os
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
                lesson_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def save_lesson_to_db(lesson_text: str):
    """Saves a verified lesson to the local database."""
    with get_db() as conn:
        conn.execute('INSERT INTO lessons (lesson_text) VALUES (?)', (lesson_text,))
        conn.commit()

def remove_lesson_from_db(lesson_text: str):
    """Removes a lesson (used for Undo)."""
    with get_db() as conn:
        conn.execute('DELETE FROM lessons WHERE lesson_text = ?', (lesson_text,))
        conn.commit()

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
