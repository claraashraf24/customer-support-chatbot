import sqlite3
import os
from datetime import datetime
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

DB_PATH = os.path.join(os.path.dirname(__file__), "../../chatbot_logs.db")


def init_db():
    """Create logs table if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user TEXT,                        -- 👈 NEW
            question TEXT,
            answer TEXT,
            confidence REAL,
            sources TEXT,
            escalated INTEGER,
            topic TEXT,
            response_time REAL,
            feedback INTEGER   -- 👍👎 feedback (1 = helpful, 0 = not helpful, NULL = not given)
        )
    """)
    conn.commit()
    conn.close()



def detect_topic(question, n_clusters=5):
    """Assign a topic cluster label to the new question."""
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT question FROM logs", conn)
    except Exception:
        df = pd.DataFrame(columns=["question"])
    finally:
        conn.close()

    questions = df["question"].dropna().tolist() + [question]

    if len(questions) == 0:
        return "Cluster-0"

    vectorizer = TfidfVectorizer(stop_words="english")
    X = vectorizer.fit_transform(questions)

    kmeans = KMeans(n_clusters=min(n_clusters, len(questions)), random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    return f"Cluster-{labels[-1]}"  # last label = current question


def log_interaction(user, question, answer, confidence, sources, escalated, response_time=None):
    """Insert a new chatbot interaction into the database with topic clustering."""
    topic = detect_topic(question)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs (timestamp, user, question, answer, confidence, sources, escalated, topic, response_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        user,   # 👈 store username
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



def update_feedback(log_id, feedback):
    """Update feedback (👍 or 👎) for a given log entry."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE logs SET feedback = ? WHERE id = ?",
        (feedback, log_id),
    )
    conn.commit()

    # Debug: check if any row was updated
    if cursor.rowcount == 0:
        print(f"⚠️ No row found with id={log_id}")
    else:
        print(f"✅ Updated feedback for log_id={log_id} → {feedback}")

    conn.close()
