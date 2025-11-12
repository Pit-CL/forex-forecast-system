# PDF Reporting Quick Reference Guide

**Date:** 2025-11-12
**Purpose:** Quick reference for developers working with PDF reporting system

---

## Quick Setup

### Install System Dependencies (Ubuntu/Debian)

```bash
sudo apt-get update && sudo apt-get install -y \
    libpangocairo-1.0-0 \
    libcairo2 \
    libffi8 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info
```

### Install System Dependencies (macOS)

```bash
brew install cairo pango gdk-pixbuf libffi
```

### Install Python Dependencies

```bash
pip install matplotlib>=3.9 seaborn>=0.13 pandas>=2.2
pip install weasyprint>=62.3 cairocffi>=1.7 jinja2>=3.1 markdown>=3.6
```

---

## Usage Examples

### Generate 7-Day Forecast Report

```python
from forex_core.reporting import ReportBuilder, ReportConfig

config = ReportConfig(
    horizon="7d",
    historical_window=30,  # days
    forecast_points=7,
    time_unit="days",
    trend_threshold=0.5,
    pdf_title="USD/CLP 7-Day Forecast"
)

builder = ReportBuilder(config)
report = builder.build(bundle, forecast, technicals, artifacts)

print(f"PDF saved to: {report.pdf_path}")
print(f"Charts: {len(report.chart_paths)}")
```

### Generate 12-Month Forecast Report

```python
config = ReportConfig(
    horizon="12m",
    historical_window=24,  # months
    forecast_points=12,
    time_unit="months",
    trend_threshold=1.5,
    pdf_title="USD/CLP 12-Month Forecast"
)

builder = ReportBuilder(config)
report = builder.build(bundle, forecast, technicals, artifacts)
```

### Generate Importer Macro Report

```python
config = ReportConfig(
    horizon="monthly",
    historical_window=36,
    forecast_points=6,
    time_unit="months",
    include_cover=True,
    include_toc=True,
    include_page_numbers=True,
    pdf_title="Informe Mensual Entorno Importador"
)

builder = ReportBuilder(config)
report = builder.build(bundle, forecast, technicals, artifacts)
```

### Send Report via Email

```python
from forex_core.notifications import EmailService

email_service = EmailService(settings)
email_service.send_report(
    subject="USD/CLP Forecast - November 2025",
    body="Attached is the latest forecast report.",
    attachments=[report.pdf_path]
)
```

---

## Chart Generation

### Generate Standard Forecast Charts

```python
from forex_core.reporting import ChartGenerator, ChartConfig

chart_config = ChartConfig(
    horizon="7d",
    dpi=200,
    size=(10, 5),
    colors={
        "historical": "#1f77b4",
        "forecast": "#d62728",
        "ci80": "#ff9896",
        "ci95": "#c5b0d5"
    }
)

chart_gen = ChartGenerator(chart_config)
charts = chart_gen.generate(bundle, forecast)
```

### Generate Custom Chart

```python
import matplotlib.pyplot as plt
from pathlib import Path

def generate_custom_chart(data, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(data["date"], data["value"])
    ax.set_title("Custom Chart")
    ax.grid(True, alpha=0.3)

    chart_path = output_dir / "custom_chart.png"
    fig.savefig(chart_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    return chart_path
```

---

## Template Customization

### Modify HTML Template

Edit: `forex_core/reporting/templates/forecast.html.j2`

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: "Helvetica Neue", Arial, sans-serif;
            margin: 24px;
            color: #1b1b1b;
        }
        h1 { color: #0a1f44; font-size: 24px; }
        h2 { color: #0a1f44; font-size: 18px; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 16px;
        }
        th, td {
            border: 1px solid #d0d0d0;
            padding: 6px 8px;
            font-size: 12px;
        }
        th { background-color: #eef2f7; }
        img.chart {
            width: 100%;
            margin: 12px 0;
            border: 1px solid #ddd;
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <div class="meta">
        Generado: {{ generated_at }} | Zona horaria: {{ timezone }}
    </div>
    {% for chart in charts %}
        <img src="{{ chart }}" class="chart" alt="chart">
    {% endfor %}
    <div>{{ body | safe }}</div>
</body>
</html>
```

---

## Section Development

### Create New Section

```python
from forex_core.reporting.sections import Section, SectionContent

class CustomSection(Section):
    def generate(self, bundle: DataBundle, forecast: ForecastPackage) -> SectionContent:
        # Extract data
        spot = bundle.indicators["usdclp_spot"].value
        forecast_mean = forecast.series[-1].mean

        # Build content
        paragraphs = [
            f"Current spot rate: {spot:.2f} CLP/USD",
            f"Forecast: {forecast_mean:.2f} CLP/USD"
        ]

        # Build table
        table_data = {
            "Metric": ["Spot", "Forecast", "Change"],
            "Value": [spot, forecast_mean, forecast_mean - spot]
        }
        table = pd.DataFrame(table_data)

        return SectionContent(
            title="Custom Analysis",
            paragraphs=paragraphs,
            tables=[table]
        )
```

---

## Validation

### Validate PDF

```python
from forex_core.reporting import validate_pdf

result = validate_pdf(pdf_path)
if result.success:
    print("PDF is valid")
else:
    print(f"PDF validation failed: {result.error}")
```

### Validate Chart

```python
from forex_core.reporting import validate_chart

if validate_chart(chart_path):
    print("Chart is valid")
else:
    print("Chart validation failed")
```

---

## Error Handling

### Handle PDF Generation Failures

```python
from forex_core.reporting import ReportBuilder, WeasyPrintError

builder = ReportBuilder(config)

try:
    report = builder.build(bundle, forecast, technicals, artifacts)
except WeasyPrintError as e:
    logger.error(f"WeasyPrint failed: {e}")
    # Fallback to markdown
    report = builder.build(bundle, forecast, technicals, artifacts, skip_pdf=True)
except Exception as e:
    logger.critical(f"Report generation failed: {e}")
    raise
```

### Handle Missing Charts

```python
from forex_core.reporting import ChartGenerator

try:
    charts = chart_gen.generate(bundle, forecast)
except Exception as e:
    logger.error(f"Chart generation failed: {e}")
    # Use empty list or default charts
    charts = []
```

---

## Testing

### Unit Test Chart Generation

```python
def test_chart_generation():
    config = ChartConfig(horizon="7d", dpi=200, size=(10, 5))
    chart_gen = ChartGenerator(config)

    charts = chart_gen.generate(test_bundle, test_forecast)

    assert len(charts) == 2
    for chart in charts:
        assert chart.exists()
        assert chart.stat().st_size > 10_000  # >10KB
```

### Unit Test PDF Generation

```python
def test_pdf_generation():
    renderer = WeasyPrintRenderer(config)
    html = "<h1>Test Report</h1><p>Español: ñ, á, é</p>"

    pdf_path = renderer.write_pdf(html)

    assert pdf_path.exists()
    assert pdf_path.suffix == ".pdf"
    assert 50_000 < pdf_path.stat().st_size < 5_000_000
```

### Integration Test Full Report

```python
def test_full_report():
    config = ReportConfig(horizon="7d")
    builder = ReportBuilder(config)

    report = builder.build(bundle, forecast, technicals, artifacts)

    assert report.pdf_path.exists()
    assert len(report.chart_paths) >= 2

    validation = validate_pdf(report.pdf_path)
    assert validation.success
```

---

## Troubleshooting

### Issue: WeasyPrint Import Error

**Error:**
```
ModuleNotFoundError: No module named 'weasyprint'
```

**Solution:**
```bash
pip install weasyprint cairocffi
# Also install system dependencies (see Quick Setup above)
```

---

### Issue: Cairo Library Not Found

**Error:**
```
OSError: cannot load library 'gobject-2.0-0'
```

**Solution (Ubuntu/Debian):**
```bash
sudo apt-get install libpangocairo-1.0-0 libcairo2
```

**Solution (macOS):**
```bash
brew install cairo pango
```

---

### Issue: Spanish Characters Display as Boxes

**Problem:** ñ, á, é, í, ó, ú show as �

**Solution:**
- Ensure HTML template has `<meta charset="utf-8">`
- Use UTF-8 encoding when writing files
- Test with web-safe fonts (Helvetica, Arial)

---

### Issue: Charts Not Appearing in PDF

**Problem:** PDF generated but charts missing

**Solution:**
- Check chart paths are valid
- Verify base64 encoding is correct
- Ensure charts are generated before PDF
- Check chart file sizes (should be >10KB)

---

### Issue: PDF File Too Large

**Problem:** PDF exceeds 5 MB

**Solution:**
- Reduce chart DPI (from 200 to 150)
- Reduce chart size (from 10x5 to 8x4)
- Compress charts (use PNG optimization)
- Remove unnecessary charts

---

### Issue: PDF Generation Times Out

**Problem:** PDF takes >30 seconds to generate

**Solution:**
- Profile chart generation (matplotlib can be slow)
- Close figures immediately with `plt.close(fig)`
- Generate charts in parallel (if possible)
- Use faster chart backend (Agg)

---

## Configuration Options

### ReportConfig Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `horizon` | str | Report horizon | "7d", "12m", "monthly" |
| `historical_window` | int | Historical data window | 30 (days), 24 (months) |
| `forecast_points` | int | Number of forecast points | 7, 12, 6 |
| `time_unit` | str | Time unit | "days", "months" |
| `trend_threshold` | float | Trend classification threshold | 0.5, 1.5 |
| `word_limits` | dict | Word limits per section | {"interpretation": 300} |
| `chart_specs` | list | Chart specifications | See ChartConfig |
| `include_cover` | bool | Include cover page | True, False |
| `include_toc` | bool | Include table of contents | True, False |
| `include_page_numbers` | bool | Include page numbers | True, False |
| `pdf_title` | str | PDF metadata title | "Forecast Report" |
| `pdf_author` | str | PDF metadata author | "Forecast Team" |

### ChartConfig Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `horizon` | str | Chart horizon | "7d", "12m" |
| `dpi` | int | Chart DPI | 200 |
| `size` | tuple | Chart size (inches) | (10, 5) |
| `colors` | dict | Color palette | {"historical": "#1f77b4"} |
| `elements` | list | Chart elements | ["line", "ci80", "ci95"] |

---

## Best Practices

### Chart Generation

1. Always close matplotlib figures: `plt.close(fig)`
2. Use DPI=200 for print quality
3. Use PNG format (not JPEG)
4. Use seaborn styling for consistency
5. Add grid for readability: `ax.grid(True, alpha=0.3)`
6. Use descriptive titles and labels
7. Test with real data

### PDF Generation

1. Validate inputs before generating
2. Handle WeasyPrint errors gracefully
3. Provide fallback to markdown
4. Validate output PDF
5. Check file size
6. Test with multiple PDF readers
7. Use UTF-8 encoding consistently

### Section Development

1. Keep sections focused (single responsibility)
2. Use word limits to prevent bloat
3. Format tables consistently
4. Add descriptive captions
5. Test with edge cases (empty data, missing fields)
6. Document assumptions
7. Cite sources

### Testing

1. Test with real data from all horizons
2. Test edge cases (empty data, outliers)
3. Test Spanish characters
4. Test large reports (memory usage)
5. Test error conditions
6. Use visual regression tests
7. Test on multiple platforms

---

## Useful Code Snippets

### Format Number in Spanish Locale

```python
def format_number_es(value: float, decimals: int = 2) -> str:
    """Format number with Spanish separators."""
    formatted = f"{value:,.{decimals}f}"
    # Spanish uses . for thousands, , for decimals
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted

# Example: 1234567.89 -> "1.234.567,89"
```

### Format Date in Spanish

```python
from datetime import datetime

SPANISH_MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

SPANISH_DAYS = [
    "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"
]

def format_date_es(dt: datetime) -> str:
    """Format date in Spanish: '15 de noviembre de 2025'"""
    month = SPANISH_MONTHS[dt.month - 1]
    return f"{dt.day} de {month} de {dt.year}"

def weekday_es(dt: datetime) -> str:
    """Get Spanish weekday name."""
    return SPANISH_DAYS[dt.weekday()]
```

### Generate Base64 Chart

```python
import base64
from pathlib import Path

def chart_to_base64(chart_path: Path) -> str:
    """Convert chart to base64 data URI."""
    with chart_path.open("rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"
```

### Enforce Word Limit

```python
def enforce_word_limit(text: str, limit: int) -> str:
    """Truncate text to word limit."""
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]) + "..."
```

---

## Common Patterns

### Pattern: Section with Dynamic Table

```python
def build_forecast_table(forecast: ForecastPackage) -> pd.DataFrame:
    rows = []
    for point in forecast.series:
        rows.append({
            "Fecha": point.date.strftime("%Y-%m-%d"),
            "Media": round(point.mean, 2),
            "IC 80% Inf": round(point.ci80_low, 2),
            "IC 80% Sup": round(point.ci80_high, 2)
        })
    return pd.DataFrame(rows)
```

### Pattern: Section with Conditional Content

```python
def build_macro_section(bundle: DataBundle) -> SectionContent:
    paragraphs = []

    if bundle.macro_events:
        events_text = f"Hay {len(bundle.macro_events)} eventos importantes."
        paragraphs.append(events_text)
    else:
        paragraphs.append("No hay eventos macro relevantes.")

    return SectionContent(title="Macro Events", paragraphs=paragraphs)
```

### Pattern: Weighted Driver Ranking

```python
def rank_drivers(drivers: List[Dict]) -> List[Dict]:
    """Rank drivers by score and calculate weights."""
    sorted_drivers = sorted(drivers, key=lambda x: x["score"], reverse=True)
    total_score = sum(d["score"] for d in sorted_drivers) or 1

    for driver in sorted_drivers:
        driver["weight"] = driver["score"] / total_score * 100

    return sorted_drivers[:5]  # Top 5
```

---

## File Locations

### Source Files (Legacy)

- **7d:** `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/deployment/7d/src/usdclp_forecaster/report/`
- **12m:** `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/deployment/12m/src/usdclp_forecaster_12m/report/`
- **Importer:** `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/importer_macro_report/monthly_import_report/`

### Target Files (Unified)

- **Core:** `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/`
- **Sections:** `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/sections/`
- **Templates:** `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/templates/`
- **Email:** `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/notifications/`

---

## Additional Resources

- [WeasyPrint Documentation](https://weasyprint.readthedocs.io/)
- [Matplotlib Documentation](https://matplotlib.org/stable/index.html)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [ReportLab Documentation](https://www.reportlab.com/docs/reportlab-userguide.pdf)

---

**Last Updated:** 2025-11-12
