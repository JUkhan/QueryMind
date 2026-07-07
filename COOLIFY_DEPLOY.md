# Deploying QueryMind on Hostinger Coolify

This app is deployed as a **Docker Compose** resource. Coolify builds both
images from their Dockerfiles and routes public traffic through its built-in
proxy — you do not open host ports yourself.

## Architecture on Coolify

```
Internet ──► Coolify proxy ──► angular (nginx, port 80)
                                  │  serves the Angular SPA
                                  └─ proxies /api/ and /static/ ──► api (gunicorn, port 5000)
```

Only the **angular** service gets a public domain. The Angular app calls the
backend with relative `/api/` URLs, which nginx forwards to the internal
`api` service, so the API stays private on the internal network.

## Prerequisites

- A Hostinger VPS with Coolify installed.
- This repository pushed to a Git provider (GitHub/GitLab) that Coolify can reach.
- A Google Gemini API key.

## Steps

1. **Create the resource**
   - Coolify → your Project → **+ New** → **Docker Compose** (or "Application"
     with build pack = *Docker Compose*).
   - Connect this Git repository and branch (`main`).
   - Set the **Compose file path** to `docker-compose.yaml` (repo root).

2. **Set environment variables** (Service → *Environment Variables*)

   | Variable         | Required        | Example / notes                                   |
   |------------------|-----------------|---------------------------------------------------|
   | `GOOGLE_API_KEY` | ✅ yes          | Your Gemini key. Mark as a **secret**.            |
   | `DB_SYSTEM`      | optional        | `sqlite` (default), `postgres`, or `mssql`.       |
   | `DATABASE_URL`   | postgres/mssql  | Connection string (see `api/.env.example`).       |
   | `SCHEMA`         | optional        | Schema name for postgres/mssql.                   |
   | `SEED_USERNAME`  | optional        | Initial login username (default `testuser`).      |
   | `SEED_EMAIL`     | optional        | Initial login email (default `testuser@gmail.com`).|
   | `SEED_SAMPLE_DATA`| optional       | `1` (default) loads demo data from `sample_data.sql`; `0` to skip. |

   On first boot with an empty database the API seeds one login user so you can
   sign in immediately. The app has no self-registration and no passwords —
   login just matches `username` + `email`. **Log in with the seeded values**
   (default `testuser` / `testuser@gmail.com`, or whatever you set above), then
   change/add users as needed. Set `SEED_DEFAULT_USER=0` to disable seeding.

   With `DB_SYSTEM=sqlite` (default) no `DATABASE_URL` is needed — the SQLite
   file is stored on the `querymind-data` volume and survives redeploys.

3. **Assign the domain**
   - The compose file declares `SERVICE_FQDN_ANGULAR_80`, so Coolify creates a
     route to the angular container's port 80 automatically.
   - Open Service → **Domains** for the `angular` service and set your domain
     (e.g. `https://querymind.yourdomain.com`). Coolify provisions HTTPS via
     Let's Encrypt. Point that DNS record at your VPS first.

4. **Deploy**
   - Click **Deploy**. Coolify builds both images and starts the stack.
   - Healthchecks gate readiness: `api` must answer on `/` before `angular`
     starts, and the domain goes live once `angular` is healthy.

## Switching database backend

The `api/entrypoint.sh` picks the Flask module from `DB_SYSTEM`:

- `sqlite`   → `api-sqlite:app` (default, uses the `querymind-data` volume)
- `postgres` → `api-postgres:app` (set `DATABASE_URL`)
- `mssql`    → `api-mssql:app` (set `DATABASE_URL`; needs the MS ODBC driver)

For **mssql**, the base image includes `unixodbc` but not the Microsoft ODBC
driver. Add the `msodbcsql18` package to `api/Dockerfile` if you use mssql, or
point `DATABASE_URL` at a database reachable with the installed driver.

## Data persistence

The named volume `querymind-data` is mounted at `/app/data`, and
`docker-compose.yaml` sets `SQLITE_PATH=/app/data/database.db`. Back this volume
up from Coolify (Storages) if you rely on the SQLite database in production.

## Security notes

- **Rotate the Google API key** that was previously committed to `api/.env` —
  treat it as compromised. Store the new key only as a Coolify secret.
- `.env` is excluded from the Docker image (see `api/.dockerignore`); provide
  all secrets through Coolify environment variables.

## Local development (unchanged)

```bash
docker compose up --build
```

Note: locally there is no Coolify proxy, so add a host port mapping if you want
to reach it directly, e.g. under `angular:` add `ports: ["4200:80"]`, then open
http://localhost:4200. In production, leave ports unmapped and let Coolify route.
