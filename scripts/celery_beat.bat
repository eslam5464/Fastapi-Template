@echo off
celery -A app.services.task_queue beat --loglevel=info %*