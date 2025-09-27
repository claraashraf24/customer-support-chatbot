from fastapi import APIRouter, UploadFile, File
import os
import shutil
from backend.services.embeddings import (
    reindex_all_docs,
    add_file_to_vectorstore,
)

router = APIRouter(prefix="/upload", tags=["upload"])

DATA_DIR = "data"
INDEX_DIR = "embeddings/faiss_index"

# ✅ Ensure data dir exists on startup
os.makedirs(DATA_DIR, exist_ok=True)


# 🚀 Replace mode (clear index + add only this file)
@router.post("/single")
async def upload_single_doc(file: UploadFile = File(...)):
    # Clear embeddings index
    if os.path.exists(INDEX_DIR):
        shutil.rmtree(INDEX_DIR)

    # Clear all old files in /data
    if os.path.exists(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            file_path = os.path.join(DATA_DIR, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

    # ✅ Make sure data dir exists again
    os.makedirs(DATA_DIR, exist_ok=True)

    # Save uploaded file
    save_path = os.path.join(DATA_DIR, file.filename)
    with open(save_path, "wb") as f:
        f.write(await file.read())

    # Add only this file to index
    add_file_to_vectorstore(save_path)

    return {"message": f"File {file.filename} uploaded and indexed (single mode) 🚀"}


# 🚀 Append mode (add to existing index, keep old files)
@router.post("/append")
async def upload_and_append(file: UploadFile = File(...)):
    os.makedirs(DATA_DIR, exist_ok=True)  # ✅ ensure dir exists
    save_path = os.path.join(DATA_DIR, file.filename)
    with open(save_path, "wb") as f:
        f.write(await file.read())

    add_file_to_vectorstore(save_path)

    return {"message": f"File {file.filename} uploaded and added to index 🚀"}


# 🚀 Reindex all docs in /data
@router.post("/reindex")
async def reindex_docs():
    reindex_all_docs()
    return {"message": "All documents re-indexed 🚀"}


# 🚀 List currently indexed files
@router.get("/list")
async def list_indexed_docs():
    if not os.path.exists(DATA_DIR):
        return {"indexed_files": []}

    files = [f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f))]
    return {"indexed_files": files}
