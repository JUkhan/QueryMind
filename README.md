# QueryMind

An AI-powered Business Intelligence dashboard that lets users query their database using plain English. No SQL knowledge required.

## How It Works

1. User types a natural language question (e.g. *"What were our top 5 products last month?"*)
2. Google Gemini AI (via LangGraph) inspects the relevant schema and generates SQL
3. The query executes against your database
4. Results are returned as a table or chart, and can be saved to a personal dashboard

---

## Tech Stack

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| Frontend  | Angular 20, Angular Material, TailwindCSS       |
| Charts    | ng2-charts (Chart.js)                           |
| Dashboard | @katoid/angular-grid-layout (drag & drop)       |
| Backend   | Flask (Python), SQLAlchemy, Gunicorn            |
| AI        | Google Gemini (`gemini-flash`), LangGraph       |
| Databases | SQLite / PostgreSQL / MSSQL                     |
| Deploy    | Docker + Docker Compose                         |

---

## Quick Start (Docker)

```bash
# 1. Clone the repo
git clone <repo-url> && cd QueryMind

# 2. Configure the API
cp api/.env.sample api/.env
# Edit api/.env — set GOOGLE_API_KEY, DATABASE_URL, DB_SYSTEM

# 3. Launch
docker-compose up -d
```

- Frontend: http://localhost:4200
- API: http://localhost:5000

---

## Local Development

### Backend

```bash
cd api
pip install -r requirements.txt
cp .env.sample .env   # fill in values

# Pick the entry point matching your DB:
python api-sqlite.py      # SQLite (simplest)
python api-postgres.py    # PostgreSQL
python api-mssql.py       # MSSQL
```

### Frontend

```bash
cd angular
npm install

npm start              # port 4200 (no proxy)
npm run start:proxy    # port 4201 — proxies /api/** to localhost:5000
```

---

## Environment Variables (`api/.env`)

| Variable       | Description                                       | Example                        |
|----------------|---------------------------------------------------|--------------------------------|
| `GOOGLE_API_KEY` | Google Gemini API key (required)                | `AIza...`                      |
| `DATABASE_URL`  | SQLAlchemy connection string                     | `sqlite:///dev.db`             |
| `DB_SYSTEM`     | `sqlite` \| `postgres` \| `mssql`               | `sqlite`                       |
| `SCHEMA`        | DB schema name                                   | `dbo` (MSSQL) / `public` (PG) |

---

## Project Structure

```
QueryMind/
├── api/
│   ├── app.py                   # Flask app init
│   ├── api-sqlite.py            # SQLite entry point
│   ├── api-postgres.py          # PostgreSQL entry point
│   ├── api-mssql.py             # MSSQL entry point
│   ├── schema.txt               # AI schema knowledge base
│   ├── routes/
│   │   ├── core_routes.py       # Auth, dashboards, helpdesk
│   │   ├── bot_routes.py        # Chatbot & query endpoints
│   │   └── schema_routes.py     # Schema explorer UI & REST
│   ├── gen_sql/
│   │   ├── sql_gen.py           # LangGraph AI pipeline
│   │   ├── schema.py            # schema.txt read/write utils
│   │   └── schema_filter.py     # Schema filtering
│   └── schema_readers/
│       ├── schema_reader.py     # SQLAlchemy inspector
│       └── schema_reader_postgres.py
└── angular/
    └── src/app/
        ├── chat/                # Chat interface
        ├── dashboard/           # Saved dashboards
        ├── search/              # Query search
        ├── table-component/     # Paginated table
        ├── chart-components/    # Bar, line, pie charts
        └── services/            # API service wrappers
```

---

## API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/login` | User login |

### AI Chatbot & Queries
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chatbot` | Send a natural language question |
| GET | `/api/get-bot-messages/<thread_id>` | Fetch conversation history |
| POST | `/api/get-query-result` | AI query generation + execution |
| POST | `/api/get-query-result2` | Direct SQL execution |

### Dashboards
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/dashboard` | Create dashboard |
| GET | `/api/dashboards/<user_id>` | List user's dashboards |
| GET | `/api/dashboard/<id>` | Get dashboard |
| PUT | `/api/dashboard/<id>` | Update dashboard |
| DELETE | `/api/dashboard/<id>` | Delete dashboard |

### Schema Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Interactive schema explorer UI |
| GET | `/api/schema` | Full schema (JSON or text) |
| GET | `/api/tables` | List tables |
| GET | `/api/tables/<name>` | Table details |
| POST/GET | `/api/descriptions` | Table descriptions |
| POST/GET | `/api/comments` | Column comments |

### Help Desk
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/helpdesk` | Create entry |
| GET | `/api/helpdesk` | List all entries |
| GET/PUT/DELETE | `/api/helpdesk/<title>` | Manage entry |

---

## AI Pipeline

The AI pipeline (`api/gen_sql/sql_gen.py`) is a LangGraph `StateGraph` with two nodes:

- **`agent`** — Gemini model with tool binding; generates SQL from natural language
- **`tools`** — Calls `get_schema_detail` to fetch relevant schema context on demand

Conversations are keyed by `thread_id` using an in-memory saver (resets on restart). History is trimmed at 10 messages to control context length.

SQL is extracted from AI responses using a regex that matches ` ```sql `, ` ```sqlite `, or ` ```postgresql ` fenced code blocks.

---

## Schema Knowledge Base

`api/schema.txt` is the source of truth for AI context. You can enrich it through:
- The browser UI at `http://localhost:5000/` (schema explorer)
- The `/api/descriptions` and `/api/comments` REST endpoints

Descriptions are stored in both `schema.txt` and the `table_descriptions_gen_core` / `column_comments_gen_core` database tables.

---

## Security Notes

Before deploying to production:

- Store secrets in environment variables or a secrets manager — never commit `.env`
- Use a **read-only** database user for the AI query pipeline
- Add password hashing (bcrypt) and JWT/session-based auth
- Restrict CORS to known origins
- Enable HTTPS
- Implement rate limiting on the API

---

## System Requirements

| Component | Minimum |
|-----------|---------|
| Docker | 20.10+ |
| RAM | 4 GB |
| CPU | 2 cores |
| Database | MSSQL 2016+ / PostgreSQL 12+ / SQLite 3+ |

---

## License

See [LICENSE](LICENSE) for details. Google Gemini API usage is subject to [Google's Terms of Service](https://ai.google.dev/terms).
