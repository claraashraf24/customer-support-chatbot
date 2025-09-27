import sqlite3
import pandas as pd
from backend.services.logging_service import init_db

DB_PATH = "chatbot_logs.db"

# Ensure table exists
init_db()

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM logs ORDER BY id DESC LIMIT 10;", conn)
conn.close()

print(df)
