import os

# Gunicorn configuration for Cloud Run
workers = 1
threads = 8
timeout = 0
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
worker_class = "uvicorn.workers.UvicornWorker"
