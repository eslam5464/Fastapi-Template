@echo off
celery -A app.services.task_queue worker --loglevel=info --pool=solo %*
