 Docs-Aware Customer Support Chatbot

This is a customer support chatbot that can read documents you upload, store them, and answer questions based on their content. It’s built with FastAPI (backend) and Streamlit (frontend), and uses OpenAI embeddings + FAISS under the hood for document search.

I built this project to make support teams more efficient — you can upload PDFs, chat with them, and track usage/feedback in one place.

 Features

Upload and manage documents

Replace mode → reset index and start fresh with one file

Append mode → add files without losing the old ones

Reindex mode → rebuild index from all files

Chat with documents in natural language

Feedback system → mark answers as helpful or not

Logs saved in a local SQLite database (chatbot_logs.db)

Simple analytics dashboard (usage + feedback)

Fully containerized with Docker (backend + frontend)

 Tech Stack

Backend: FastAPI, LangChain, FAISS, OpenAI API

Frontend: Streamlit

Database: SQLite (easy to swap with Postgres later)

Deployment: Docker & Docker Compose

 Project Structure
customer-support-chatbot/
├── backend/          # FastAPI backend (routes, services, embeddings)
├── frontend/         # Streamlit frontend
├── data/             # Uploaded documents
├── embeddings/       # FAISS vectorstore
├── logs/             # App logs
├── chatbot_logs.db   # SQLite database
├── docker-compose.yml
├── .env              # Environment variables (not committed)

 Getting Started
1. Clone the repo
git clone https://github.com/YOUR_USERNAME/customer-support-chatbot.git
cd customer-support-chatbot

2. Create a .env file
OPENAI_API_KEY=your-openai-key-here
DATABASE_URL=sqlite:///./logs/chatbot_logs.db

3. Run with Docker
docker-compose up --build


Backend → http://localhost:8000

Frontend → http://localhost:8501

4. Run locally (for dev)

Backend:

cd backend
uvicorn backend.main:app --reload --port 8000


Frontend:

cd frontend
streamlit run app.py

 Roadmap

 Pie chart for feedback (helpful vs not helpful)

 Heatmap for busiest chatbot hours

 Export logs to CSV

 Adjustable thresholds for confidence scores

 UI polish (tabs, light/dark mode)

 Add screenshots to this README

 Author

Hi, I’m Clara Yousif 👋

Biomedical Engineering graduate → now in AI & software development

Experience with DevOps, backend, and automation
#FREE_PALESTINE
