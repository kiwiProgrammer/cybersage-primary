FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    curl \
    git \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy agent_a module (needed for imports)
COPY --from=agent_a . /app/agent_a

WORKDIR /app/agent_a

RUN pip install --no-cache-dir -e .

WORKDIR /app/agent_a_web

# Copy agent_a_web application
COPY . /app/agent_a_web

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
#RUN pip install --no-cache-dir -r agent_a_requirements.txt

# Set working directory to agent_a_web
WORKDIR /app/agent_a_web

# Create output directory
RUN mkdir -p /app/out

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV OUTPUT_DIR=/app/out

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
