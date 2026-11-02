# Python API Server Backend

A Flask-based Python backend for the Sales Analysis AI application.

## Installation

```bash
pip install -r requirements.txt
```

## Development

```bash
python src/app.py
```

Server will run on `http://localhost:3001`

## Environment Variables

- `PORT` (default: 3001) - Server port
- `NODE_ENV` (default: development) - Set to "production" for production mode
- `LOG_LEVEL` (default: INFO) - Logging level (DEBUG, INFO, WARNING, ERROR)

## API Endpoints

### Health Check
```
GET /api/healthz
```

### Analyze Sales Data
```
POST /api/analyze
Content-Type: multipart/form-data

file: <CSV file>
```

**Required CSV columns:**
- date
- product
- revenue
- quantity
- region

## Architecture

- **src/app.py** - Flask application factory and configuration
- **src/routes.py** - API route handlers
- **src/analyzer.py** - Core sales analysis logic
- **src/logger.py** - Logging configuration
- **src/app.py** - Application entry point

## Features

- CSV file upload and validation
- Comprehensive sales data analysis
- KPI calculation
- Chart data generation
- Anomaly detection
- Revenue forecasting
- Automated insights and recommendations
- Full CORS support

## Notes

This is a direct port from the TypeScript Express backend to Python Flask, maintaining 100% functional parity with the original implementation.
