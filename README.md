# Sales Analysis AI

> Turn your sales data into clear business decisions in seconds.

A sales analytics dashboard that accepts CSV uploads, performs comprehensive analysis (KPIs, charts, insights, recommendations, forecasting), and includes an AI-powered Q&A chat.

## Architecture

```
Sales-Analysis-AI/
├── artifacts/
│   ├── sales-ai/               # Frontend (Vanilla HTML + Chart.js)
│   │   ├── index.html          # Complete dashboard UI
│   │   ├── public/             # Static assets (logo, sample CSV)
│   │   ├── vite.config.ts      # Dev server + API proxy
│   │   └── package.json
│   │
│   └── api-server-python/      # Backend (Python / Django)
│       ├── src/
│       │   ├── settings.py     # Django settings
│       │   ├── urls.py         # API and dashboard URLs
│       │   ├── routes.py       # API views
│       │   ├── analyzer.py     # Sales analysis engine
│       │   └── logger.py       # Logging configuration
│       ├── manage.py           # Development and test commands
│       ├── wsgi.py             # Production WSGI entry point
│       ├── requirements.txt
│       └── .env.example
│
├── pnpm-workspace.yaml
└── package.json
```

## Quick Start

### 1. Backend

```bash
cd artifacts/api-server-python
python -m pip install -r requirements.txt
python manage.py runserver 0.0.0.0:3001
# → Server starts on http://localhost:3001
```

### 2. Frontend

```bash
# From project root
pnpm install
pnpm dev
# → Vite dev server on http://localhost:5173 (proxies /api to :3001)
```

### 3. Upload & Analyze

Open `http://localhost:5173`, upload a CSV with these columns:

| date | product | revenue | quantity | region |
|------|---------|---------|----------|--------|
| 2024-01-15 | Widget A | 1500.00 | 25 | North |

Or download the sample CSV from the landing page.

You can also open `http://localhost:3001` to use the dashboard directly through Django.

## Features

- **KPI Dashboard** — Total revenue, orders, growth rate, average order value
- **Interactive Charts** — Sales over time, revenue by product (doughnut), revenue by region (bar)
- **AI Insights** — Automated trend detection, anomaly alerts, underperformance warnings
- **Recommendations** — Actionable business suggestions based on data patterns
- **Forecasting** — Next-week and next-month revenue projections
- **AI Chat** — Ask natural-language questions about your data (powered by Groq)

## AI Chat Setup (Optional)

The chat feature uses the Groq API (free tier available):

```bash
cd artifacts/api-server-python
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your-key-here
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/healthz` | Health check |
| POST | `/api/analyze` | Upload CSV, returns full analysis |
| POST | `/api/chat` | AI Q&A about analysis results |

## Tech Stack

- **Frontend**: Vanilla HTML/CSS/JS, Chart.js, Tailwind (CDN), Font Awesome
- **Backend**: Django 5.2 LTS, Python 3.10–3.14
- **AI**: Groq API (GPT-OSS 20B) via OpenAI-compatible client
- **Dev Server**: Vite (proxy + hot reload)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3001` | Port used by the documented Gunicorn command |
| `APP_ENV` | `production` | Set to `development` for local Django debug pages |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `DJANGO_ALLOWED_HOSTS` | Localhost and the managed Render hostname, when present | Add comma-separated hostnames for other domains or local network access |
| `DJANGO_SECRET_KEY` | Random per process | Set a stable secret in production |
| `GROQ_API_KEY` | — | Required for AI chat feature |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Groq chat model |

Production startup and backend tests are documented in the [backend README](artifacts/api-server-python/README.md).

## License

MIT
