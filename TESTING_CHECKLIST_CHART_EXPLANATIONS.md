# Testing Checklist - Chart Explanations Enhancement

**Version:** 2.2.0
**Feature:** Chart explanations paired with images
**Status:** Ready for Testing

---

## Pre-Deployment Tests (Local)

### Functionality Tests

- [x] **PDF Generation**
  ```bash
  python -m services.forecaster_7d.cli run --skip-email
  ```
  - [x] Command executes without errors
  - [x] PDF file created in `reports/` directory
  - [x] PDF opens without corruption

- [x] **Chart Blocks Structure**
  - [x] All 6 charts present in PDF
  - [x] Each chart has title above it
  - [x] Each chart has explanation below it
  - [x] Explanations start with "Interpretación:"

- [x] **Page Break Protection**
  - [x] No chart split from its title
  - [x] No chart split from its explanation
  - [x] Chart blocks contained in single page when possible

- [x] **Dynamic Explanations**
  - [x] Technical Panel shows RSI value (e.g., "RSI en neutral (52.3)")
  - [x] Technical Panel shows MACD status ("momentum positivo/negativo")
  - [x] Macro Dashboard shows copper price (e.g., "Cobre (4.15 USD/lb)")
  - [x] Macro Dashboard shows TPM rate (e.g., "TPM (5.75%)")
  - [x] Risk Regime shows regime status ("Risk-On/Risk-Off/Mixto")
  - [x] Risk Regime shows percentage changes (e.g., "DXY +1.2%")

- [x] **Styling Verification**
  - [x] Chart blocks have gray background (#f9fafb)
  - [x] Chart titles are bold blue (#1e5a96, 13pt)
  - [x] Explanations have blue left border (4px solid #4299e1)
  - [x] Explanation text is italic (10pt, #4a5568)
  - [x] Explanation background is white (#ffffff)

---

### Edge Case Tests

- [ ] **Missing Data Handling**
  ```bash
  # Test with network issues or API failures
  # Temporarily disable internet to simulate
  ```
  - [ ] Technical Panel fallback text appears when RSI/MACD unavailable
  - [ ] Macro Dashboard fallback text appears when Copper/TPM unavailable
  - [ ] Risk Regime fallback text appears when regime data unavailable
  - [ ] PDF still generates (no crashes)

- [ ] **Long Explanations**
  - [ ] Explanations wrap correctly within chart block
  - [ ] No overflow beyond container
  - [ ] Readability maintained

- [ ] **Chart Order**
  - [ ] Charts appear in correct sequence:
    1. Historical + Forecast
    2. Forecast Bands
    3. Technical Panel
    4. Correlation Matrix
    5. Macro Dashboard
    6. Risk Regime

---

### Regression Tests

- [x] **Existing Sections Intact**
  - [x] Executive Summary still present
  - [x] Forecast Table still present
  - [x] Technical Analysis section still present
  - [x] Risk Regime section still present
  - [x] Fundamental Factors section still present
  - [x] Methodology section still present
  - [x] Conclusion section still present

- [x] **No Duplicate Content**
  - [x] Chart explanations don't duplicate body text
  - [x] No verbose explanations in body sections
  - [x] Clean separation between charts and analysis

- [x] **Performance**
  - [x] Execution time ~30-35 seconds (no significant increase)
  - [x] Memory usage ~500 MB (no significant increase)
  - [x] PDF file size ~1.2-1.5 MB (no significant increase)

---

### Code Quality Tests

- [ ] **Type Checking**
  ```bash
  mypy src/forex_core/reporting/builder.py
  ```
  - [ ] No type errors
  - [ ] All type hints valid

- [ ] **Linting**
  ```bash
  flake8 src/forex_core/reporting/builder.py
  flake8 src/forex_core/notifications/email.py
  ```
  - [ ] No PEP 8 violations (or only minor ones)
  - [ ] No unused imports
  - [ ] No undefined variables

- [ ] **Unit Tests (To Be Written)**
  ```bash
  pytest tests/unit/reporting/test_chart_blocks.py -v
  ```
  - [ ] `test_build_chart_blocks_structure()`
  - [ ] `test_get_technical_panel_explanation_with_data()`
  - [ ] `test_get_technical_panel_explanation_fallback()`
  - [ ] `test_get_macro_dashboard_explanation_with_data()`
  - [ ] `test_get_macro_dashboard_explanation_fallback()`
  - [ ] `test_get_regime_explanation_with_data()`
  - [ ] `test_get_regime_explanation_fallback()`

---

## Deployment Tests (Vultr VPS)

### Pre-Deployment

- [ ] **Code Sync**
  ```bash
  ssh reporting
  cd /home/deployer/forex-forecast-system
  git status  # Should show clean working tree
  git pull origin main  # Should pull latest changes
  ```
  - [ ] Git pull successful
  - [ ] No merge conflicts
  - [ ] Latest code deployed

- [ ] **Dependencies**
  ```bash
  source venv/bin/activate
  pip install -r requirements.txt
  ```
  - [ ] All dependencies installed
  - [ ] No version conflicts

---

### Manual Test Run

- [ ] **Execute Pipeline (Skip Email)**
  ```bash
  python -m services.forecaster_7d.cli run --skip-email
  ```
  - [ ] Command completes successfully
  - [ ] PDF generated in `reports/` directory
  - [ ] Log file shows no errors
  - [ ] Execution time ~30-35 seconds

- [ ] **PDF Quality Check**
  ```bash
  ls -lth reports/ | head -3
  # Download PDF to local machine
  scp reporting:/home/deployer/forex-forecast-system/reports/usdclp_forecast_7d_*.pdf ~/Downloads/
  ```
  - [ ] PDF file size ~1.2-1.5 MB
  - [ ] PDF opens correctly
  - [ ] All 6 charts visible
  - [ ] Explanations below each chart
  - [ ] No page breaks between chart/explanation
  - [ ] Styling correct (gray boxes, blue accents)
  - [ ] Dynamic values present (RSI, TPM, regime)

- [ ] **Log Review**
  ```bash
  tail -n 100 logs/forecaster_7d_*.log
  ```
  - [ ] No ERROR or CRITICAL messages
  - [ ] INFO messages show normal flow
  - [ ] Chart generation logged
  - [ ] Report building logged

---

### Full Pipeline Test (With Email)

- [ ] **Execute Full Pipeline**
  ```bash
  python -m services.forecaster_7d.cli run
  ```
  - [ ] Command completes successfully
  - [ ] PDF generated
  - [ ] Email sent (check logs)

- [ ] **Email Verification**
  - [ ] Email received at configured addresses
  - [ ] Subject line correct: "Proyección USD/CLP (7 días) - Forex Forecast System"
  - [ ] PDF attached
  - [ ] PDF opens correctly from email
  - [ ] Email body contains summary

---

### Cron Execution Test

- [ ] **Wait for Next Scheduled Run**
  ```bash
  # Check cron schedule
  crontab -l | grep forecast

  # Monitor logs during scheduled run (8 AM Chile time)
  tail -f logs/cron_7d.log
  ```
  - [ ] Cron executes at scheduled time
  - [ ] PDF generated successfully
  - [ ] Email sent successfully
  - [ ] No errors in cron log

---

## Post-Deployment Monitoring (7 Days)

### Daily Checks

**Day 1:**
- [ ] Cron executed successfully
- [ ] PDF quality verified
- [ ] Email delivered
- [ ] No errors in logs

**Day 2:**
- [ ] Cron executed successfully
- [ ] PDF quality verified
- [ ] Email delivered
- [ ] No errors in logs

**Day 3:**
- [ ] Cron executed successfully
- [ ] PDF quality verified
- [ ] Email delivered
- [ ] No errors in logs

**Day 4:**
- [ ] Cron executed successfully
- [ ] PDF quality verified
- [ ] Email delivered
- [ ] No errors in logs

**Day 5:**
- [ ] Cron executed successfully
- [ ] PDF quality verified
- [ ] Email delivered
- [ ] No errors in logs

**Day 6:**
- [ ] Cron executed successfully
- [ ] PDF quality verified
- [ ] Email delivered
- [ ] No errors in logs

**Day 7:**
- [ ] Cron executed successfully
- [ ] PDF quality verified
- [ ] Email delivered
- [ ] No errors in logs

---

### Weekly Review Checklist

- [ ] **Execution Reliability**
  - [ ] 7/7 successful executions
  - [ ] No failures or retries
  - [ ] Consistent execution time

- [ ] **PDF Quality**
  - [ ] All charts rendering correctly every day
  - [ ] Dynamic values changing appropriately (RSI, TPM vary)
  - [ ] No formatting issues observed
  - [ ] Page breaks working correctly

- [ ] **User Feedback**
  - [ ] Stakeholders received emails
  - [ ] No complaints about readability
  - [ ] Positive feedback on explanations (if any)
  - [ ] Feature enhancement requests (if any)

- [ ] **Performance Metrics**
  - [ ] Average execution time: _____ seconds
  - [ ] Average PDF size: _____ MB
  - [ ] Average memory usage: _____ MB
  - [ ] No degradation observed

---

## Rollback Criteria

**Execute rollback if:**
- [ ] PDF generation fails 2+ consecutive times
- [ ] Chart explanations missing or incorrect
- [ ] Page breaks between chart/explanation observed
- [ ] Performance degradation >20% (execution time >42 seconds)
- [ ] Critical user complaints about readability

**Rollback Procedure:**
```bash
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
git revert <commit-hash>
git push origin main

ssh reporting
cd /home/deployer/forex-forecast-system
git pull origin main
python -m services.forecaster_7d.cli run --skip-email  # Test
```

---

## Sign-Off

### Pre-Deployment Sign-Off
- [ ] All pre-deployment tests passed
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] Rollback plan in place

**Tested by:** _______________
**Date:** _______________
**Approved by:** _______________

---

### Post-Deployment Sign-Off
- [ ] All deployment tests passed
- [ ] 7-day monitoring complete
- [ ] No critical issues
- [ ] Feature working as expected

**Verified by:** _______________
**Date:** _______________
**Status:** PRODUCTION STABLE / ROLLBACK REQUIRED

---

## Quick Reference Commands

**Local Test:**
```bash
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
source venv/bin/activate
python -m services.forecaster_7d.cli run --skip-email
open reports/usdclp_forecast_7d_*.pdf
```

**Production Test:**
```bash
ssh reporting
cd /home/deployer/forex-forecast-system
python -m services.forecaster_7d.cli run --skip-email
ls -lth reports/ | head -3
```

**View Logs:**
```bash
ssh reporting
tail -f /home/deployer/forex-forecast-system/logs/forecaster_7d_*.log
```

**Download PDF:**
```bash
scp reporting:/home/deployer/forex-forecast-system/reports/usdclp_forecast_7d_latest.pdf ~/Downloads/
```

---

**Document Status:** Complete
**Version:** 1.0
**Last Updated:** 2025-11-12
