#!/bin/bash
# Bash script to start all services

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting all services with docker-compose..."
echo ""

cd "${SCRIPT_DIR}"

docker-compose --project-directory ./ \
  -f AutonomousCouncil/docker-compose.yml \
  -f security-advisor/docker-compose.yml \
  -f docker-compose.yml \
  up --build
