# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies from the backend folder
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project to the container
COPY . .

# Change to the backend directory to run the app if needed, 
# but our main.py is in backend/app/main.py
# So we run it from the root but adjust the module path

# Expose port (Render sets this automatically)
EXPOSE 8080

# Command to run the application
# We need to tell uvicorn to look in the backend folder
# Or we can change WORKDIR to /app/backend
WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
