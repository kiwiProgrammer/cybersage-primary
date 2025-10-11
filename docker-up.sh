#!/bin/sh
# POSIX-compliant shell script to start all services

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Starting all services with docker-compose..."
echo ""

cd "$SCRIPT_DIR"

docker-compose --project-directory ./ \
  -f AutonomousCouncil/docker-compose.yml \
  -f security-advisor/docker-compose.yml \
  -f docker-compose.yml \
  up --build
