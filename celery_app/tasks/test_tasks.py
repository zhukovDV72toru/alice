# celery_app/tasks/test_tasks.py
from celery_app.app import celery_app
import time

@celery_app.task
def test_task(message):
    """Простая тестовая задача"""
    print(f"Получено сообщение: {message}")
    time.sleep(50)
    return f"Обработано: {message}"