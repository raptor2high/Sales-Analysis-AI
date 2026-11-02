"""Sales data analysis engine.

Parses CSV rows into typed dataclasses, computes KPIs, chart data,
insights, recommendations, and a simple linear forecast.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class SalesRow:
    date: datetime
    product: str
    revenue: float
    quantity: int
    region: str


@dataclass
class KPIs:
    totalRevenue: float
    totalOrders: int
    growthRate: float
    avgOrderValue: float
    topProduct: str
    topRegion: str


@dataclass
class ChartData:
    labels: List[str]
    data: List[float]


@dataclass
class Charts:
    salesOverTime: ChartData
    revenueByProduct: ChartData
    revenueByRegion: ChartData


@dataclass
class Insight:
    type: str   # "warn" | "good" | "info"
    text: str


@dataclass
class Recommendation:
    icon: str
    text: str


@dataclass
class Forecast:
    nextWeek: float
    nextMonth: float
    growthTrend: str
    anomaly: Optional[str]


@dataclass
class AnalysisResult:
    kpis: KPIs
    charts: Charts
    insights: List[Insight]
    recommendations: List[Recommendation]
    forecast: Forecast
    summary: str

    def to_dict(self) -> dict:
        """Recursively convert to a JSON-serialisable dict."""
        return asdict(self)


# ── Parsing Helpers ──────────────────────────────────────────────────────────

def _parse_number(value: str, *, integer: bool = False) -> Optional[float]:
    """Strip non-numeric chars and convert. Returns None on failure."""
    try:
        cleaned = ''.join(c for c in value if c.isdigit() or c in '.-')
        return int(float(cleaned)) if integer else float(cleaned)
    except (ValueError, IndexError):
        return None


def _parse_date(value: str) -> Optional[datetime]:
    """Parse various date formats into a datetime object. Returns None on failure."""
    if not value or not isinstance(value, str):
        return None

    cleaned = value.strip()
    if not cleaned:
        return None

    # Handle optional time component
    date_part = cleaned.split("T")[0].split(" ")[0].strip()

    # Try ISO format first (standard YYYY-MM-DD)
    try:
        return datetime.fromisoformat(date_part)
    except (ValueError, TypeError):
        pass

    # Common formats to try (DD-MM-YYYY, DD/MM/YYYY, MM-DD-YYYY, etc.)
    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m-%d-%Y",
        "%m/%d/%Y",
        "%d.%m.%Y",
        "%m.%d.%Y",
        "%Y.%m.%d",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%m-%d-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]

    for candidate in (date_part, cleaned):
        for fmt in formats:
            try:
                return datetime.strptime(candidate, fmt)
            except (ValueError, TypeError):
                continue

    return None


def validate_columns(headers: List[str]) -> List[str]:
    """Return list of missing required columns (empty = valid)."""
    required = {"date", "product", "revenue", "quantity", "region"}
    present = {h.strip().lower() for h in headers}
    return sorted(required - present)


def parse_rows(raw_rows: List[Dict[str, str]]) -> Tuple[List[SalesRow], List[str]]:
    """Parse raw CSV dicts into SalesRow objects. Returns (rows, warnings)."""
    rows: List[SalesRow] = []
    warnings: List[str] = []

    for i, raw in enumerate(raw_rows, start=2):
        # Normalise keys once
        cols = {k.strip().lower(): (v.strip() if v else "") for k, v in raw.items()}

        date_s = cols.get("date", "")
        product = cols.get("product", "")
        revenue_s = cols.get("revenue", "")
        quantity_s = cols.get("quantity", "")
        region = cols.get("region", "")

        if not all((date_s, product, revenue_s, quantity_s, region)):
            warnings.append(f"Row {i}: missing values, skipped")
            continue

        # Date
        date = _parse_date(date_s)
        if date is None:
            warnings.append(f'Row {i}: invalid date "{date_s}", skipped')
            continue

        # Numerics
        revenue = _parse_number(revenue_s)
        quantity = _parse_number(quantity_s, integer=True)
        if revenue is None or quantity is None:
            warnings.append(f"Row {i}: invalid numbers, skipped")
            continue

        rows.append(SalesRow(
            date=date,
            product=product,
            revenue=revenue,
            quantity=int(quantity),
            region=region,
        ))

    return rows, warnings


# ── Formatting ───────────────────────────────────────────────────────────────

def _fmt_currency(n: float) -> str:
    if n >= 1_000_000:
        return f"${n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"${n / 1_000:.1f}K"
    return f"${n:.0f}"


# ── Core Analysis ────────────────────────────────────────────────────────────

def analyze(rows: List[SalesRow]) -> AnalysisResult:
    """Run full analysis on parsed sales rows. O(n log n) due to sort."""
    if not rows:
        raise ValueError("No rows to analyze")

    rows.sort(key=lambda r: r.date)
    n = len(rows)

    # ── Single-pass aggregation ──────────────────────────────────────────
    total_revenue = 0.0
    by_week: Dict[str, float] = {}
    by_product: Dict[str, float] = defaultdict(float)
    by_region: Dict[str, float] = defaultdict(float)
    by_day: Dict[str, float] = defaultdict(float)

    for row in rows:
        total_revenue += row.revenue

        # Weekly bucket (week starts Sunday)
        week_start = row.date - timedelta(days=row.date.weekday() + 1)
        week_label = week_start.strftime("%b %d")
        by_week[week_label] = by_week.get(week_label, 0) + row.revenue

        by_product[row.product] += row.revenue
        by_region[row.region] += row.revenue
        by_day[row.date.strftime("%Y-%m-%d")] += row.revenue

    avg_order_value = total_revenue / n

    # ── Growth rate (last 25 % vs previous 25 %) ────────────────────────
    quarter = max(1, n // 4)
    recent_rev = sum(r.revenue for r in rows[-quarter:])
    prev_rev = sum(r.revenue for r in rows[-quarter * 2 : -quarter])
    growth_rate = ((recent_rev - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0.0

    # ── Sorted breakdowns ────────────────────────────────────────────────
    product_ranked = sorted(by_product.items(), key=lambda x: x[1], reverse=True)
    region_ranked = sorted(by_region.items(), key=lambda x: x[1], reverse=True)

    top_product, top_product_rev = product_ranked[0]
    top_product_pct = (top_product_rev / total_revenue * 100) if total_revenue else 0.0
    top_region = region_ranked[0][0]

    worst_region_name, worst_region_rev = region_ranked[-1]
    avg_region_rev = total_revenue / len(region_ranked) if region_ranked else 0.0
    worst_region_gap = (
        (avg_region_rev - worst_region_rev) / avg_region_rev * 100
        if avg_region_rev > 0 else 0.0
    )

    # ── Anomaly detection ────────────────────────────────────────────────
    day_values = list(by_day.values())
    avg_day = sum(day_values) / len(day_values) if day_values else 0.0
    anomaly_label: Optional[str] = None
    for d, v in by_day.items():
        if v > avg_day * 2.5:
            dt = datetime.fromisoformat(d)
            anomaly_label = f"Unusual spike on {dt.strftime('%b %d')} — {v / avg_day:.1f}x above average"
            break

    # ── Forecast (linear extrapolation on weekly data) ───────────────────
    week_data = list(by_week.values())
    wlen = len(week_data)
    slope = 0.0
    if wlen >= 2:
        tail = week_data[-min(4, wlen):]
        slope = (tail[-1] - tail[0]) / (len(tail) - 1)

    last_week = week_data[-1] if wlen else avg_order_value * 10
    next_week = max(0.0, last_week + slope)
    next_month = max(0.0, next_week * 4 + slope * 10)
    trend = "Upward trend" if slope > 0 else "Declining trend" if slope < 0 else "Stable"

    # ── Insights ─────────────────────────────────────────────────────────
    insights: List[Insight] = []

    if growth_rate < -10:
        insights.append(Insight("warn", f"Revenue dropped {abs(growth_rate):.1f}% recently — may signal seasonal dip or competitive pressure."))
    elif growth_rate > 10:
        insights.append(Insight("good", f"Revenue grew {growth_rate:.1f}% in the latest period — strong positive momentum."))
    else:
        insights.append(Insight("info", f"Revenue is relatively stable with {abs(growth_rate):.1f}% change in the latest period."))

    insights.append(Insight("good", f'"{top_product}" is your top product, contributing {top_product_pct:.0f}% of total revenue.'))

    if worst_region_gap > 15:
        insights.append(Insight("warn", f"{worst_region_name} region is underperforming by {worst_region_gap:.0f}% below the regional average."))

    insights.append(Insight("good", f"Average order value is {_fmt_currency(avg_order_value)} across {n:,} orders."))

    if anomaly_label:
        insights.append(Insight("warn", f"Anomaly detected: {anomaly_label}"))

    if len(product_ranked) > 1:
        bot_name, bot_rev = product_ranked[-1]
        bot_pct = (bot_rev / total_revenue * 100) if total_revenue else 0.0
        if bot_pct < 10:
            insights.append(Insight("warn", f'"{bot_name}" contributes only {bot_pct:.1f}% of revenue — consider reviewing its positioning.'))

    # ── Recommendations ──────────────────────────────────────────────────
    recs: List[Recommendation] = [
        Recommendation("bullseye", f'Increase marketing budget for "{top_product}" — it drives {top_product_pct:.0f}% of your revenue with the highest ROI.'),
    ]

    if worst_region_gap > 15:
        recs.append(Recommendation("magnifying-glass", f'Investigate "{worst_region_name}" region — assign a dedicated rep or run a targeted campaign to close the {worst_region_gap:.0f}% performance gap.'))

    if growth_rate < -10:
        recs.append(Recommendation("chart-line", "Revenue is declining — consider running promotions or discounts to re-engage customers and reverse the trend."))
    else:
        recs.append(Recommendation("boxes-stacked", f'Maintain inventory levels for "{top_product}" — demand trend suggests continued strong performance.'))

    if len(product_ranked) > 1:
        recs.append(Recommendation("user-tie", f'Bundle "{top_product}" with lower-performing products to lift overall average order value.'))

    # ── Summary ──────────────────────────────────────────────────────────
    direction = "Growing" if growth_rate >= 0 else "Declining"
    summary = f'Analysis of {n:,} orders totalling {_fmt_currency(total_revenue)}. {direction} at {abs(growth_rate):.1f}% with "{top_product}" leading.'

    # ── Build result ─────────────────────────────────────────────────────
    week_labels = list(by_week.keys())

    return AnalysisResult(
        kpis=KPIs(
            totalRevenue=total_revenue,
            totalOrders=n,
            growthRate=growth_rate,
            avgOrderValue=avg_order_value,
            topProduct=top_product,
            topRegion=top_region,
        ),
        charts=Charts(
            salesOverTime=ChartData(labels=week_labels, data=week_data),
            revenueByProduct=ChartData(
                labels=[p[0] for p in product_ranked],
                data=[p[1] for p in product_ranked],
            ),
            revenueByRegion=ChartData(
                labels=[r[0] for r in region_ranked],
                data=[r[1] for r in region_ranked],
            ),
        ),
        insights=insights,
        recommendations=recs,
        forecast=Forecast(
            nextWeek=next_week,
            nextMonth=next_month,
            growthTrend=trend,
            anomaly=anomaly_label,
        ),
        summary=summary,
    )
