from fastapi import APIRouter, Request
from pydantic import BaseModel
from backend.services.embeddings import load_vectorstore, similarity_search_with_scores
from langchain_openai import ChatOpenAI
from backend.services.logging_service import log_interaction, init_db
from collections import defaultdict
import time

router = APIRouter(prefix="/chat", tags=["chat"])

# Make sure DB table exists
init_db()
ESCALATION_MESSAGE = "I’m not confident enough to answer. Handing off to a human 👩‍💻"


class ChatRequest(BaseModel):
    question: str


@router.post("/")
async def chat_with_docs(request: ChatRequest, fastapi_request: Request):
    start_time = time.time()   # ⏱ start measuring
    user = fastapi_request.headers.get("X-User", "anonymous")

    vectorstore = load_vectorstore()
    docs_and_scores = similarity_search_with_scores(vectorstore, request.question, k=10)
    print("DEBUG: Raw scores from similarity_search_with_scores:", docs_and_scores)

    # Case 1: No docs found → escalate
    if not docs_and_scores:
        answer = ESCALATION_MESSAGE
        response_time = time.time() - start_time
        try:
            log_id = log_interaction(user, request.question, answer, None, [], True, response_time)
            print(f"✅ Logged escalation with id={log_id}")
        except Exception as e:
            print(f"⚠️ Logging failed: {e}")
            log_id = None
        return {
            "question": request.question,
            "answer": answer,
            "sources": [],
            "confidence_score": None,
            "log_id": log_id,
        }

    # Pick best match
    best_doc, best_score = docs_and_scores[0]
    best_score = float(best_score)
    threshold = 0.7  # lower distance = better

    # Case 2: Low confidence → escalate
    if best_score >= threshold:
        answer = ESCALATION_MESSAGE
        response_time = time.time() - start_time
        try:
            log_id = log_interaction(user, request.question, answer, best_score, [], True, response_time)
            print(f"✅ Logged low-confidence escalation with id={log_id}")
        except Exception as e:
            print(f"⚠️ Logging failed: {e}")
            log_id = None
        return {
            "question": request.question,
            "answer": answer,
            "sources": [],
            "confidence_score": best_score,
            "log_id": log_id,
        }

    # Case 3: Confident → ask GPT with context
    file_chunks = defaultdict(list)
    for doc, _ in docs_and_scores:
        source = doc.metadata.get("source", "Unknown")
        file_chunks[source].append(doc.page_content)

    context_sections = []
    for source, chunks in file_chunks.items():
        joined_text = "\n\n".join(chunks)
        context_sections.append(f"### Document: {source}\n{joined_text}")

    context = "\n\n".join(context_sections)

    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    prompt = f"""
    You are a helpful assistant. Use ALL of the following context to answer the question. 
    If multiple documents are relevant, summarize each of them clearly and separately.

    Context (grouped by document):
    {context}

    Question:
    {request.question}
    """

    response = llm.invoke(prompt)
    answer_text = response.content.strip()

    # Collect sources
    sources = []
    for doc, _ in docs_and_scores:
        source = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page", None)
        chunk = doc.metadata.get("chunk", None)

        if page is not None:
            sources.append(f"{source} - Page {page}")
        elif chunk is not None:
            sources.append(f"{source} - Chunk {chunk}")
        else:
            sources.append(source)

    response_time = time.time() - start_time  # ⏱ stop measuring

    # 🚨 Case 4: GPT doesn’t know → escalate
    if answer_text.lower().startswith("i don't know"):
        answer = ESCALATION_MESSAGE
        try:
            log_id = log_interaction(user, request.question, answer, best_score, [], True, response_time)
            print(f"✅ Logged GPT fallback escalation with id={log_id}")
        except Exception as e:
            print(f"⚠️ Logging failed: {e}")
            log_id = None
        return {
            "question": request.question,
            "answer": answer,
            "sources": [],
            "confidence_score": best_score,
            "log_id": log_id,
        }

    # ✅ Case 5: Normal answer
    try:
        log_id = log_interaction(user, request.question, answer_text, best_score, sources, False, response_time)
        print(f"✅ Logged normal answer with id={log_id}")
    except Exception as e:
        print(f"⚠️ Logging failed: {e}")
        log_id = None

    return {
        "question": request.question,
        "answer": answer_text,
        "sources": list(set(sources)),
        "confidence_score": best_score,
        "log_id": log_id,  # Always return DB ID
    }
