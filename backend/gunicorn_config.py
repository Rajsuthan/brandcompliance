# Gunicorn configuration file
bind = "0.0.0.0:8001"
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 600  # 10 minutes in seconds
keepalive = 65
