# Specialized Dockerfile for Build Context: backend/
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# In this context, requirements.txt is in the same folder
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything from the backend folder
COPY . .

# Expose port
EXPOSE 8080

# Run uvicorn (app/main.py is in the current directory)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
