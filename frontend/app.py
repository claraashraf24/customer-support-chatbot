import streamlit as st
import requests
import sqlite3
import pandas as pd
import time
import streamlit.components.v1 as components
import datetime
import os

# 🔗 Backend URL (set in docker-compose, defaults to localhost for dev)
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# ✅ DB path works inside Docker (volume mounted to /app)
DB_PATH = os.getenv("DB_PATH", "/app/chatbot_logs.db")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["username"] = None

if not st.session_state["authenticated"]:
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    # Demo-only: hardcoded users
    users = {"admin": "admin123", "clara": "pass123", "demo": "demo123"}

    if st.button("Login"):
        if username in users and users[username] == password:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.success(f"✅ Welcome, {username}!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

    st.stop()  # prevent loading rest of app until logged in


def copy_to_clipboard(text: str, key: str):
    """Render a copy-to-clipboard button with JS and dynamic feedback."""
    button_id = f"copy-btn-{key}"
    copied_id = f"copied-{key}"

    components.html(
        f"""
        <button id="{button_id}" 
                style="padding:6px 12px; border-radius:8px; border:none; cursor:pointer; background-color:#eee;">
            📋 Copy
        </button>
        <span id="{copied_id}" style="margin-left:8px; color:green; display:none;">Copied!</span>
        <script>
        const btn = document.getElementById("{button_id}");
        const copied = document.getElementById("{copied_id}");
        btn.onclick = function() {{
            navigator.clipboard.writeText({repr(text)});
            copied.style.display = "inline";
            btn.innerText = "✅ Copied!";
            btn.style.backgroundColor = "#90EE90";
            setTimeout(() => {{
                copied.style.display = "none";
                btn.innerText = "📋 Copy";
                btn.style.backgroundColor = "#eee";
            }}, 2000);
        }};
        </script>
        """,
        height=40,
    )


st.set_page_config(page_title="Docs-Aware Chatbot", page_icon="🤖")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Chatbot", "Analytics Dashboard"])

# -------------------------
# 📚 Chatbot Page
# -------------------------
if page == "Chatbot":
    st.title("📚 Docs-Aware Customer Support Chatbot")

    # Sidebar for file upload
    st.sidebar.header("Upload Documents")
    uploaded_file = st.sidebar.file_uploader("Upload a file", type=["pdf", "docx", "txt"])
    upload_mode = st.sidebar.radio("Upload mode", ["Single (replace)", "Append (multi-file)"])

    if uploaded_file:
        with st.spinner("Uploading and indexing..."):
            endpoint = (
                f"{BACKEND_URL}/upload/single"
                if upload_mode == "Single (replace)"
                else f"{BACKEND_URL}/upload/append"
            )

            response = requests.post(
                endpoint,
                files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
            )
            if response.status_code == 200:
                st.sidebar.success("✅ File uploaded & indexed")
            else:
                st.sidebar.error("❌ Upload failed")

    # 🔄 Re-index all docs button
    if st.sidebar.button("🔄 Re-index All Documents"):
        with st.spinner("Rebuilding index from all docs..."):
            response = requests.post(f"{BACKEND_URL}/upload/reindex")
            if response.status_code == 200:
                st.sidebar.success("✅ All docs re-indexed")
            else:
                st.sidebar.error("❌ Re-index failed")

    # 📋 Show currently indexed files
    try:
        response = requests.get(f"{BACKEND_URL}/upload/list")
        if response.status_code == 200:
            files = response.json().get("indexed_files", [])
            if files:
                st.sidebar.subheader("Indexed Files")
                for f in files:
                    st.sidebar.markdown(f"- {f}")
            else:
                st.sidebar.info("No files indexed yet.")
        else:
            st.sidebar.warning("⚠️ Could not fetch indexed files")
    except Exception:
        st.sidebar.warning("⚠️ Backend not reachable for file list")

    # Chat UI
    st.subheader("💬 Ask your documents")

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Display past messages with avatars
    for msg in st.session_state["messages"]:
        avatar = "🧑" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask me something about your documents..."):
        # Display user message
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)

        # Send to backend
        with st.spinner("Thinking..."):
            response = requests.post(
                f"{BACKEND_URL}/chat/",
                json={"question": prompt},
                headers={"X-User": st.session_state["username"]}
            )
            if response.status_code == 200:
                result = response.json()
                answer = result["answer"]
                sources = result.get("sources", [])
                confidence = result.get("confidence_score", None)
                log_id = result.get("log_id", None)

                bot_reply = f"{answer}\n\n**Sources:** {', '.join(set(sources)) if sources else 'None'}"
                if confidence is not None:
                    bot_reply += f"\n\n_Confidence: {round((1 - confidence) * 100)}%_"
            else:
                bot_reply = "❌ Error connecting to backend"
                log_id = None

        # Display bot reply with streaming + copy + feedback
        st.session_state["messages"].append({"role": "assistant", "content": bot_reply})
        with st.chat_message("assistant", avatar="🤖"):
            if "Handing off to a human" in bot_reply:
                st.markdown(f"**:red[{bot_reply}]**")
            else:
                placeholder = st.empty()
                streamed_text = ""
                for char in bot_reply:
                    streamed_text += char
                    placeholder.markdown(streamed_text)
                    time.sleep(0.01)

                copy_to_clipboard(bot_reply, key=f"{len(st.session_state['messages'])}")

                # 👍👎 feedback buttons
                if log_id is not None:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("👍 Helpful", key=f"up-{log_id}"):
                            requests.post(f"{BACKEND_URL}/feedback/", json={"log_id": log_id, "feedback": 1})
                            st.success("Thanks for the feedback! ✅")
                            st.session_state["refresh_dashboard"] = True
                    with col2:
                        if st.button("👎 Not Helpful", key=f"down-{log_id}"):
                            requests.post(f"{BACKEND_URL}/feedback/", json={"log_id": log_id, "feedback": 0})
                            st.warning("Feedback noted. ⚠️")
                            st.session_state["refresh_dashboard"] = True


# -------------------------
# 📊 Analytics Dashboard Page
# -------------------------
elif page == "Analytics Dashboard":
    st.title("📊 Chatbot Analytics Dashboard")

    if st.session_state.get("refresh_dashboard", False):
        st.session_state["refresh_dashboard"] = False
        st.rerun()

    # Default range: last 7 days
    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)

    date_range = st.date_input(
        "Select date range",
        value=(last_week, today),
        min_value=datetime.date(2020, 1, 1),
        max_value=today
    )

    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range

    conn = sqlite3.connect(DB_PATH)
    query = f"""
        SELECT * FROM logs
        WHERE DATE(timestamp) BETWEEN '{start_date}' AND '{end_date}'
    """
    print("FRONTEND DB PATH:", DB_PATH)
    df = pd.read_sql_query(query, conn)
    conn.close()

    st.write(f"📅 Showing logs from **{start_date}** to **{end_date}**")

    if df.empty:
        st.info("No logs yet. Ask the chatbot a few questions first.")
    else:
        st.subheader("Recent Logs (full data incl. feedback)")
        st.dataframe(df.tail(10))

        escalation_rate = df["escalated"].mean() * 100
        st.metric("Escalation Rate", f"{escalation_rate:.1f}%")

        avg_conf = df["confidence"].dropna().mean()
        if avg_conf is not None:
            st.metric("Average Confidence (lower = better)", f"{avg_conf:.2f}")

        if "response_time" in df.columns:
            avg_response_time = df["response_time"].dropna().mean()
            st.metric("Avg Response Time (s)", f"{avg_response_time:.2f}")

        if "feedback" in df.columns:
            helpful = df["feedback"].eq(1).sum()
            not_helpful = df["feedback"].eq(0).sum()
            total_feedback = helpful + not_helpful
            if total_feedback > 0:
                satisfaction = (helpful / total_feedback) * 100
                st.metric("User Satisfaction", f"{satisfaction:.1f}% 👍")

        st.subheader("Top 5 Asked Questions")
        top_qs = df["question"].value_counts().head(5)
        st.bar_chart(top_qs)

        if "topic" in df.columns:
            st.subheader("Most Common Question Topics")
            topic_counts = df["topic"].value_counts().head(10)
            st.bar_chart(topic_counts)

            st.subheader("Example Questions per Cluster")
            for topic, group in df.groupby("topic"):
                st.markdown(f"**{topic}** ({len(group)} questions)")
                st.write(group["question"].tolist()[:5])

        st.subheader("Escalations Over Time")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        daily_escalations = df.groupby(df["timestamp"].dt.date)["escalated"].sum()
        st.line_chart(daily_escalations)
