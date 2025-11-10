from celery import Celery
from .config import broker_url, result_backend

def create_celery_app():
    """Фабрика для создания приложения Celery"""
    app = Celery(
        'alice_skill',
        broker=broker_url,
        backend=result_backend,
        include=['celery_app.tasks.long_operations', 'celery_app.tasks.test_tasks']
    )
    
    # Конфигурация
    app.config_from_object('celery_app.config')
    
    # Автоматическое обнаружение задач
    app.autodiscover_tasks(['celery_app.tasks', 'celery_app.tasks.test_tasks'])
    
    return app

# Создаем экземпляр приложения
celery_app = create_celery_app()