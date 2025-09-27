import sqlite3
import os
from datetime import datetime
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

#  Always use the shared Docker volume DB
DB_PATH = os.getenv("DB_PATH", "/app/chatbot_logs/chatbot_logs.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def init_db() -> None:
    """Create logs table if it does not exist."""
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


def detect_topic(question: str, n_clusters: int = 5) -> str:
    """Assign a topic cluster label to the new question."""
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT question FROM logs", conn)
    except Exception:
        df = pd.DataFrame(columns=["question"])
    finally:
        conn.close()

    questions = df["question"].dropna().tolist() + [question]

    if not questions:
        return "Cluster-0"

    vectorizer = TfidfVectorizer(stop_words="english")
    X = vectorizer.fit_transform(questions)

    kmeans = KMeans(
        n_clusters=min(n_clusters, len(questions)),
        random_state=42,
        n_init=10
    )
    labels = kmeans.fit_predict(X)

    return f"Cluster-{labels[-1]}"


def log_interaction(
    user: str,
    question: str,
    answer: str,
    confidence: float,
    sources: list,
    escalated: bool,
    response_time: float = None
) -> int:
    """Insert a new chatbot interaction into the database with topic clustering."""
    init_db()  #  Ensure table exists before inserting
    topic = detect_topic(question)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs (timestamp, user, question, answer, confidence, sources, escalated, topic, response_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        user,
        question,
        answer,
        confidence if confidence is not None else None,
        ", ".join(sources) if sources else "",
        1 if escalated else 0,
        topic,
        response_time
    ))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id


def update_feedback(log_id: int, feedback: int) -> bool:
    """Update feedback for a given log entry. Returns True if updated."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE logs SET feedback = ? WHERE id = ?",
        (feedback, log_id),
    )
    updated = cursor.rowcount
    conn.commit()
    conn.close()
    return updated > 0
