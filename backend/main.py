from fastapi import FastAPI
from dotenv import load_dotenv
import os
import shutil
from backend.services.embeddings import DATA_DIR, INDEX_DIR
from backend.services.logging_service import init_db

# ✅ Load environment variables from .env (works in Docker too if env_file is set)
load_dotenv()

# ✅ Double-check for OPENAI_API_KEY
if not os.getenv("OPENAI_API_KEY"):
    print("⚠️ WARNING: OPENAI_API_KEY is not set. Embeddings will fail until this is fixed.")

# ✅ Import routers after env is loaded
from backend.routers import upload, chat, feedback

app = FastAPI(title="Docs-Aware Chatbot API")

# ✅ Register routers
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(feedback.router)


@app.get("/")
def root():
    return {"message": "Docs-Aware Chatbot API is running 🚀"}


@app.on_event("startup")
def cleanup_on_startup():
    # Clear embeddings index
    if os.path.exists(INDEX_DIR):
        shutil.rmtree(INDEX_DIR)
        print("🧹 Cleared old FAISS index on startup")

    # Clear old files in /data
    if os.path.exists(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            file_path = os.path.join(DATA_DIR, f)
            if os.path.isfile(file_path):
                os.remove(file_path)
        print("🧹 Cleared old /data files on startup")

    # Initialize DB
    init_db()
    print("✅ Database initialized")
