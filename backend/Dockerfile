FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Copy requirements first (inside ./backend context, so just "requirements.txt")
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend code (since context = ./backend)
COPY . /app/backend

# Ensure backend is a Python package
RUN touch /app/backend/__init__.py

# Start FastAPI
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
