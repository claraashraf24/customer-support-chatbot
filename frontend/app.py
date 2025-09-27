import streamlit as st
import requests
import sqlite3
import pandas as pd
import time
import streamlit.components.v1 as components
import datetime
import os
import matplotlib.pyplot as plt
import seaborn as sns


# -------------------
# Global Config
# -------------------
st.set_page_config(page_title="Docs-Aware Chatbot", page_icon="🤖", layout="wide")

#  Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
DB_PATH = os.getenv("DB_PATH", "/app/chatbot_logs/chatbot_logs.db")


#  Local init_db for frontend
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

# -------------------
# Custom Styling
# -------------------
def load_custom_css(theme="Light"):
    if theme == "Dark":
        bg = "#121212"
        text = "#f0f0f0"
        accent = "#1DB954"
        bubble_user = "#2E86C1"
        bubble_bot = "#2C3E50"
    else:
        bg = "#f8f9fa"
        text = "#222"
        accent = "#4CAF50"
        bubble_user = "#0078D7"
        bubble_bot = "#E5E5E5"

    css = f"""
    <style>
    body {{
        background-color: {bg};
        color: {text};
        font-family: 'Segoe UI', sans-serif;
    }}
    .stButton button {{
        background: {accent};
        color: white;
        border-radius: 8px;
        padding: 0.5em 1em;
        border: none;
    }}
    .chat-bubble-user {{
        background: {bubble_user};
        color: white;
        padding: 10px 14px;
        border-radius: 15px;
        margin: 5px;
        text-align: right;
    }}
    .chat-bubble-bot {{
        background: {bubble_bot};
        color: {text};
        padding: 10px 14px;
        border-radius: 15px;
        margin: 5px;
        text-align: left;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# -------------------
# Authentication
# -------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["username"] = None

if not st.session_state["authenticated"]:
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    users = {"admin": "admin123", "clara": "pass123", "demo": "demo123"}

    if st.button("Login"):
        if username in users and users[username] == password:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.success(f"✅ Welcome, {username}!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")
    st.stop()


# -------------------
# Sidebar & Theme
# -------------------
st.sidebar.image("https://streamlit.io/images/brand/streamlit-mark-color.png", width=100)
st.sidebar.title("📚 Docs-Aware Chatbot")
st.sidebar.caption("AI-powered document Q&A + analytics dashboard.")

theme = st.sidebar.radio("🎨 Theme", ["Light", "Dark"])
load_custom_css(theme)

page = st.sidebar.radio("Go to", ["Chatbot", "Analytics Dashboard"])


# -------------------------
#  Chatbot Page
# -------------------------
if page == "Chatbot":
    st.title("💬 Docs-Aware Chatbot")

    # Sidebar uploads
    st.sidebar.header("📂 Manage Documents")
    uploaded_file = st.sidebar.file_uploader("Upload a file", type=["pdf", "docx", "txt"])
    upload_mode = st.sidebar.radio("Upload mode", ["Single (replace)", "Append (multi-file)"])

    if uploaded_file:
        with st.spinner("Uploading and indexing..."):
            endpoint = f"{BACKEND_URL}/upload/single" if upload_mode == "Single (replace)" else f"{BACKEND_URL}/upload/append"
            response = requests.post(endpoint, files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)})
            if response.status_code == 200:
                st.sidebar.success("✅ File uploaded & indexed")
            else:
                st.sidebar.error("❌ Upload failed")

    if st.sidebar.button("🔄 Re-index All Documents"):
        response = requests.post(f"{BACKEND_URL}/upload/reindex")
        st.sidebar.success("✅ Reindexed") if response.status_code == 200 else st.sidebar.error("❌ Failed")

    # Show files
    try:
        response = requests.get(f"{BACKEND_URL}/upload/list")
        files = response.json().get("indexed_files", [])
        if files:
            st.sidebar.subheader("📑 Indexed Files")
            for f in files:
                st.sidebar.markdown(f"- {f}")
    except:
        st.sidebar.warning("⚠️ Backend not reachable")

    # Chat interface
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            st.markdown(f"<div class='chat-bubble-user'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-bubble-bot'>{msg['content']}</div>", unsafe_allow_html=True)

    if prompt := st.chat_input("Ask me something..."):
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.spinner("Thinking..."):
            response = requests.post(f"{BACKEND_URL}/chat/", json={"question": prompt}, headers={"X-User": st.session_state["username"]})
            if response.status_code == 200:
                result = response.json()
                answer = result["answer"]
                sources = ", ".join(result.get("sources", [])) or "None"
                reply = f"{answer}<br><small><i>Sources: {sources}</i></small>"

                # Store log_id with reply (so we can send feedback)
                log_id = result.get("log_id")
                st.session_state["messages"].append({"role": "assistant", "content": reply, "log_id": log_id})
            else:
                st.session_state["messages"].append({"role": "assistant", "content": "❌ Backend error", "log_id": None})
        st.rerun()

    # Feedback buttons (for last assistant message)
    if st.session_state["messages"] and st.session_state["messages"][-1]["role"] == "assistant":
        last_message = st.session_state["messages"][-1]
        log_id = last_message.get("log_id")

        if log_id:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👍 Helpful"):
                    requests.post(f"{BACKEND_URL}/feedback/{log_id}", json={"feedback": 1})
                    st.success("Thanks for your feedback! 👍")
            with col2:
                if st.button("👎 Not Helpful"):
                    requests.post(f"{BACKEND_URL}/feedback/{log_id}", json={"feedback": 0})
                    st.warning("Sorry about that, we’ll improve! 👎")


# -------------------------
#  Analytics Dashboard Page
# -------------------------
elif page == "Analytics Dashboard":
    st.title("📊 Analytics Dashboard")

    #  Ensure DB + logs table exists before querying
    init_db()

    if st.session_state.get("refresh_dashboard", False):
        st.session_state["refresh_dashboard"] = False
        st.rerun()

    # Date range
    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)
    date_range = st.date_input("Select date range", value=(last_week, today), min_value=datetime.date(2020, 1, 1), max_value=today)

    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range

    conn = sqlite3.connect(DB_PATH)
    query = f"SELECT * FROM logs WHERE DATE(timestamp) BETWEEN '{start_date}' AND '{end_date}'"
    df = pd.read_sql_query(query, conn)
    conn.close()

    st.write(f"📅 Showing logs from **{start_date}** to **{end_date}**")

    if df.empty:
        st.info("No logs yet. Ask the chatbot a few questions first.")
    else:
        # Tabs
        tab1, tab2, tab3 = st.tabs(["📊 Overview", "👍 Feedback", "📌 Topics"])

        # -------------------
        # Overview Tab
        # -------------------
        with tab1:
            col1, col2, col3 = st.columns(3)
            col1.metric("Escalation Rate", f"{df['escalated'].mean() * 100:.1f}%")
            col2.metric("Avg Confidence (lower=better)", f"{df['confidence'].dropna().mean():.2f}")
            if "response_time" in df.columns:
                col3.metric("Avg Response Time (s)", f"{df['response_time'].dropna().mean():.2f}")

            st.subheader("Top 5 Asked Questions")
            top_qs = df["question"].value_counts().head(5)
            st.bar_chart(top_qs)

            st.subheader("Escalations Over Time")
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            daily_escalations = df.groupby(df["timestamp"].dt.date)["escalated"].sum()
            st.line_chart(daily_escalations)

            # Heatmap
            st.subheader("Busiest Hours of Chatbot Usage")
            df["hour"] = df["timestamp"].dt.hour
            df["day"] = df["timestamp"].dt.day_name()
            heatmap_data = df.pivot_table(index="day", columns="hour", values="id", aggfunc="count").fillna(0)
            ordered_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            heatmap_data = heatmap_data.reindex(ordered_days)
            fig, ax = plt.subplots(figsize=(12, 6))
            sns.heatmap(heatmap_data, cmap="YlGnBu", annot=True, fmt=".0f", cbar=True, ax=ax)
            ax.set_title("Chatbot Usage by Day & Hour")
            ax.set_xlabel("Hour of Day")
            ax.set_ylabel("Day of Week")
            st.pyplot(fig)

        # -------------------
        # Feedback Tab
        # -------------------
        with tab2:
            if "feedback" in df.columns:
                helpful = df["feedback"].eq(1).sum()
                not_helpful = df["feedback"].eq(0).sum()
                total_feedback = helpful + not_helpful
                if total_feedback > 0:
                    st.metric("User Satisfaction", f"{(helpful / total_feedback) * 100:.1f}% 👍")

                    st.subheader("Feedback Distribution")
                    feedback_counts = {"👍 Helpful": helpful, "👎 Not Helpful": not_helpful}
                    fig, ax = plt.subplots()
                    ax.pie(feedback_counts.values(), labels=feedback_counts.keys(), autopct="%1.1f%%", startangle=90, colors=["#4CAF50", "#F44336"])
                    ax.axis("equal")
                    st.pyplot(fig)

            st.subheader("Recent Logs with Feedback")
            st.dataframe(df[["timestamp", "user", "question", "feedback"]].tail(10))

        # -------------------
        # Topics Tab
        # -------------------
        with tab3:
            if "topic" in df.columns:
                st.subheader("Most Common Question Topics")
                topic_counts = df["topic"].value_counts().head(10)
                st.bar_chart(topic_counts)

                st.subheader("Example Questions per Cluster")
                for topic, group in df.groupby("topic"):
                    st.markdown(f"**{topic}** ({len(group)} questions)")
                    st.write(group["question"].tolist()[:5])
