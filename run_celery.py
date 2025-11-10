#!/usr/bin/env python3
"""
Скрипт для запуска Celery worker
"""
from celery_app.app import celery_app

if __name__ == '__main__':
    celery_app.worker_main()