"""API route handlers for the Sales Analysis AI backend."""

import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from src.analyzer import validate_columns, parse_rows, analyze
from src.logger import logger

api_bp = Blueprint('api', __name__)

# ── Lazy-initialised AI client (singleton) ───────────────────────────────────
_ai_client = None


def _get_ai_client():
    """Return a cached OpenAI-compatible client pointed at Groq."""
    global _ai_client
    if _ai_client is None:
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return None
        from openai import OpenAI
        _ai_client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    return _ai_client


# ── Health ───────────────────────────────────────────────────────────────────

@api_bp.route('/healthz', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})


# ── CSV Analysis ─────────────────────────────────────────────────────────────

@api_bp.route('/analyze', methods=['POST'])
def analyze_endpoint():
    try:
        # --- File validation ---
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded. Please attach a CSV file."}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({"error": "No file selected. Please choose a CSV file."}), 400

        filename = secure_filename(file.filename)
        if not filename or not filename.lower().endswith('.csv'):
            return jsonify({"error": "Invalid file type. Please upload a .csv file."}), 400

        file_content = file.read().decode('utf-8')
        if not file_content.strip():
            return jsonify({"error": "The uploaded file is empty."}), 400

        # --- CSV parsing ---
        import csv, io
        try:
            raw_rows = list(csv.DictReader(io.StringIO(file_content), skipinitialspace=True))
        except Exception as e:
            logger.error(f"CSV parsing error: {e}")
            return jsonify({"error": "Failed to parse CSV file. Please check the format."}), 400

        if not raw_rows:
            return jsonify({"error": "The CSV file has no data rows."}), 400

        # --- Column validation ---
        headers = list(raw_rows[0].keys())
        missing = validate_columns(headers)
        if missing:
            return jsonify({
                "error": f"Invalid file format. Missing required columns: {', '.join(missing)}.",
                "hint": "Required columns: date, product, revenue, quantity, region",
                "missingColumns": missing,
            }), 400

        # --- Row parsing ---
        rows, warnings = parse_rows(raw_rows)
        if not rows:
            hint = f"Detail: {warnings[0]}" if warnings else "Supported date formats include YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY."
            return jsonify({
                "error": "No valid data rows found after cleaning. Check your file for invalid dates or numbers.",
                "hint": hint,
                "warnings": warnings,
            }), 400

        if len(rows) < 5:
            hint = f"Detail: {warnings[0]}" if warnings else "Upload at least 5 rows with date, product, revenue, quantity, region."
            return jsonify({
                "error": f"Dataset too small — only {len(rows)} valid row(s) found. Please upload at least 5 rows for meaningful analysis.",
                "hint": hint,
                "warnings": warnings,
            }), 400

        # --- Analysis ---
        result = analyze(rows)

        return jsonify({
            "success": True,
            "data": result.to_dict(),
            "warnings": warnings,
            "rowCount": len(rows),
        })

    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        return jsonify({"error": "Something went wrong during analysis. Please try again."}), 500


# ── AI Chat ──────────────────────────────────────────────────────────────────

@api_bp.route('/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON body received."}), 400

        message = (data.get('message') or '').strip()
        if not message:
            return jsonify({"error": "Message is required."}), 400

        # Build context from analysis data
        ctx = data.get('context', {})
        kpis = ctx.get('kpis', {})
        forecast = ctx.get('forecast', {})
        insight_lines = '\n'.join(f"- {i.get('text', '')}" for i in ctx.get('insights', [])[:5])
        rec_lines = '\n'.join(f"- {r.get('text', '')}" for r in ctx.get('recommendations', [])[:4])

        system_prompt = f"""You are a sharp, concise sales data analyst AI embedded inside a dashboard.
The user has uploaded a CSV. Here is the full analysis:

KPIs:
- Total Revenue: ${kpis.get('totalRevenue', 0):,.0f}
- Total Orders: {kpis.get('totalOrders', 0)}
- Growth Rate: {kpis.get('growthRate', 0):.1f}%
- Avg Order Value: ${kpis.get('avgOrderValue', 0):,.0f}
- Top Product: {kpis.get('topProduct', 'N/A')}
- Top Region: {kpis.get('topRegion', 'N/A')}

Summary: {ctx.get('summary', '')}

Insights:
{insight_lines}

Recommendations:
{rec_lines}

Forecast:
- Next Week: ${forecast.get('nextWeek', 0):,.0f}
- Next Month: ${forecast.get('nextMonth', 0):,.0f}
- Trend: {forecast.get('growthTrend', '')}
- Anomaly: {forecast.get('anomaly', 'None')}

Answer the user's question using only this data. Be specific, cite numbers, and keep responses under 3 sentences."""

        client = _get_ai_client()
        if client is None:
            return jsonify({"error": "Groq API key not configured."}), 500

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            max_tokens=200,
            temperature=0.4,
        )

        reply = response.choices[0].message.content.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({"error": "Chat failed. Please try again."}), 500
