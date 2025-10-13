FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the application code
COPY . /app/agent_c_queue/

WORKDIR /app/agent_c_queue

# Copy requirements and install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/out /app/temp

# Set Python path
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "-u", "/app/agent_c_queue/app.py"]
