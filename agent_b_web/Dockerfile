FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=agent_b . /app/agent_b/

WORKDIR /app/agent_b

RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app/agent_b_web

# Copy the application code
COPY . /app/agent_b_web/

# Copy requirements and install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/out /app/pending

# Set Python path
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "-u", "/app/agent_b_web/app.py"]
