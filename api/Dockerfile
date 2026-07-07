FROM python:3.13-slim

WORKDIR /app

# unixodbc runtime is required if you switch DB_SYSTEM to mssql (pyodbc).
# Kept minimal; harmless for the default sqlite backend.
RUN apt-get update \
    && apt-get install -y --no-install-recommends unixodbc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Entrypoint selects the app module from DB_SYSTEM (sqlite | postgres | mssql).
RUN chmod +x /app/entrypoint.sh

EXPOSE 5000

CMD ["/app/entrypoint.sh"]
