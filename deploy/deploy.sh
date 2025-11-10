#!/bin/bash
set -e

echo "=== Deploying PRODUCTION environment ==="

cd $CI_DEPLOY_PATH_DIRECTORY

# Останавливаем старые контейнеры
docker compose -f docker-compose-prod.yml down || true

# Загружаем образы
docker load -i $CI_PROJECT_ARTEFACT_NAME
docker load -i $CI_REDIS_ARTEFACT_NAME
docker tag redis:8-alpine redis-image

# Запускаем прод окружение
docker compose -f docker-compose-prod.yml up -d

# Очистка старых образов
docker image prune -f

echo "=== PRODUCTION environment deployed successfully ==="
echo "Web: http://localhost:8000"
echo "Redis: localhost:6379"