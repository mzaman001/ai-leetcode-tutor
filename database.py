import sqlite3
import os

DB_PATH = "lessons.db"

def init_db():
    """Initializes the local SQLite database for storing lessons."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_lesson_to_db(lesson_text: str):
    """Saves a verified lesson to the local database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO lessons (lesson_text) VALUES (?)', (lesson_text,))
    conn.commit()
    conn.close()

def remove_lesson_from_db(lesson_text: str):
    """Removes a lesson (used for Undo)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM lessons WHERE lesson_text = ?', (lesson_text,))
    conn.commit()
    conn.close()

def get_lessons_context() -> str:
    """Retrieves up to 5 recent lessons from the local database."""
    if not os.path.exists(DB_PATH):
        init_db()
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT lesson_text FROM lessons ORDER BY created_at DESC LIMIT 5')
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return ""
    
    # Reverse to put oldest first among the 5 recent
    lessons = [row[0] for row in reversed(rows)]
    return "\n\nLESSONS FROM YOUR MEMORY (avoid repeating past mistakes):\n" + "\n".join(f"- {l}" for l in lessons)
