#!/bin/bash
set -e

echo "=== Deploying STAGING environment ==="

cd $CI_DEPLOY_PATH_DIRECTORY

# Останавливаем только stage/тестовые контейнеры
docker compose -f docker-compose-stage.yml down || true

# Загружаем образы
docker load -i $CI_PROJECT_ARTEFACT_NAME
docker load -i $CI_REDIS_ARTEFACT_NAME

# Запускаем stage окружение
docker compose -f docker-compose-stage.yml up -d

# Очистка старых образов (только stage/тестовые)
docker image prune -f

echo "=== STAGING environment deployed successfully ==="
echo "Web: http://localhost:8001"
echo "Redis: localhost:6380"