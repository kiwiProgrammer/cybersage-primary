#!/bin/sh
# POSIX-compliant shell script to start all services

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Starting all services with docker-compose..."
echo ""

cd "$SCRIPT_DIR"

docker-compose --project-directory ./ \
  -f agent_a/docker-compose.yml \
  -f agent_c/docker-compose.yml \
  -f agent_d/docker-compose.yml \
  -f docker-compose.yml \
  up --build
