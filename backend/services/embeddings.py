# backend/services/embeddings.py
import os
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader

_vectorstore_cache = None

DATA_DIR = "data"
INDEX_DIR = "embeddings/faiss_index"
MANIFEST_FILE = os.path.join(INDEX_DIR, "indexed_files.json")


# -----------------------------
# 🔹 Manifest Helpers
# -----------------------------
def _save_manifest(filenames):
    os.makedirs(INDEX_DIR, exist_ok=True)
    with open(MANIFEST_FILE, "w") as f:
        json.dump(filenames, f)


def _load_manifest():
    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, "r") as f:
            return json.load(f)
    return []


# -----------------------------
# 🔹 Document Loading
# -----------------------------
def load_document(file_path: str):
    """Load document based on extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return PyPDFLoader(file_path).load()
    elif ext == ".docx":
        return Docx2txtLoader(file_path).load()
    elif ext == ".txt":
        return TextLoader(file_path).load()
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def add_metadata(chunks, file_path: str):
    """Attach source filename, page number (if available), and chunk index."""
    for i, chunk in enumerate(chunks):
        chunk.metadata["source"] = os.path.basename(file_path)
        chunk.metadata["chunk"] = i
        if "page" not in chunk.metadata and "page_number" in chunk.metadata:
            chunk.metadata["page"] = chunk.metadata["page_number"]
    return chunks


# -----------------------------
# 🔹 Vectorstore Creation
# -----------------------------
def create_vectorstore():
    """Rebuild FAISS index from all docs in /data."""
    docs = []
    for filename in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.isfile(file_path):
            try:
                docs.extend(load_document(file_path))
            except Exception as e:
                print(f"Skipping {filename}: {e}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    # Add metadata
    all_chunks = []
    for filename in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.isfile(file_path):
            file_docs = load_document(file_path)
            file_chunks = splitter.split_documents(file_docs)
            file_chunks = add_metadata(file_chunks, file_path)
            all_chunks.extend(file_chunks)

    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(all_chunks, embeddings)

    os.makedirs(INDEX_DIR, exist_ok=True)
    vectorstore.save_local(INDEX_DIR)

    # Save manifest
    _save_manifest([f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f))])

    return vectorstore


def load_vectorstore():
    """Load FAISS index if exists, else create one. Cached in memory."""
    global _vectorstore_cache
    if _vectorstore_cache is not None:
        return _vectorstore_cache

    embeddings = OpenAIEmbeddings()
    if os.path.exists(INDEX_DIR):
        _vectorstore_cache = FAISS.load_local(
            INDEX_DIR, embeddings, allow_dangerous_deserialization=True
        )
    else:
        _vectorstore_cache = create_vectorstore()
    return _vectorstore_cache


def reindex_all_docs():
    """Rebuild FAISS index from all documents in /data."""
    import shutil
    if os.path.exists(INDEX_DIR):
        shutil.rmtree(INDEX_DIR)

    vectorstore = create_vectorstore()

    global _vectorstore_cache
    _vectorstore_cache = vectorstore

    return vectorstore


# -----------------------------
# 🔹 Append-Only Indexing
# -----------------------------
def add_file_to_vectorstore(file_path: str):
    """Embed ONLY this file and add it to existing FAISS index."""
    global _vectorstore_cache

    docs = load_document(file_path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    chunks = add_metadata(chunks, file_path)

    embeddings = OpenAIEmbeddings()

    if os.path.exists(INDEX_DIR):
        vectorstore = FAISS.load_local(
            INDEX_DIR, embeddings, allow_dangerous_deserialization=True
        )
        vectorstore.add_documents(chunks)
    else:
        vectorstore = FAISS.from_documents(chunks, embeddings)

    os.makedirs(INDEX_DIR, exist_ok=True)
    vectorstore.save_local(INDEX_DIR)

    # Update manifest
    files = _load_manifest()
    filename = os.path.basename(file_path)
    if filename not in files:
        files.append(filename)
        _save_manifest(files)

    _vectorstore_cache = vectorstore
    return vectorstore


def list_indexed_files():
    """Return list of indexed files (from manifest)."""
    return _load_manifest()


# -----------------------------
# 🔹 Searching
# -----------------------------
def search_with_confidence(vectorstore, query: str, k: int = 3, threshold: float = 0.7):
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    docs = retriever.get_relevant_documents(query)

    results = []
    for doc in docs:
        score = doc.metadata.get("score", 1.0)
        results.append((doc, score))

    return results


def similarity_search_with_scores(vectorstore, query: str, k: int = 3):
    return vectorstore.similarity_search_with_score(query, k=k)
