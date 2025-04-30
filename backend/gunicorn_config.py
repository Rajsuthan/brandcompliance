# Gunicorn configuration file
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 600  # 10 minutes in seconds
keepalive = 65
