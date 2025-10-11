# CyberSage Primary

This repository combines multiple cybersecurity and AI-powered analysis tools into a unified deployment.

## Project Structure

This project uses **Git submodules** to manage two main components:

- **AutonomousCouncil** - AI-powered vulnerability analysis system with multi-agent council
- **security-advisor** - Security profiling and advisory platform

## Quick Start

To start all services, simply run:

```bash
./docker-up.sh
# or
./docker-up.bash
```

This will build and start all services including:
- **autonomous-council-api** - Available at http://localhost:8080
- **security-advisor-backend** - Available at http://localhost:8000
- **security-advisor-frontend** - Available at http://localhost:3000
- **chromadb** - Vector database at http://localhost:8001
- **postgres** - Database at localhost:5432

## Working with Git Submodules

### Initial Setup

When cloning this repository for the first time, initialize and update the submodules:

```bash
git clone <repository-url>
cd cybersage-primary
git submodule init
git submodule update
```

Or clone with submodules in one command:

```bash
git clone --recurse-submodules <repository-url>
```

### Updating Submodule References

To update the submodules to their latest commits:

```bash
# Update all submodules to latest from their respective branches
git submodule update --remote

# Or update a specific submodule
git submodule update --remote AutonomousCouncil
git submodule update --remote security-advisor
```

### Working Inside a Submodule

Each submodule is a separate git repository. To make changes:

```bash
# Navigate into the submodule
cd AutonomousCouncil

# Create a branch and make changes
git checkout -b feature-branch
# Make your changes...
git add .
git commit -m "Your changes"
git push origin feature-branch

# Return to main repository
cd ..

# Commit the updated submodule reference
git add AutonomousCouncil
git commit -m "Update AutonomousCouncil submodule"
git push
```

### Checking Submodule Status

```bash
# View current submodule commits
git submodule status

# View submodule summary
git submodule summary
```

## Services Overview

### AutonomousCouncil
- **Port**: 8080
- **API Docs**: http://localhost:8080/docs
- Multi-agent AI system for vulnerability analysis
- Uses ChromaDB for vector storage

### Security Advisor
- **Backend Port**: 8000
- **Frontend Port**: 3000
- Security profiling and advisory platform
- Uses PostgreSQL for data persistence

## Development

### Running Services Individually

You can also start services from their respective subfolders:

```bash
# AutonomousCouncil only
cd AutonomousCouncil
docker-compose up --build

# Security Advisor only
cd security-advisor
docker-compose up --build
```

### Stopping Services

```bash
# Stop all services
docker-compose --project-directory ./ \
  -f AutonomousCouncil/docker-compose.yml \
  -f security-advisor/docker-compose.yml \
  -f docker-compose.yml \
  down

# Stop with volume cleanup
docker-compose --project-directory ./ \
  -f AutonomousCouncil/docker-compose.yml \
  -f security-advisor/docker-compose.yml \
  -f docker-compose.yml \
  down -v
```

## Configuration

The root `docker-compose.yml` file overrides the default ports to avoid conflicts:
- AutonomousCouncil API: 8000 → 8080
- ChromaDB: 8000 → 8001

Environment variables can be configured in a `.env` file in the root directory.

## Troubleshooting

### Submodule not initialized
```bash
git submodule init
git submodule update
```

### Port conflicts
Check if ports 3000, 5432, 8000, 8001, or 8080 are already in use:
```bash
lsof -i :8080
lsof -i :8000
lsof -i :3000
```

### Container logs
```bash
docker-compose logs autonomous-council-api
docker-compose logs security-advisor-backend
docker-compose logs security-advisor-frontend
```
