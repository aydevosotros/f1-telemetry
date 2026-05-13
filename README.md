# F1 25 Telemetry

Local web app for capturing, storing, replaying, and comparing telemetry from EA Sports F1 25.

## Stack

- Python 3.12, FastAPI, SQLAlchemy, Alembic, WebSockets
- React, Vite, TypeScript
- PostgreSQL
- Docker Compose

## Run Locally

Create a local environment file:

```bash
cp .env.example .env
```

Change `POSTGRES_PASSWORD` in `.env` before running anywhere beyond local development.

```bash
docker compose up --build
```

Then open:

- Web UI: http://localhost:5173
- API docs: http://localhost:8010/docs

Apply database migrations from another shell:

```bash
docker compose run --rm api uv run alembic upgrade head
```

## F1 25 Setup

In the game telemetry settings:

- Enable UDP telemetry.
- Use packet format `2025`.
- Send to the IP address of the machine running this app.
- Use UDP port `20777` unless you changed `UDP_PORT`.

## Development

Backend:

```bash
cd api
uv sync
uv run alembic upgrade head
uv run uvicorn f1_telemetry.main:app --reload
uv run pytest
```

Frontend:

```bash
cd web
npm install
npm run dev
```
