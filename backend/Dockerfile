FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/backend
RUN touch /app/backend/__init__.py

#  Point backend to shared volume
ENV DB_PATH=/app/data/chatbot_logs.db

CMD ["sh", "-c", "python /app/backend/init_db.py && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
