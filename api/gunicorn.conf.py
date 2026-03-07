# gunicorn.conf.py
bind = "0.0.0.0:5000"
workers = 1  # Start with 1 worker to test
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
preload_app = False  # Important: Don't preload to avoid connection sharing
max_requests = 1000  # Restart workers periodically
max_requests_jitter = 50