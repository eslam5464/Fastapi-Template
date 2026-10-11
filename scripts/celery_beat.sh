#!/bin/bash
set -euo pipefail

celery -A app.services.task_queue beat --loglevel=info "$@"
