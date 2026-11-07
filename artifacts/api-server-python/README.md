# Django API server

Run these commands from `artifacts/api-server-python` with Python 3.10–3.14.

```bash
python -m pip install -r requirements.txt
python manage.py runserver 0.0.0.0:3001
```

Django serves the dashboard at `http://localhost:3001`. The Vite development server also works with this backend on port 3001. The app keeps its state in the browser and has no database setup or migrations.

For optional AI chat, copy `.env.example` to `.env` and set `GROQ_API_KEY`. Set `APP_ENV=development` to enable local debug pages.

## API

| Method | Path | Request |
|--------|------|---------|
| GET | `/api/healthz` | Health check |
| POST | `/api/analyze` | Multipart field `file` containing a CSV with date, product, revenue, quantity, and region columns |
| POST | `/api/chat` | JSON with `message`, analysis `context`, and optional conversation `history` |

## Production

Set `APP_ENV=production`, provide a stable `DJANGO_SECRET_KEY`, and set `DJANGO_ALLOWED_HOSTS` to a comma-separated list of deployment hostnames. Loopback and the hostname supplied by Render in `RENDER_EXTERNAL_HOSTNAME` are included automatically.

Run Gunicorn from this directory on the production host.

```bash
gunicorn --bind "0.0.0.0:${PORT:-3001}" wsgi:application
```

Existing Gunicorn commands targeting `wsgi:app` are also supported. Deploy the sibling `sales-ai` directory alongside the backend so the dashboard and sample CSV remain available.

## Tests

```bash
python manage.py check
python manage.py test
```
