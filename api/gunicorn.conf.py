# gunicorn.conf.py
bind = "0.0.0.0:5000"
# Keep 1 worker: conversation state lives in an in-process InMemorySaver
# (see gen_sql/sql_gen.py). Multiple workers would fragment chat history
# across processes. Scaling out needs a shared checkpointer first.
workers = 1
worker_class = "sync"
worker_connections = 1000
# LLM round-trips (plus the tool-calling loop) can easily exceed 30s. A short
# timeout makes gunicorn kill the worker mid-request -> proxy returns 502.
timeout = 120
keepalive = 2
preload_app = False  # Important: Don't preload to avoid connection sharing
max_requests = 1000  # Restart workers periodically
max_requests_jitter = 50