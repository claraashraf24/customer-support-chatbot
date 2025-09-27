import sqlite3, os

#  Put DB in shared /app/data volume
DB_PATH = os.getenv("DB_PATH", "/app/data/chatbot_logs.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user TEXT,
            question TEXT,
            answer TEXT,
            confidence REAL,
            sources TEXT,
            escalated INTEGER,
            topic TEXT,
            response_time REAL,
            feedback INTEGER
        )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print(f"✅ Database initialized at {DB_PATH}")
    init_db()
