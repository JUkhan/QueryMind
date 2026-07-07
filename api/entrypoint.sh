#!/bin/sh
set -e

# Pick the Flask app module based on DB_SYSTEM so the backend can be switched
# with a single environment variable in Coolify (no image rebuild needed).
case "$(printf '%s' "${DB_SYSTEM:-sqlite}" | tr '[:upper:]' '[:lower:]')" in
  postgres|postgresql)
    APP_MODULE="api-postgres:app"
    ;;
  mssql|sqlserver)
    APP_MODULE="api-mssql:app"
    ;;
  *)
    APP_MODULE="api-sqlite:app"
    ;;
esac

echo "Starting API with DB_SYSTEM=${DB_SYSTEM:-sqlite} -> ${APP_MODULE}"
exec gunicorn --config gunicorn.conf.py "${APP_MODULE}"
