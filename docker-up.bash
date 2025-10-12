#!/bin/bash
# Bash script to start all services

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting all services with docker-compose..."
echo ""

cd "${SCRIPT_DIR}"

docker-compose --env-file ./.env --project-directory ./ \
  -f agent_a_web/docker-compose.yml \
  -f agent_c/docker-compose.yml \
  -f agent_d/docker-compose.yml \
  -f docker-compose.yml \
  up --build
