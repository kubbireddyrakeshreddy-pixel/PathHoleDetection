FROM python:3.11-slim

# Install system dependencies required for OpenCV and YOLO
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Set working directory to backend where app.py lives
WORKDIR /app/backend

# Set environment variables for production
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:///pothole_system.db

# Expose port 7860 (default for Hugging Face spaces)
EXPOSE 7860

# Run the app with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "120", "wsgi:app"]
