from celery_app.tasks.test_tasks import test_task

# Отправляем тестовую задачу
result = test_task.delay("Тестовое сообщение")
print(f"Задача отправлена, ID: {result.id}")
try:
    task_result = result.get(timeout=10)
    print(f"Результат задачи: {task_result}")
except Exception as e:
    print(f"Ошибка выполнения задачи: {e}")