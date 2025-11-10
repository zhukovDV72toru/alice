# gunicorn.conf.py
import multiprocessing
import os
import sys

# Количество рабочих процессов (рекомендуется: 2 * CPU_cores + 1)
workers = multiprocessing.cpu_count() * 2 + 1

# Используйте async worker class для aiohttp
worker_class = "aiohttp.GunicornWebWorker"

# Добавляем путь к проекту в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

bind = "0.0.0.0:8000"

# Логирование
accesslog = "-"  # stdout
errorlog = "-"
loglevel = "info"