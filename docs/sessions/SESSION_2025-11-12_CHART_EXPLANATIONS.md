# Session: Chart Explanations Refactor for USD/CLP Reports

**Date:** 2025-11-12
**Duration:** ~90 minutes
**Type:** Feature Enhancement
**Status:** COMPLETED - Ready for Deployment

---

## Executive Summary

Refactored the PDF report generation system to pair chart explanations directly below each chart image, replacing the previous approach where explanations appeared in separate sections (often on different pages). This enhancement improves readability, ensures charts and their interpretations stay together, and adds dynamic statistical insights from real-time market data.

**Key Achievement:** Transformed report structure from "charts-then-text" to "integrated chart blocks" with professional styling and page-break protection.

---

## Objectives

**Primary Goals:**
- [x] Move chart explanations from separate sections to directly below charts
- [x] Ensure charts and explanations never split across pages
- [x] Add professional styling with visual hierarchy
- [x] Include dynamic statistical insights (RSI values, TPM rates, risk regimes)

**Secondary Goals:**
- [x] Refactor verbose explanation methods into concise helpers
- [x] Create reusable chart block structure
- [x] Document implementation for future maintainers
- [x] Maintain backward compatibility with existing pipeline

---

## Work Completed

### Changes to Code

#### 1. `/src/forex_core/reporting/builder.py` (889 lines total)

**Modified Methods:**

**A. `build()` method (Lines 93-120)**
- Changed: `chart_imgs` list → `chart_blocks` structured data
- Before: `[ChartGenerator.image_to_base64(path) for path in charts.values()]`
- After: `self._build_chart_blocks(bundle, charts)`
- Impact: Template now receives structured blocks with title/image/explanation instead of raw base64 images

**B. New `_build_chart_blocks()` method (Lines 122-207)**
```python
def _build_chart_blocks(
    self,
    bundle: DataBundle,
    charts: Dict[str, Path],
) -> List[Dict[str, str]]:
    """
    Build chart blocks with embedded explanations.

    Returns:
        List of dicts with keys: image, title, explanation
    """
```

**Chart Blocks Created (in order):**
1. **Historical + Forecast** - Static explanation about SARIMAX confidence intervals
2. **Forecast Bands** - Static explanation about projection uncertainty
3. **Technical Panel** - Dynamic (calls `_get_technical_panel_explanation()`)
4. **Correlation Matrix** - Static explanation about statistical significance
5. **Macro Dashboard** - Dynamic (calls `_get_macro_dashboard_explanation()`)
6. **Risk Regime** - Dynamic (calls `_get_regime_explanation()`)

**C. Refactored Explanation Methods (Lines 807-889)**

Created three concise helper methods:

**`_get_technical_panel_explanation(bundle)` (Lines 807-842)**
- Extracts live RSI and MACD values
- Interprets RSI: >70 = sobrecompra, <30 = sobreventa, else neutral
- Interprets MACD: > signal = momentum positivo, else negativo
- Returns 2-3 sentence explanation with current values
- Example output: "Tres paneles técnicos: precio con Bollinger Bands, RSI en neutral (52.3), y MACD con momentum positivo."

**`_get_macro_dashboard_explanation(bundle)` (Lines 845-861)**
- Extracts current copper price and TPM rate
- Example: "Cobre (4.15 USD/lb), TPM (5.75%)"
- Explains four macro drivers: Copper, TPM, DXY, IPC
- Fallback text if data unavailable

**`_get_regime_explanation(bundle)` (Lines 863-889)**
- Computes risk regime (Risk-on/Risk-off/Neutral)
- Shows DXY, VIX, EEM 5-day changes as percentages
- Example: "Régimen actual: Risk-Off, DXY +1.2%, VIX +8.5%, EEM -2.3%"
- Includes actionable interpretation (favorable/unfavorable for CLP)

**D. Updated `_build_markdown_sections()` (Lines 245-286)**
- Removed calls to old verbose methods:
  - `_build_technical_panel_explanation()`
  - `_build_correlation_explanation()`
  - `_build_macro_dashboard_explanation()`
  - `_build_regime_explanation()`
- Added comment: `# NOTE: Chart explanations are now embedded with charts in template`
- Explanations now render at top of report with charts, not in body sections

---

#### 2. `/src/forex_core/reporting/templates/report.html.j2` (251 lines total)

**A. New CSS Classes (Lines 88-131)**

```css
/* Chart blocks - keep chart + explanation together */
.chart-block {
    margin: 24px 0;
    page-break-inside: avoid;  /* CRITICAL: Keeps chart + explanation on same page */
    background-color: #f9fafb;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 16px;
}

.chart-title {
    font-size: 13pt;
    font-weight: 600;
    color: #1e5a96;  /* Professional blue */
    margin-bottom: 12px;
}

.chart-explanation {
    margin-top: 12px;
    padding: 12px 16px;
    background-color: #ffffff;
    border-left: 4px solid #4299e1;  /* Blue accent bar */
    border-radius: 4px;
    font-size: 10pt;
    font-style: italic;
    color: #4a5568;
    line-height: 1.5;
}
```

**Key Design Decisions:**
- `page-break-inside: avoid` ensures chart blocks never split across pages
- Gray background (#f9fafb) differentiates chart blocks from text sections
- Blue accent bar (#4299e1) on explanation box for visual hierarchy
- Italic 10pt font for explanations (vs 11pt body) - subtle but distinct
- Title in bold blue (#1e5a96) matches report color scheme

**B. Updated HTML Template (Lines 233-244)**

**Before:**
```html
<div class="charts-section">
    {% for chart in charts %}
        <img src="{{ chart }}" class="chart" alt="Gráfico de análisis">
    {% endfor %}
</div>
```

**After:**
```html
<div class="charts-section">
    {% for block in chart_blocks %}
        <div class="chart-block">
            <div class="chart-title">{{ block.title }}</div>
            <img src="{{ block.image }}" class="chart" alt="{{ block.title }}">
            <div class="chart-explanation">
                <strong>Interpretación:</strong> {{ block.explanation }}
            </div>
        </div>
    {% endfor %}
</div>
```

**Visual Structure:**
```
┌─────────────────────────────────────────┐
│  Chart Block (light gray background)   │
│  ┌───────────────────────────────────┐ │
│  │ Proyección USD/CLP (bold blue)    │ │  ← Title
│  └───────────────────────────────────┘ │
│  ┌───────────────────────────────────┐ │
│  │                                   │ │
│  │      [CHART IMAGE PNG]            │ │  ← Chart
│  │                                   │ │
│  └───────────────────────────────────┘ │
│  ┌───────────────────────────────────┐ │
│  │▌ Interpretación: Evolución...     │ │  ← Explanation (blue bar, italic)
│  │▌ Las bandas grises representan... │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

### Statistical Explanations Added

Each chart now has a professional 2-3 sentence explanation:

**Chart 1 - Historical + Forecast:**
> "Evolución histórica de 60 días y proyección futura con intervalos de confianza. Las bandas grises representan incertidumbre: banda oscura (80% confianza), banda clara (95% confianza). El escenario central aparece en línea azul sólida."

**Chart 2 - Forecast Bands:**
> "Detalle de la proyección mostrando evolución esperada del tipo de cambio. La zona sombreada muestra el rango probable de movimiento según el modelo ensemble. Importante: mientras más angosta la banda, mayor certeza en la proyección."

**Chart 3 - Technical Panel (Dynamic):**
> "Tres paneles técnicos: precio con Bollinger Bands (bandas de volatilidad), RSI en {rsi_status}, y MACD con {macd_status}. Las Bollinger Bands señalan zonas de sobreextensión cuando el precio toca las bandas."

- RSI status: "sobrecompra (>70)" | "sobreventa (<30)" | "neutral (52.3)"
- MACD status: "momentum positivo" | "momentum negativo"

**Chart 4 - Correlation Matrix:**
> "Relaciones estadísticas entre USD/CLP y sus principales drivers. Correlación negativa USD/CLP-Cobre indica que alza del cobre fortalece el peso. VIX-EEM negativa confirma que en risk-off los emergentes caen."

**Chart 5 - Macro Dashboard (Dynamic):**
> "Cuatro drivers fundamentales: Cobre ({copper_price} USD/lb) con relación inversa al USD/CLP, TPM ({tpm_rate}%) que determina diferencial de tasas, DXY como proxy de fortaleza USD global, e IPC que guía política monetaria del BCCh."

**Chart 6 - Risk Regime (Dynamic):**
> "Régimen actual: {regime_status}. Calculado con DXY (dólar refugio), VIX (volatilidad implícita), y EEM (ETF emergentes). Cambios en 5 días: DXY {dxy_change:+.1f}%, VIX {vix_change:+.1f}%, EEM {eem_change:+.1f}%."

- Regime status examples:
  - "Risk-On: apetito por riesgo favorable a emergentes, positivo para CLP"
  - "Risk-Off: aversión al riesgo presiona CLP hacia depreciación"
  - "Mixto: señales contradictorias, factores locales tienen mayor peso"

---

### Files Modified Summary

| File | Lines Changed | Type | Impact |
|------|---------------|------|--------|
| `builder.py` | +150 / -80 | Python | Core logic refactor |
| `report.html.j2` | +50 / -10 | Jinja2/CSS | Template structure |

**Total:** ~200 lines added, ~90 lines removed (net +110 lines)

---

## Decisions Made

### Decision 1: Pair Charts with Explanations vs Keep Separate Sections

**Context:** Original design had all charts at top, explanations scattered in markdown sections below

**Options Considered:**
1. Keep current design (charts at top, explanations in sections)
   - Pros: Minimal code changes
   - Cons: Charts and explanations separated across pages, poor UX
2. Add brief captions below charts (1 sentence)
   - Pros: Simple implementation
   - Cons: Not enough context for non-expert readers
3. Create structured chart blocks with 2-3 sentence explanations
   - Pros: Professional appearance, always paired, sufficient context
   - Cons: More refactoring required

**Decision:** Option 3 (structured chart blocks)

**Reasoning:**
- User specifically requested explanations "directly below charts"
- Statistical insights from agent-usdclp require 2-3 sentences
- Professional reports benefit from integrated explanations
- `page-break-inside: avoid` ensures pairing

**Impact:** Significant refactor of builder.py and template, but much better UX

---

### Decision 2: Dynamic vs Static Explanations

**Context:** Some charts benefit from showing current market values (RSI, TPM, regime)

**Options Considered:**
1. All static explanations (hardcoded text)
   - Pros: Simple, no risk of data errors
   - Cons: Generic, not actionable
2. All dynamic explanations (extract values for every chart)
   - Pros: Maximum relevance
   - Cons: Complex, risk of crashes if data missing
3. Mix: Static for descriptive charts, dynamic for analytical charts
   - Pros: Balance of simplicity and relevance
   - Cons: Two code paths

**Decision:** Option 3 (mixed approach)

**Static Explanations (Charts 1, 2, 4):**
- Historical + Forecast
- Forecast Bands
- Correlation Matrix

**Dynamic Explanations (Charts 3, 5, 6):**
- Technical Panel (RSI/MACD values)
- Macro Dashboard (Copper/TPM values)
- Risk Regime (regime classification + percentage changes)

**Reasoning:**
- Technical/macro/regime charts contain actionable insights
- Descriptive charts (forecast, correlation) are self-explanatory
- Fallback text prevents crashes if data unavailable

**Impact:** Readers get current market context where it matters most

---

### Decision 3: Explanation Length (2-3 sentences)

**Context:** Needed to balance detail with brevity

**Options:**
1. One sentence captions
2. 2-3 sentences (paragraph)
3. Full section (5-10 sentences)

**Decision:** 2-3 sentences

**Reasoning:**
- One sentence too brief for statistical context
- Full sections duplicate body text
- 2-3 sentences provide "just enough" interpretation
- Fits well below chart without overwhelming page

---

## Problems Encountered and Solutions

### Problem 1: Page Breaks Between Charts and Explanations

**Symptom:** In early tests, some charts appeared at bottom of page, explanation on next page

**Cause:** WeasyPrint default page-break behavior splits content to fit pages

**Solution:**
```css
.chart-block {
    page-break-inside: avoid;
}
```

**Prevention:** Always test PDF rendering with real data, not just HTML preview

---

### Problem 2: Missing Optional Import in email.py

**Symptom:** Initial test failed with `NameError: name 'Optional' is not defined`

**Cause:** `email.py` used `Optional` type hint without importing it

**Root Cause:** Recent refactor added `additional_attachments: Sequence[Path] = None` parameter without adding import

**Solution:**
```python
# Added to imports
from typing import List, Sequence, Optional
```

**File:** `/src/forex_core/notifications/email.py` (Line 24)

**Prevention:** Run type checker (`mypy`) before committing

---

### Problem 3: Explanation Methods Naming Conflict

**Symptom:** Old verbose methods (`_build_*_explanation`) conflicted with new concise helpers

**Cause:** Wanted to keep method signatures but change behavior

**Solution:** Renamed methods:
- `_build_technical_panel_explanation()` → `_get_technical_panel_explanation()`
- `_build_macro_dashboard_explanation()` → `_get_macro_dashboard_explanation()`
- `_build_regime_explanation()` → `_get_regime_explanation()`

**Reasoning:** `_get_*` prefix indicates they return concise strings, not build full sections

---

## Testing and Validation

### Testing Checklist

**Pre-deployment Tests:**
- [x] Run `python -m services.forecaster_7d.cli run` locally
- [x] Verify PDF generates without errors
- [x] Check all 6 charts appear with explanations
- [x] Confirm explanations directly below charts
- [x] Verify `page-break-inside: avoid` works (no splits)
- [x] Validate dynamic explanations show real data
- [x] Test styling: gray background, blue accent bar, italic text
- [x] Confirm no regression in existing sections

**Post-deployment Tests:**
- [ ] Monitor production execution on Vultr VPS
- [ ] Review generated PDFs for 3 consecutive days
- [ ] Gather user feedback on readability
- [ ] Verify no performance degradation
- [ ] Check logs for any new errors

**Edge Case Tests:**
- [ ] Test with missing RSI/MACD data (fallback text)
- [ ] Test with missing TPM/Copper data (fallback text)
- [ ] Test with missing risk regime data (fallback text)
- [ ] Test with only 2-3 charts available
- [ ] Test with very long explanations (>5 sentences)

---

## Proximos Pasos

### Alta Prioridad (Next 24 hours)

- [ ] **Deploy to Production Vultr VPS**
  ```bash
  cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
  git add src/forex_core/reporting/builder.py
  git add src/forex_core/reporting/templates/report.html.j2
  git add src/forex_core/notifications/email.py
  git commit -m "feat: Pair chart explanations with images in PDF reports"
  git push origin develop

  ssh reporting
  cd /home/deployer/forex-forecast-system
  git pull origin develop
  python -m services.forecaster_7d.cli run  # Test execution
  ```

- [ ] **Update PROJECT_STATUS.md**
  - Mark chart explanations refactor as deployed
  - Update version to 2.2.0
  - Add to changelog

- [ ] **Monitor First Production Run**
  - Check cron execution tomorrow 8 AM
  - Review generated PDF
  - Verify email delivery
  - Check logs for errors

### Media Prioridad (Next Week)

- [ ] **Gather User Feedback**
  - Share new PDFs with stakeholders
  - Ask: "Are chart explanations helpful?"
  - Ask: "Is anything confusing or missing?"
  - Iterate based on feedback

- [ ] **Add Unit Tests for New Methods**
  ```python
  # tests/unit/reporting/test_chart_blocks.py
  def test_build_chart_blocks():
      """Test chart block structure."""

  def test_get_technical_panel_explanation_with_data():
      """Test dynamic RSI/MACD explanation."""

  def test_get_technical_panel_explanation_fallback():
      """Test fallback when data missing."""
  ```

- [ ] **Refine Explanation Text**
  - Review with domain expert
  - Ensure Spanish grammar is correct
  - Optimize for non-expert readers

### Baja Prioridad (Backlog)

- [ ] **Add Source Citations to Charts**
  - Example: "Fuente: Elaboración propia con datos de Yahoo Finance, Banco Central"
  - Position below explanation box

- [ ] **Conditional Chart Rendering**
  - Hide chart block entirely if data unavailable
  - Show fallback message: "Gráfico no disponible por falta de datos"

- [ ] **Interactive Explanations (Web Dashboard)**
  - Highlight chart elements mentioned in explanation
  - Tooltip on hover showing exact values

---

## References

### Commits (Pending)
- To be committed: `feat: Pair chart explanations with images in PDF reports`

### Files Modified
- `/src/forex_core/reporting/builder.py` (Lines 93-120, 122-207, 245-286, 807-889)
- `/src/forex_core/reporting/templates/report.html.j2` (Lines 88-131, 233-244)
- `/src/forex_core/notifications/email.py` (Line 24 - import fix)

### Related Documentation
- `/docs/CHART_EXPLANATIONS_REFACTOR.md` - Implementation summary
- `/docs/sessions/SESSION_2025-11-12_REFINEMENT.md` - Date formatting session
- `/PROJECT_STATUS.md` - Overall project status

### External Resources
- [WeasyPrint CSS Page Breaks](https://doc.courtbouillon.org/weasyprint/stable/api_reference.html#css) - `page-break-inside` documentation
- [@agent-usdclp Expert System](internal) - Source of statistical insights

### Useful Commands

**Test Locally:**
```bash
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
source venv/bin/activate
python -m services.forecaster_7d.cli run --skip-email
open reports/usdclp_forecast_7d_*.pdf
```

**Deploy to Production:**
```bash
ssh reporting
cd /home/deployer/forex-forecast-system
git pull origin develop
./run_7d_forecast.sh
tail -f logs/forecaster_7d_*.log
```

**Check PDF Quality:**
```bash
# View recent PDF
ls -lth reports/ | head -3
scp reporting:/home/deployer/forex-forecast-system/reports/usdclp_forecast_7d_latest.pdf ~/Downloads/
```

---

## Before/After Comparison

### Before (Separated Charts and Text)

**PDF Structure:**
```
Page 1:
┌────────────────────────────────┐
│ [Chart 1 - Historical]         │
│ [Chart 2 - Forecast Bands]     │
│ [Chart 3 - Technical Panel]    │
└────────────────────────────────┘

Page 2:
┌────────────────────────────────┐
│ [Chart 4 - Correlation]        │
│ [Chart 5 - Macro Dashboard]    │
│ [Chart 6 - Risk Regime]        │
└────────────────────────────────┘

Page 3:
┌────────────────────────────────┐
│ ## Proyección Cuantitativa     │
│ [Forecast table]               │
│                                │
│ ## Análisis Técnico            │
│ **Análisis Técnico USD/CLP**  │
│ Este gráfico muestra tres...   │
│ (verbose explanation)          │
└────────────────────────────────┘

Page 5:
┌────────────────────────────────┐
│ **Matriz de Correlaciones**    │
│ La matriz muestra...           │
│ (verbose explanation)          │
└────────────────────────────────┘
```

**Problems:**
- Charts on pages 1-2, explanations on pages 3-5
- Reader must flip back and forth
- Explanations too verbose
- No visual pairing

---

### After (Integrated Chart Blocks)

**PDF Structure:**
```
Page 1:
┌─────────────────────────────────────┐
│ ┌─────────────────────────────────┐ │
│ │ Proyección USD/CLP              │ │
│ │ [Chart 1 - Historical]          │ │
│ │ ▌ Interpretación: Evolución...  │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Bandas de Proyección            │ │
│ │ [Chart 2 - Forecast Bands]      │ │
│ │ ▌ Interpretación: Detalle...    │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘

Page 2:
┌─────────────────────────────────────┐
│ ┌─────────────────────────────────┐ │
│ │ Análisis Técnico USD/CLP        │ │
│ │ [Chart 3 - Technical Panel]     │ │
│ │ ▌ Interpretación: Tres paneles  │ │
│ │ ▌ técnicos, RSI en neutral...   │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Matriz de Correlaciones         │ │
│ │ [Chart 4 - Correlation]         │ │
│ │ ▌ Interpretación: Relaciones... │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Improvements:**
- Chart and explanation always together
- No page flipping required
- Concise 2-3 sentence explanations
- Professional styling with visual hierarchy
- Dynamic values (RSI, TPM, regime) included

---

## Notas y Observaciones

### Key Learnings

1. **Page-break protection is critical for PDF reports**
   - HTML preview looks fine, but PDF rendering splits content
   - Always test with `page-break-inside: avoid`

2. **Balance detail and brevity in explanations**
   - Too short: readers confused
   - Too long: defeats purpose of pairing with chart
   - 2-3 sentences = sweet spot

3. **Dynamic explanations add significant value**
   - Showing "RSI in neutral (52.3)" vs "RSI shows momentum" is huge difference
   - Readers want current market context, not generic descriptions

4. **Visual hierarchy matters**
   - Blue accent bar draws eye to interpretation
   - Italic font distinguishes explanation from body text
   - Gray background separates chart blocks from sections

### Implementation Notes

- Chart blocks are rendered at top of PDF (before body sections)
- Explanation methods have fallback text if data unavailable
- No performance impact (explanations computed during report build)
- Backward compatible (no breaking changes to pipeline)

### Future Considerations

- Consider adding chart source citations below explanations
- Could add "Key Insight" box for most important charts
- May want to make explanations configurable (verbose/concise mode)
- Could internationalize explanations (Spanish/English toggle)

---

## Tags

`feature` `pdf-reports` `chart-explanations` `ux-improvement` `refactor` `statistical-insights`

---

**Generated by:** session-doc-keeper skill
**Session Type:** Feature Enhancement
**Reviewed by:** [Pending]
**Deployed:** [Pending - 2025-11-12]
