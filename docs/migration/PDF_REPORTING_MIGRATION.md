# PDF Reporting and Chart Generation Migration

**Date:** 2025-11-12
**Status:** CRITICAL - Primary System Output
**Priority:** HIGH
**Author:** Migration Analysis Agent

---

## Executive Summary

This document details the migration of PDF reporting and chart generation systems from three legacy services (7d forecaster, 12m forecaster, and importer macro report) into the consolidated `forex_core` library. PDF generation is the **primary output** of the system and must work flawlessly.

### Key Findings

1. **Two Different PDF Libraries Used:**
   - **7d/12m Forecasters:** WeasyPrint (HTML-to-PDF, requires Cairo/Pango)
   - **Importer Report:** ReportLab (programmatic PDF generation)

2. **7d vs 12m Differences:** Minimal - mostly text labels (days vs months)

3. **Importer Report Differences:** Significantly different architecture, richer report structure

---

## Current System Architecture

### 1. Seven-Day Forecaster (7d)

**Location:** `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/deployment/7d/src/usdclp_forecaster/`

#### Files:

**`report/charting.py` (69 lines)**
- Generates 2 charts using matplotlib/seaborn
- Chart 1: Historical 30d + 7d forecast with confidence bands
- Chart 2: Forecast confidence intervals only
- Base64 encoding for HTML embedding
- Fixed DPI: 200
- Chart size: 10x5 and 10x4 inches

**`report/pdf_renderer.py` (53 lines)**
- Uses WeasyPrint for HTML-to-PDF conversion
- Jinja2 templating (`report.html.j2`)
- Markdown-to-HTML conversion for body content
- Spanish character support
- Error handling for missing WeasyPrint dependencies

**`report/builder.py` (327 lines)**
- Main orchestrator for report generation
- Sections:
  1. Projection table (7 days)
  2. Executive interpretation
  3. Key drivers (top 5 by weighted score)
  4. Quantitative factors
  5. Macro calendar (next 7 days)
  6. News (last 48h)
  7. Technical analysis
  8. Uncertainty statement
  9. Tail risks
  10. Methodology
  11. Conclusion
  12. Sources
- Word limits: interpretation (300), conclusion (150)
- Markdown backup option (skip_pdf flag)

**`report/templates/report.html.j2` (25 lines)**
- Simple HTML template with embedded CSS
- Spanish language metadata
- Base64 chart embedding
- Responsive table styling

**`analysis/report_sections.py` (1 line)**
- Empty file (legacy)

**`emailer.py` (36 lines)**
- SMTP email delivery via Gmail
- PDF attachment support
- SSL/TLS connection

---

### 2. Twelve-Month Forecaster (12m)

**Location:** `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/deployment/12m/src/usdclp_forecaster_12m/`

#### Files:

**`report/charting.py` (69 lines)**
- **Difference:** Historical window = 24 months (resampled to month-end)
- **Difference:** Chart titles say "12m" instead of "7d"
- Otherwise identical to 7d

**`report/builder.py` (321 lines)**
- **Differences:**
  - Projection table shows months (not day-of-week)
  - Move thresholds: >1.5% (not >0.5%) for trend classification
  - Interpretation mentions "12M" horizon
  - Macro calendar says "próximas 4 semanas" not "próximos 7 días"
  - Conclusion mentions "T1 y T4" (quarters)
- Otherwise identical to 7d

**`report/pdf_renderer.py`** - Identical to 7d
**`report/templates/report.html.j2`** - Identical to 7d
**`emailer.py`** - Identical to 7d

---

### 3. Importer Macro Report (Monthly)

**Location:** `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/importer_macro_report/monthly_import_report/`

#### Files:

**`visuals.py` (216 lines)**
- **Much more sophisticated chart generation:**
  1. CLP/USD observed + BCCh projection
  2. Freight + port congestion
  3. IPC YoY vs TPM
  4. Import volume
  5. Retail confidence (CNC)
  6. Copper vs CLP/USD scatter plot with linear regression
  7. Risk map (horizontal bar chart)
  8. FX forecast (SARIMAX) vs actual
  9. Restaurant sales forecast vs actual
- Matplotlib configuration handling (`MPLCONFIGDIR`)
- Chart size: 6x3.4 inches
- DPI: 200
- Returns `List[ChartSpec]` data models

**`pdf_builder.py` (241 lines)**
- **Uses ReportLab (not WeasyPrint!)**
- Programmatic PDF generation (not HTML-to-PDF)
- Features:
  - Custom numbered canvas (page X of Y)
  - Cover page with Spanish date formatting
  - Table of contents
  - Section-based structure
  - Advanced table styling (colored headers, row backgrounds)
  - Image embedding
  - Caption support
  - A4 page size with margins
  - PDF metadata (title, author)

**`report_sections.py` (321 lines)**
- **Much more comprehensive than 7d/12m:**
  - Executive summary
  - Introduction and methodology
  - Macro and financial environment
  - Demand, logistics, costs
  - Critical variable impacts
  - Micro environment analysis
  - Restaurant/food service industry
  - PESTEL analysis
  - Porter's 5 Forces
  - 1/3/5 year scenarios
  - Quantitative projections (SARIMAX, VAR, Gradient Boosting, Random Forest)
  - Conclusions and recommendations
  - Sources and appendices

**`email_client.py` (69 lines)**
- More robust than 7d/12m emailer:
  - MIME type detection
  - TLS vs SSL support
  - Configurable SMTP settings
  - Better error handling

---

## Dependency Analysis

### WeasyPrint Dependencies (7d/12m)

**System Libraries (Ubuntu/Debian):**
```bash
libpangocairo-1.0-0
libcairo2
libffi8
libgdk-pixbuf-2.0-0
shared-mime-info
```

**Python Requirements:**
```
weasyprint>=62.3
cairocffi>=1.7
```

**Dockerfile snippet:**
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpangocairo-1.0-0 \
        libcairo2 \
        libffi8 \
        libgdk-pixbuf-2.0-0 \
        shared-mime-info
```

### ReportLab Dependencies (Importer)

**Python Requirements:**
```
reportlab>=4.1
```

**No system dependencies required** (pure Python)

---

## Critical Requirements Validation

### 1. Spanish Character Support

**WeasyPrint Approach (7d/12m):**
- Uses `<meta charset="utf-8">` in HTML template
- Helvetica Neue font family with fallback to Arial
- Tested with: á, é, í, ó, ú, ñ, ¿, ¡

**ReportLab Approach (Importer):**
- Uses Helvetica font (built-in Type1 font)
- Supports Latin-1 character set
- Paragraph styles with proper encoding

**Validation:** Both approaches support Spanish characters correctly.

---

### 2. Chart Embedding

**WeasyPrint Approach:**
```python
def image_to_base64(path: Path) -> str:
    with path.open("rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"
```
- Charts embedded as base64 data URIs
- No external file dependencies in PDF

**ReportLab Approach:**
```python
img = Image(str(chart.path), width=width, height=width * 0.6)
img.hAlign = "CENTER"
```
- Charts embedded from file paths
- PDF includes image data

**Validation:** Both approaches work. WeasyPrint method is more portable.

---

### 3. Multi-Page PDF Support

**WeasyPrint:**
- Automatic pagination based on HTML content
- CSS page break controls available

**ReportLab:**
- Manual `PageBreak()` insertion
- Custom canvas for page numbering
- Table `repeatRows` for multi-page tables

**Validation:** Both handle multi-page PDFs correctly.

---

### 4. PDF Metadata

**WeasyPrint:**
- Limited metadata support
- Can be enhanced via CSS `@page` rules

**ReportLab:**
```python
doc = SimpleDocTemplate(
    str(output_path),
    title=config.report_title,
    author="Equipo de Análisis Estratégico",
)
```
- Full metadata support (title, author, subject, keywords)

**Validation:** ReportLab has better metadata support.

---

### 5. File Size

**Typical Sizes:**
- 7d/12m PDFs: ~150-300 KB (2 charts, ~8 pages)
- Importer PDFs: ~500 KB - 1.5 MB (9 charts, ~15 pages)

**Validation:** All within acceptable range (>50KB, <5MB).

---

## Migration Strategy

### Phase 1: Core Infrastructure

**Target Structure:**
```
forex_core/
├── reporting/
│   ├── __init__.py
│   ├── charting.py          # Unified chart generation
│   ├── pdf_weasy.py         # WeasyPrint renderer
│   ├── pdf_reportlab.py     # ReportLab renderer (optional)
│   ├── builder.py           # Horizon-agnostic builder
│   ├── sections/
│   │   ├── __init__.py
│   │   ├── executive.py     # Executive summary
│   │   ├── technical.py     # Technical analysis
│   │   ├── fundamental.py   # Fundamental analysis
│   │   └── forecast.py      # Forecast tables
│   └── templates/
│       ├── base.html.j2     # Base HTML template
│       ├── forecast.html.j2 # Forecast-specific
│       └── macro.html.j2    # Macro report-specific
├── notifications/
│   ├── __init__.py
│   └── email.py             # Unified email service
```

### Phase 2: Parameterize by Horizon

**Unified Builder Configuration:**
```python
@dataclass
class ReportConfig:
    horizon: str  # "7d", "12m", "monthly"
    historical_window: int  # 30, 24, 36 (days/months)
    forecast_points: int  # 7, 12, 6
    time_unit: str  # "days", "months"
    trend_threshold: float  # 0.5, 1.5
    word_limits: Dict[str, int]  # interpretation: 300, etc.
    chart_specs: List[ChartSpec]
```

### Phase 3: Enhanced Features

1. **Add validation for generated PDFs:**
   ```python
   def validate_pdf(path: Path) -> ValidationResult:
       """Validate PDF can be opened and has expected structure."""
       if not path.exists():
           return ValidationResult(success=False, error="File not found")
       if path.stat().st_size < 50_000:
           return ValidationResult(success=False, error="File too small")
       if path.stat().st_size > 5_000_000:
           return ValidationResult(success=False, error="File too large")
       # Try opening with PyPDF2 or similar
       return ValidationResult(success=True)
   ```

2. **Add chart quality validation:**
   ```python
   def validate_chart(path: Path) -> bool:
       """Ensure chart is readable and not corrupted."""
       from PIL import Image
       try:
           img = Image.open(path)
           width, height = img.size
           return width >= 600 and height >= 300
       except Exception:
           return False
   ```

3. **Enhanced error handling:**
   ```python
   try:
       pdf_path = renderer.write_pdf(html_body)
   except WeasyPrintError as e:
       logger.error(f"WeasyPrint failed: {e}")
       # Fallback: write markdown backup
       return report_backup(markdown_body)
   except Exception as e:
       logger.critical(f"Unexpected PDF error: {e}")
       raise
   ```

---

## Files to Migrate

### 1. Charting Module

**Source Files:**
- `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/deployment/7d/src/usdclp_forecaster/report/charting.py`
- `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/deployment/12m/src/usdclp_forecaster_12m/report/charting.py`
- `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/importer_macro_report/monthly_import_report/visuals.py`

**Target:**
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/charting.py`

**Consolidation Strategy:**
- Create `ChartConfig` dataclass for parameterization
- Unify chart generation functions
- Support both forecast charts (7d/12m) and macro charts (importer)
- Keep `image_to_base64` utility

---

### 2. PDF Renderers

**Source Files:**
- `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/deployment/7d/src/usdclp_forecaster/report/pdf_renderer.py` (WeasyPrint)
- `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/importer_macro_report/monthly_import_report/pdf_builder.py` (ReportLab)

**Target:**
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/pdf_weasy.py`
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/pdf_reportlab.py`

**Decision:** Keep both renderers initially, default to WeasyPrint for forecasts.

---

### 3. Report Builders

**Source Files:**
- `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/deployment/7d/src/usdclp_forecaster/report/builder.py`
- `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/deployment/12m/src/usdclp_forecaster_12m/report/builder.py`
- `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/importer_macro_report/monthly_import_report/report_sections.py`

**Target:**
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/builder.py`
- Split sections into:
  - `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/sections/executive.py`
  - `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/sections/technical.py`
  - `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/sections/fundamental.py`
  - `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/sections/forecast.py`

---

### 4. Templates

**Source:**
- `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/deployment/7d/src/usdclp_forecaster/report/templates/report.html.j2`

**Target:**
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/templates/base.html.j2`
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/templates/forecast.html.j2`
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/templates/macro.html.j2`

---

### 5. Email Service

**Source:**
- `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/deployment/7d/src/usdclp_forecaster/emailer.py`
- `/Users/rafaelfarias/Documents/Archivos/Rollitos_cl/Woocomerce/importer_macro_report/monthly_import_report/email_client.py`

**Target:**
- `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/notifications/email.py`

**Preferred Base:** Importer's `email_client.py` (more robust)

---

## Import Path Changes

### Before (7d):
```python
from usdclp_forecaster.report.charting import generate_charts
from usdclp_forecaster.report.pdf_renderer import PdfRenderer
from usdclp_forecaster.report.builder import ForecastReportBuilder
from usdclp_forecaster.emailer import EmailService
```

### Before (12m):
```python
from usdclp_forecaster_12m.report.charting import generate_charts
from usdclp_forecaster_12m.report.pdf_renderer import PdfRenderer
from usdclp_forecaster_12m.report.builder import ForecastReportBuilder
from usdclp_forecaster_12m.emailer import EmailService
```

### Before (Importer):
```python
from monthly_import_report.visuals import build_charts
from monthly_import_report.pdf_builder import build_pdf
from monthly_import_report.report_sections import build_sections
from monthly_import_report.email_client import EmailClient
```

### After (Unified):
```python
from forex_core.reporting.charting import ChartGenerator
from forex_core.reporting.pdf_weasy import WeasyPrintRenderer
from forex_core.reporting.pdf_reportlab import ReportLabRenderer
from forex_core.reporting.builder import ReportBuilder
from forex_core.reporting.sections import (
    ExecutiveSection,
    TechnicalSection,
    FundamentalSection,
    ForecastSection,
)
from forex_core.notifications.email import EmailService
```

---

## Test Plan for PDF Validation

### 1. Unit Tests

**Test Chart Generation:**
```python
def test_chart_generation():
    """Ensure charts are created with correct dimensions and DPI."""
    config = ChartConfig(horizon="7d", dpi=200, size=(10, 5))
    charts = generator.generate(bundle, forecast, config)
    assert len(charts) == 2
    for chart in charts:
        assert chart.exists()
        assert chart.stat().st_size > 10_000  # >10KB
        img = Image.open(chart)
        assert img.size == (2000, 1000)  # 10*200 x 5*200
```

**Test PDF Generation:**
```python
def test_weasyprint_pdf():
    """Ensure WeasyPrint generates valid PDF."""
    renderer = WeasyPrintRenderer(settings)
    html = "<h1>Test</h1><p>Español: ñ, á, é, í</p>"
    pdf_path = renderer.write_pdf(html)
    assert pdf_path.exists()
    assert pdf_path.suffix == ".pdf"
    assert 50_000 < pdf_path.stat().st_size < 5_000_000
```

**Test Spanish Characters:**
```python
def test_spanish_characters():
    """Ensure Spanish characters render correctly."""
    text = "Proyección USD/CLP: ¿Qué pasará con el tipo de cambio?"
    html = renderer.render(text, [])
    assert "Proyección" in html
    assert "¿Qué" in html
```

---

### 2. Integration Tests

**Test Full Report Pipeline:**
```python
def test_full_report_generation():
    """End-to-end test of report generation."""
    builder = ReportBuilder(ReportConfig(horizon="7d"))
    payload = builder.build(bundle, forecast, technicals, artifacts)

    # Validate structure
    assert payload.pdf_path.exists()
    assert len(payload.chart_paths) >= 2
    assert payload.markdown_body
    assert payload.html_body

    # Validate PDF
    result = validate_pdf(payload.pdf_path)
    assert result.success

    # Validate charts
    for chart in payload.chart_paths:
        assert validate_chart(chart)
```

**Test Email Delivery:**
```python
@pytest.mark.skipif(not os.getenv("SMTP_CONFIGURED"), reason="SMTP not configured")
def test_email_delivery():
    """Test email delivery with PDF attachment."""
    service = EmailService(settings)
    service.send_report(
        subject="Test Report",
        body="This is a test",
        attachments=[pdf_path]
    )
    # Check email was sent (requires SMTP mock or test server)
```

---

### 3. Visual Regression Tests

**Compare PDFs:**
```python
def test_pdf_visual_regression():
    """Ensure new PDF matches expected output."""
    new_pdf = generate_report(test_data)
    reference_pdf = Path("tests/fixtures/reference_report.pdf")

    # Use pdf2image + PIL to compare
    new_images = convert_from_path(new_pdf)
    ref_images = convert_from_path(reference_pdf)

    for new_img, ref_img in zip(new_images, ref_images):
        similarity = image_similarity(new_img, ref_img)
        assert similarity > 0.95  # 95% similar
```

---

## Potential Issues and Mitigations

### Issue 1: WeasyPrint Installation Failures

**Problem:** Cairo/Pango dependencies not installed on macOS/Windows dev machines.

**Mitigation:**
1. Document system dependencies clearly
2. Provide Docker-based development environment
3. Add `skip_pdf=True` option for local dev
4. Fall back to markdown output if WeasyPrint unavailable

**Detection:**
```python
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except Exception as e:
    WEASYPRINT_AVAILABLE = False
    logger.warning(f"WeasyPrint not available: {e}")
```

---

### Issue 2: Font Rendering Issues

**Problem:** Spanish characters may render as boxes if fonts missing.

**Mitigation:**
1. Use web-safe fonts (Helvetica, Arial)
2. Test with full Spanish character set
3. Embed fonts in PDF if needed (ReportLab)
4. Validate rendering in CI pipeline

---

### Issue 3: Chart Quality Degradation

**Problem:** Charts may look blurry or pixelated in PDF.

**Mitigation:**
1. Use DPI=200 consistently (not 72 or 96)
2. Save charts as PNG (not JPEG)
3. Use base64 embedding for WeasyPrint
4. Validate chart dimensions in tests

---

### Issue 4: Memory Issues with Large Reports

**Problem:** Generating 12-month reports with many charts consumes memory.

**Mitigation:**
1. Stream chart generation (one at a time)
2. Close matplotlib figures immediately
3. Use context managers for file handles
4. Monitor memory usage in tests

---

### Issue 5: Different Results 7d vs 12m

**Problem:** Accidentally using wrong horizon configuration.

**Mitigation:**
1. Make horizon explicit in all function calls
2. Add validation for horizon-specific parameters
3. Include horizon in PDF filename
4. Add assertion tests for horizon-specific text

---

## Installation Instructions

### System Dependencies (Ubuntu/Debian)

```bash
# For WeasyPrint
apt-get update && apt-get install -y --no-install-recommends \
    libpangocairo-1.0-0 \
    libcairo2 \
    libffi8 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info
```

### System Dependencies (macOS)

```bash
# For WeasyPrint
brew install cairo pango gdk-pixbuf libffi
```

### Python Dependencies

```bash
# Core reporting
pip install matplotlib>=3.9 seaborn>=0.13 pandas>=2.2

# WeasyPrint approach (7d/12m)
pip install weasyprint>=62.3 cairocffi>=1.7 jinja2>=3.1 markdown>=3.6

# ReportLab approach (importer)
pip install reportlab>=4.1

# Email
pip install email-validator>=2.1
```

### Docker Setup

```dockerfile
FROM python:3.11-slim

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpangocairo-1.0-0 \
        libcairo2 \
        libffi8 \
        libgdk-pixbuf-2.0-0 \
        shared-mime-info && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app
COPY . .
```

---

## Chart Specifications

### Standard Charts (7d/12m)

**Chart 1: Historical + Forecast**
- Size: 10 x 5 inches
- DPI: 200
- Format: PNG
- Elements: Historical line (30d or 24m), forecast line, 80% CI band, 95% CI band
- Colors: Blue (#1f77b4), Red (#d62728), Light red (#ff9896), Purple (#c5b0d5)

**Chart 2: Forecast Bands Only**
- Size: 10 x 4 inches
- DPI: 200
- Format: PNG
- Elements: Forecast line, 80% CI band, 95% CI band
- Colors: Green (#2ca02c), Light green (#98df8a, #c7e9c0)

### Macro Charts (Importer Report)

**All charts:**
- Size: 6 x 3.4 inches
- DPI: 200
- Format: PNG
- Grid: True (alpha=0.3)
- X-axis rotation: 30 degrees
- Layout: Tight

**Chart types:**
1. Line charts: CLP/USD, IPC vs TPM
2. Bar charts: Retail confidence
3. Combined: Freight + congestion overlay
4. Scatter with regression: Copper vs CLP/USD
5. Horizontal bar: Risk map
6. Forecast overlay: Predicted vs actual

---

## Success Criteria

### Critical (Must Pass):

1. PDF generated successfully (exit code 0)
2. PDF file size between 50 KB and 5 MB
3. PDF opens in standard PDF readers (Preview, Acrobat, Chrome)
4. Spanish characters render correctly (ñ, á, é, í, ó, ú, ¿, ¡)
5. Charts are visible and not corrupted
6. All expected sections are present
7. Tables have correct column counts
8. Page numbers are present (if using ReportLab)

### Important (Should Pass):

1. PDF has correct metadata (title, author)
2. Charts are high quality (DPI=200)
3. Table formatting is consistent
4. Colors match brand guidelines
5. Markdown backup generated if PDF fails
6. Email delivery works with attachment

### Nice-to-Have (Could Pass):

1. PDF is searchable (text not rasterized)
2. PDF has bookmarks for sections
3. Charts have descriptive alt text
4. PDF is ADA-compliant
5. File size optimized (<500 KB for 7d/12m)

---

## Timeline and Dependencies

### Week 1: Core Migration
- Day 1-2: Migrate charting.py (unified)
- Day 3-4: Migrate pdf_weasy.py and templates
- Day 5: Initial tests

### Week 2: Section Splitting
- Day 1-2: Split builder.py into sections
- Day 3-4: Implement ReportConfig parameterization
- Day 5: Integration tests

### Week 3: Email and Validation
- Day 1-2: Migrate email.py
- Day 3-4: Implement PDF validation
- Day 5: End-to-end tests

### Week 4: Importer Report Support
- Day 1-2: Migrate visuals.py advanced charts
- Day 3-4: Migrate ReportLab renderer (optional)
- Day 5: Final validation

---

## Rollback Plan

If PDF generation fails after migration:

1. **Immediate:** Use markdown backup mode (`skip_pdf=True`)
2. **Short-term:** Revert to legacy services via Docker
3. **Long-term:** Fix issues and redeploy

**Rollback command:**
```bash
# Revert to legacy 7d service
cd deployment/7d
docker-compose up -d

# Revert to legacy 12m service
cd deployment/12m
docker-compose up -d
```

---

## Open Questions

1. **Should we keep both WeasyPrint and ReportLab?**
   - **Recommendation:** Yes initially, deprecate ReportLab later if not needed

2. **Should we support HTML output in addition to PDF?**
   - **Recommendation:** Yes, useful for web dashboards

3. **Should chart generation be async/parallel?**
   - **Recommendation:** Not initially, optimize later if needed

4. **Should we version PDF templates?**
   - **Recommendation:** Yes, use semantic versioning for templates

5. **Should we support custom branding (logos, colors)?**
   - **Recommendation:** Yes, add to ReportConfig

---

## References

### Documentation:
- [WeasyPrint Docs](https://weasyprint.readthedocs.io/)
- [ReportLab User Guide](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [Matplotlib Savefig](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html)
- [Jinja2 Templates](https://jinja.palletsprojects.com/)

### Related Migration Documents:
- `CORE_ABSTRACTIONS_MIGRATION.md`
- `DATA_INGESTION_MIGRATION.md`
- `FORECASTING_ENGINE_MIGRATION.md`

---

## Conclusion

PDF generation is the **most critical** component of the system. The migration must:

1. Preserve all existing functionality
2. Support both 7d and 12m horizons seamlessly
3. Handle Spanish characters correctly
4. Generate high-quality charts
5. Support email delivery
6. Have comprehensive error handling
7. Include thorough tests

**Risk Level:** HIGH - This is the primary output of the system. Any failure in PDF generation is a critical bug.

**Priority:** Implement immediately after core abstractions and before forecasting engine.

**Estimated Effort:** 3-4 weeks for full migration with tests.

---

**Next Steps:**
1. Review this document with stakeholders
2. Set up development environment with WeasyPrint
3. Begin core charting migration
4. Implement validation tests early
5. Test with real data from all three horizons
