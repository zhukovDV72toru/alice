from config import config

# Конфигурация Celery
broker_url = config.redis_url
result_backend = config.redis_url

# Настройки Celery
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Yekaterinburg'
enable_utc = True

task_default_queue = 'default'
task_track_started = True
task_ignore_result = False

task_time_limit = 30
task_soft_time_limit = 24