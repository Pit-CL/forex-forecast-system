# PDF System Comparison Matrix

**Date:** 2025-11-12
**Purpose:** Detailed feature comparison across all three PDF systems

---

## System Comparison

| Feature | 7d Forecaster | 12m Forecaster | Importer Report | Recommended |
|---------|---------------|----------------|-----------------|-------------|
| **PDF Library** | WeasyPrint | WeasyPrint | ReportLab | WeasyPrint |
| **Rendering Method** | HTML-to-PDF | HTML-to-PDF | Programmatic | HTML-to-PDF |
| **Templating** | Jinja2 | Jinja2 | None (code-based) | Jinja2 |
| **Chart Library** | Matplotlib | Matplotlib | Matplotlib | Matplotlib |
| **Chart Count** | 2 | 2 | 9 (conditional) | Configurable |
| **Chart Size** | 10x5, 10x4 | 10x5, 10x4 | 6x3.4 | Configurable |
| **Chart DPI** | 200 | 200 | 200 | 200 |
| **Chart Embedding** | Base64 | Base64 | File path | Base64 |
| **Page Size** | A4 (implied) | A4 (implied) | A4 (explicit) | A4 |
| **Page Numbers** | No | No | Yes | Yes |
| **Table of Contents** | No | No | Yes | Optional |
| **Cover Page** | No | No | Yes | Optional |
| **PDF Metadata** | Limited | Limited | Full | Full |
| **Spanish Support** | UTF-8 HTML | UTF-8 HTML | Latin-1 | UTF-8 |
| **Font Family** | Helvetica Neue | Helvetica Neue | Helvetica | Helvetica |
| **CSS Styling** | Embedded | Embedded | N/A | Embedded |
| **Markdown Support** | Yes | Yes | No | Yes |
| **Email Integration** | Basic SMTP | Basic SMTP | Advanced SMTP | Advanced |
| **Error Handling** | Basic | Basic | Moderate | Comprehensive |
| **Fallback Mode** | Markdown | Markdown | None | Markdown |
| **System Dependencies** | Cairo, Pango | Cairo, Pango | None | Cairo, Pango |
| **Lines of Code** | ~450 | ~440 | ~850 | ~600 (unified) |
| **Report Sections** | 12 | 12 | 13 | Configurable |
| **Word Limits** | Yes (300, 150) | Yes (300, 150) | No | Configurable |
| **Validation** | None | None | None | Comprehensive |

---

## Chart Comparison

### 7d Forecaster Charts

| Chart | Title | Size | Elements | Colors | Purpose |
|-------|-------|------|----------|--------|---------|
| 1 | USD/CLP - Histórico reciente + Proyección 7d | 10x5 | Historical 30d line, Forecast line, 80% CI, 95% CI | Blue, Red, Pink, Purple | Show recent context + forecast |
| 2 | USD/CLP - Intervalos de confianza 7 días | 10x4 | Forecast line, 80% CI, 95% CI | Green, Light green | Focus on uncertainty bands |

### 12m Forecaster Charts

| Chart | Title | Size | Elements | Colors | Purpose |
|-------|-------|------|----------|--------|---------|
| 1 | USD/CLP - Histórico reciente + Proyección 12m | 10x5 | Historical 24m line (monthly), Forecast line, 80% CI, 95% CI | Blue, Red, Pink, Purple | Show long-term context + forecast |
| 2 | USD/CLP - Intervalos de confianza 12 meses | 10x4 | Forecast line, 80% CI, 95% CI | Green, Light green | Focus on uncertainty bands |

### Importer Report Charts

| Chart | Title | Size | Elements | Colors | Purpose |
|-------|-------|------|----------|--------|---------|
| 1 | CLP/USD vs. supuestos IPoM | 6x3.4 | Observed + BCCh projection line | Blue | Show official projections |
| 2 | Costos logísticos y congestión | 6x3.4 | Freight line + Congestion bars | Orange, transparent | Logistics costs |
| 3 | Inflación y política monetaria | 6x3.4 | IPC line, TPM line | Green, Red | Monetary policy |
| 4 | Volumen real de importaciones | 6x3.4 | Import volume line | Purple | Demand indicator |
| 5 | Confianza retail CNC | 6x3.4 | Confidence bars + threshold line | Brown, Dark gray | Consumer sentiment |
| 6 | Cobre vs CLP/USD | 6x3.4 | Scatter plot + regression line | Cyan, Pink dashed | Correlation analysis |
| 7 | Mapa de riesgos críticos | 6x3.4 | Horizontal bars with labels | Red | Risk prioritization |
| 8 | CLP/USD observado vs pronóstico | 6x3.4 | Actual line + SARIMAX forecast | Blue, Orange dashed | Model validation |
| 9 | Ventas restaurantes vs forecast | 6x3.4 | Actual line + ML forecast | Green, Red dashed | Demand forecast |

---

## Section Comparison

### 7d Forecaster Sections

| Order | Section | Purpose | Dynamic Content |
|-------|---------|---------|-----------------|
| 1 | Proyección USD/CLP (7 días) | Main forecast table | 7 daily points with CIs |
| 2 | Interpretación Ejecutiva | Executive summary | Trend, confidence, recommendations |
| 3 | Drivers Clave | Top 5 drivers ranked | Copper, rate differential, DXY, IPC, Fed dot plot |
| 4 | Factores Cuantitativos | Key indicators table | Copper, TPM, IPC, DXY, Fed rate |
| 5 | Calendario Macro (7 días) | Upcoming events | Next 7 days USD-impacting events |
| 6 | Noticias Relevantes (48h) | Recent news | Last 48h news with sentiment |
| 7 | Análisis Técnico Complementario | Technical indicators | RSI, MACD, MA, support, resistance |
| 8 | Declaración de Incertidumbre | Assumptions | Data sources, model assumptions |
| 9 | Riesgos de Cola | Tail risks | 3 extreme scenarios |
| 10 | Razonamiento y Metodología | Model explanation | ARIMA order, ensemble weights, metrics |
| 11 | Conclusión Técnica | Action items | Hedging strategy, triggers |
| 12 | Fuentes y Validación | Source citations | All data sources with URLs |

### 12m Forecaster Sections

| Order | Section | Purpose | Dynamic Content |
|-------|---------|---------|-----------------|
| 1 | Proyección USD/CLP (12 meses) | Main forecast table | 12 monthly points with CIs |
| 2 | Interpretación Ejecutiva | Executive summary | Long-term trend, confidence |
| 3 | Drivers Clave | Top 5 drivers ranked | Same as 7d |
| 4 | Factores Cuantitativos | Key indicators table | Same as 7d |
| 5 | Calendario Macro (próximas 4 semanas) | Upcoming events | Next 4 weeks events |
| 6 | Noticias Relevantes (48h) | Recent news | Same as 7d |
| 7 | Análisis Técnico Complementario | Technical indicators | Same as 7d |
| 8 | Declaración de Incertidumbre | Assumptions | Same as 7d |
| 9 | Riesgos de Cola | Tail risks | Same as 7d |
| 10 | Razonamiento y Metodología | Model explanation | Same as 7d |
| 11 | Conclusión Técnica | Action items | Quarterly hedging strategy |
| 12 | Fuentes y Validación | Source citations | Same as 7d |

### Importer Report Sections

| Order | Section | Purpose | Dynamic Content |
|-------|---------|---------|-----------------|
| 0 | Cover Page | Title page | Report title, date |
| 1 | Índice | Table of contents | Auto-generated section list |
| 2 | Resumen ejecutivo | Executive summary | Top risks, indicators, 1 chart |
| 3 | Introducción y metodología | Context | Objective, data sources |
| 4 | Entorno macro y financiero | Macro analysis | CLP/USD, IPC, TPM, Copper + 3 charts |
| 5 | Demanda, logística y costos | Supply chain | Import volume, freight, confidence + 3 charts |
| 6 | Impacto de variables críticas | Impact analysis | FX, tariffs, logistics, demand + risk chart |
| 7 | Análisis del entorno micro | Microeconomic | Clients, suppliers, competitors tables |
| 8 | Industria restaurantes y food service | Sector deep-dive | Sales, margins, costs table |
| 9 | Análisis PESTEL | Strategic framework | Political, Economic, Social, Tech, Environmental, Legal |
| 10 | Modelo Porter 5 Fuerzas | Competitive analysis | Suppliers, buyers, rivalry, substitutes, new entrants |
| 11 | Escenarios 1, 3 y 5 años | Scenario planning | Base, stress, optimistic scenarios |
| 12 | Proyecciones cuantitativas | Forecasts | SARIMAX, VAR, ML models + 2 charts |
| 13 | Conclusiones y recomendaciones | Action items | Hedging, logistics, tech recommendations |
| 14 | Fuentes y anexos | References | Full source catalog |

---

## Code Structure Comparison

### 7d/12m Architecture

```
usdclp_forecaster/
├── report/
│   ├── __init__.py
│   ├── charting.py          # 69 lines - chart generation
│   ├── pdf_renderer.py      # 53 lines - WeasyPrint wrapper
│   ├── builder.py           # 327 lines - main orchestrator
│   └── templates/
│       └── report.html.j2   # 25 lines - HTML template
├── emailer.py               # 36 lines - SMTP email
└── analysis/
    └── report_sections.py   # 1 line - empty legacy file
```

### Importer Architecture

```
monthly_import_report/
├── visuals.py              # 216 lines - chart generation
├── pdf_builder.py          # 241 lines - ReportLab PDF
├── report_sections.py      # 321 lines - section content
└── email_client.py         # 69 lines - SMTP email
```

### Proposed Unified Architecture

```
forex_core/
├── reporting/
│   ├── __init__.py
│   ├── charting.py         # ~200 lines - unified chart generation
│   ├── pdf_weasy.py        # ~100 lines - WeasyPrint renderer
│   ├── pdf_reportlab.py    # ~250 lines - ReportLab renderer (optional)
│   ├── builder.py          # ~150 lines - horizon-agnostic orchestrator
│   ├── config.py           # ~80 lines - report configuration
│   ├── validation.py       # ~100 lines - PDF/chart validation
│   ├── sections/
│   │   ├── __init__.py
│   │   ├── base.py         # ~50 lines - section base class
│   │   ├── executive.py    # ~80 lines - executive summary
│   │   ├── technical.py    # ~100 lines - technical analysis
│   │   ├── fundamental.py  # ~120 lines - fundamental analysis
│   │   ├── forecast.py     # ~100 lines - forecast tables
│   │   └── macro.py        # ~150 lines - macro environment (importer)
│   └── templates/
│       ├── base.html.j2    # ~30 lines - base template
│       ├── forecast.html.j2 # ~40 lines - forecast-specific
│       └── macro.html.j2   # ~60 lines - importer-specific
└── notifications/
    ├── __init__.py
    └── email.py            # ~100 lines - unified email service
```

---

## Dependency Matrix

| Library | 7d | 12m | Importer | Version | Purpose |
|---------|-----|-----|----------|---------|---------|
| matplotlib | ✓ | ✓ | ✓ | >=3.9 | Chart generation |
| seaborn | ✓ | ✓ | ✗ | >=0.13 | Chart styling |
| pandas | ✓ | ✓ | ✓ | >=2.2 | Data manipulation |
| weasyprint | ✓ | ✓ | ✗ | >=62.3 | HTML-to-PDF |
| cairocffi | ✓ | ✓ | ✗ | >=1.7 | WeasyPrint dependency |
| reportlab | ✗ | ✗ | ✓ | >=4.1 | Programmatic PDF |
| jinja2 | ✓ | ✓ | ✗ | >=3.1 | Template rendering |
| markdown | ✓ | ✓ | ✗ | >=3.6 | Markdown-to-HTML |
| smtplib | ✓ | ✓ | ✓ | stdlib | Email delivery |
| email | ✓ | ✓ | ✓ | stdlib | Email formatting |
| base64 | ✓ | ✓ | ✗ | stdlib | Image encoding |
| mimetypes | ✗ | ✗ | ✓ | stdlib | MIME type detection |

### System Dependencies (Ubuntu/Debian)

**For WeasyPrint (7d/12m):**
```
libpangocairo-1.0-0
libcairo2
libffi8
libgdk-pixbuf-2.0-0
shared-mime-info
```

**For ReportLab (Importer):**
- None (pure Python)

---

## Feature Gaps Analysis

### What 7d/12m Have That Importer Lacks:

1. Jinja2 templating (easier to customize)
2. Markdown support (easier to write content)
3. Base64 chart embedding (more portable)
4. Fallback to markdown if PDF fails
5. WeasyPrint error detection

### What Importer Has That 7d/12m Lack:

1. Page numbers
2. Table of contents
3. Cover page
4. Better PDF metadata
5. More sophisticated table styling
6. Section numbering
7. More chart types (scatter, bar, overlay)
8. Risk visualization
9. MIME type detection for email
10. TLS vs SSL email configuration

### What All Systems Lack:

1. PDF validation (size, structure, readability)
2. Chart quality validation
3. Automated visual regression tests
4. PDF compression/optimization
5. Bookmarks/navigation
6. Accessibility features
7. Watermarks
8. Digital signatures
9. PDF/A compliance
10. Multi-language support (beyond Spanish)

---

## Performance Comparison

| Metric | 7d | 12m | Importer | Target |
|--------|-----|-----|----------|--------|
| Chart generation time | ~2s | ~2s | ~5s | <3s |
| PDF generation time | ~1s | ~1s | ~2s | <2s |
| Total report time | ~15s | ~20s | ~30s | <25s |
| Memory peak (MB) | ~150 | ~150 | ~200 | <200 |
| PDF file size (KB) | 150-300 | 150-300 | 500-1500 | <1000 |
| Chart file size (KB) | 50-100 | 50-100 | 40-80 | <100 |

---

## Migration Complexity

| Component | Complexity | Effort | Risk | Priority |
|-----------|------------|--------|------|----------|
| charting.py | Medium | 2 days | Medium | High |
| pdf_weasy.py | Low | 1 day | Low | High |
| builder.py | High | 3 days | High | Critical |
| templates | Low | 1 day | Low | High |
| sections (split) | High | 3 days | Medium | Critical |
| email.py | Low | 1 day | Low | Medium |
| pdf_reportlab.py | Medium | 2 days | Low | Low (optional) |
| validation.py | Medium | 2 days | Low | High |
| Tests | High | 5 days | Medium | Critical |

**Total Estimated Effort:** 20 work days (4 weeks)

---

## Decision Matrix

### Should We Use WeasyPrint or ReportLab?

| Criteria | WeasyPrint | ReportLab | Winner |
|----------|------------|-----------|--------|
| Ease of use | High (HTML) | Low (code) | WeasyPrint |
| Flexibility | Medium | High | ReportLab |
| System deps | Yes (Cairo) | No | ReportLab |
| Template support | Yes | No | WeasyPrint |
| Learning curve | Low | High | WeasyPrint |
| Styling | CSS | Python | WeasyPrint |
| Legacy use | 2/3 systems | 1/3 systems | WeasyPrint |
| Community | Large | Large | Tie |
| Maintenance | Active | Active | Tie |

**Decision:** Use WeasyPrint as primary, keep ReportLab optional for advanced use cases.

---

### Should We Split Sections or Keep Monolithic Builder?

| Criteria | Monolithic | Split Sections | Winner |
|----------|------------|----------------|--------|
| Code organization | Poor | Excellent | Split |
| Testability | Poor | Excellent | Split |
| Reusability | Poor | Excellent | Split |
| Customization | Hard | Easy | Split |
| Initial complexity | Low | High | Monolithic |
| Long-term maintenance | Hard | Easy | Split |
| Adding new sections | Hard | Easy | Split |

**Decision:** Split into sections for long-term maintainability.

---

### Should We Support Multiple Horizons in One Builder?

| Criteria | Separate Builders | Unified Builder | Winner |
|----------|-------------------|-----------------|--------|
| Code duplication | High | Low | Unified |
| Type safety | High | Medium | Separate |
| Flexibility | Low | High | Unified |
| Testing complexity | Low | High | Separate |
| Maintenance | Hard | Easy | Unified |
| Adding new horizons | Hard | Easy | Unified |

**Decision:** Unified builder with ReportConfig parameterization.

---

## Recommended Implementation Order

### Phase 1: Foundation (Week 1)
1. Create `forex_core/reporting/config.py` - ReportConfig, ChartConfig
2. Migrate `charting.py` with horizon parameterization
3. Migrate `pdf_weasy.py` with error handling
4. Migrate `templates/base.html.j2`
5. Basic unit tests for charts and PDF

### Phase 2: Core Builder (Week 2)
1. Create `sections/base.py` - Section base class
2. Create `sections/forecast.py` - Forecast table section
3. Create `sections/executive.py` - Executive summary
4. Create `sections/technical.py` - Technical analysis
5. Create unified `builder.py` with ReportConfig
6. Integration tests for full report

### Phase 3: Email and Validation (Week 3)
1. Migrate `notifications/email.py` with TLS/SSL support
2. Create `reporting/validation.py` - PDF and chart validation
3. Add validation to builder pipeline
4. Add fallback to markdown on PDF failure
5. Email integration tests

### Phase 4: Advanced Features (Week 4)
1. Migrate importer-specific charts to `charting.py`
2. Create `sections/macro.py` for importer sections
3. Add optional ReportLab renderer (`pdf_reportlab.py`)
4. Add page numbers, ToC, cover page to WeasyPrint
5. Visual regression tests
6. Performance optimization

---

## Risk Mitigation Strategies

### High Risk: PDF Generation Failures

**Mitigation:**
1. Comprehensive error handling with fallback
2. Validate WeasyPrint availability on startup
3. Document system dependencies clearly
4. Provide Docker environment for consistent builds
5. Add markdown backup mode
6. Monitor PDF generation in production

### Medium Risk: Chart Quality Issues

**Mitigation:**
1. Validate chart dimensions and file size
2. Use consistent DPI (200)
3. Test with real data from all horizons
4. Add visual regression tests
5. Monitor chart generation errors

### Medium Risk: Spanish Character Issues

**Mitigation:**
1. Use UTF-8 encoding consistently
2. Test with full Spanish character set
3. Use web-safe fonts
4. Validate rendering in CI
5. Test on multiple PDF readers

### Low Risk: Performance Degradation

**Mitigation:**
1. Profile chart generation
2. Close matplotlib figures immediately
3. Stream large datasets
4. Monitor memory usage
5. Add timeouts for PDF generation

---

## Success Metrics

### Quantitative:
- PDF generation success rate: >99.5%
- PDF generation time: <3 seconds
- Chart generation time: <2 seconds
- File size: 50 KB - 1 MB
- Memory usage: <200 MB peak
- Spanish character rendering: 100%
- Test coverage: >90%

### Qualitative:
- PDFs open in all major readers
- Charts are visually clear
- Tables are readable
- Spanish text is correct
- Formatting is consistent
- Error messages are helpful

---

## Appendix: Code Snippets

### Proposed ReportConfig

```python
from dataclasses import dataclass, field
from typing import Dict, List, Literal

@dataclass
class ChartSpec:
    title: str
    size: tuple[int, int]  # (width, height) in inches
    dpi: int = 200
    colors: Dict[str, str] = field(default_factory=dict)
    elements: List[str] = field(default_factory=list)

@dataclass
class ReportConfig:
    horizon: Literal["7d", "12m", "monthly"]
    historical_window: int  # 30 days, 24 months, etc.
    forecast_points: int  # 7, 12, 6
    time_unit: Literal["days", "months", "weeks"]
    trend_threshold: float  # 0.5, 1.5
    word_limits: Dict[str, int] = field(default_factory=lambda: {
        "interpretation": 300,
        "conclusion": 150
    })
    chart_specs: List[ChartSpec] = field(default_factory=list)
    include_cover: bool = False
    include_toc: bool = False
    include_page_numbers: bool = False
    pdf_title: str = "Forecast Report"
    pdf_author: str = "Forecast Team"
```

### Proposed Section Base Class

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import pandas as pd

@dataclass
class SectionContent:
    title: str
    paragraphs: List[str]
    tables: List[pd.DataFrame] = field(default_factory=list)
    charts: List[Path] = field(default_factory=list)
    markdown: str = ""

class Section(ABC):
    def __init__(self, config: ReportConfig):
        self.config = config

    @abstractmethod
    def generate(self, bundle: DataBundle, forecast: ForecastPackage) -> SectionContent:
        """Generate section content."""
        pass

    def to_markdown(self, content: SectionContent) -> str:
        """Convert section to markdown."""
        lines = [f"## {content.title}", ""]
        lines.extend(content.paragraphs)
        for table in content.tables:
            lines.append(table.to_markdown(index=False))
        return "\n\n".join(lines)
```

### Proposed Unified Builder

```python
class ReportBuilder:
    def __init__(self, config: ReportConfig):
        self.config = config
        self.renderer = WeasyPrintRenderer(config)
        self.chart_gen = ChartGenerator(config)
        self.sections = self._init_sections()

    def _init_sections(self) -> List[Section]:
        """Initialize sections based on horizon."""
        if self.config.horizon in ("7d", "12m"):
            return [
                ForecastSection(self.config),
                ExecutiveSection(self.config),
                TechnicalSection(self.config),
                # ... more sections
            ]
        elif self.config.horizon == "monthly":
            return [
                MacroSection(self.config),
                DemandSection(self.config),
                # ... more sections
            ]

    def build(self, bundle: DataBundle, forecast: ForecastPackage) -> ReportPayload:
        """Build complete report."""
        # Generate charts
        charts = self.chart_gen.generate(bundle, forecast)

        # Generate sections
        section_contents = []
        for section in self.sections:
            content = section.generate(bundle, forecast)
            section_contents.append(content)

        # Combine into markdown
        markdown_body = self._combine_sections(section_contents)

        # Render to HTML
        html_body = self.renderer.render(markdown_body, charts)

        # Generate PDF
        try:
            pdf_path = self.renderer.write_pdf(html_body)
        except WeasyPrintError as e:
            logger.error(f"PDF generation failed: {e}")
            pdf_path = self._write_markdown_backup(markdown_body)

        # Validate
        validation = validate_pdf(pdf_path)
        if not validation.success:
            logger.warning(f"PDF validation failed: {validation.error}")

        return ReportPayload(
            markdown_body=markdown_body,
            html_body=html_body,
            pdf_path=pdf_path,
            chart_paths=charts
        )
```

---

**End of Comparison Matrix**
