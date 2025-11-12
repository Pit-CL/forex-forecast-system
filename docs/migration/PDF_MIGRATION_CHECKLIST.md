# PDF Reporting Migration Checklist

**Date:** 2025-11-12
**Purpose:** Track migration progress and ensure nothing is missed

---

## Pre-Migration Setup

### Environment Setup

- [ ] Install Cairo and Pango system libraries
  - [ ] Ubuntu/Debian: `apt-get install libpangocairo-1.0-0 libcairo2`
  - [ ] macOS: `brew install cairo pango gdk-pixbuf libffi`
- [ ] Install Python dependencies
  - [ ] `pip install weasyprint>=62.3 cairocffi>=1.7`
  - [ ] `pip install matplotlib>=3.9 seaborn>=0.13`
  - [ ] `pip install jinja2>=3.1 markdown>=3.6`
  - [ ] `pip install reportlab>=4.1` (optional)
- [ ] Verify WeasyPrint works: `python -c "from weasyprint import HTML; print('OK')"`
- [ ] Create backup of legacy code
- [ ] Set up test data from all three services (7d, 12m, importer)

### Documentation Review

- [ ] Read PDF_REPORTING_MIGRATION.md (full technical guide)
- [ ] Read PDF_COMPARISON_MATRIX.md (feature comparison)
- [ ] Read PDF_QUICK_REFERENCE.md (quick start guide)
- [ ] Read PDF_MIGRATION_SUMMARY.md (executive summary)
- [ ] Understand differences between 7d, 12m, and importer systems

---

## Week 1: Core Infrastructure

### Day 1-2: Chart Generation

- [ ] Create `forex_core/reporting/config.py`
  - [ ] Define `ChartConfig` dataclass
  - [ ] Define `ReportConfig` dataclass
  - [ ] Add validation methods
- [ ] Create `forex_core/reporting/charting.py`
  - [ ] Migrate `generate_charts()` from 7d
  - [ ] Add horizon parameterization (7d, 12m, monthly)
  - [ ] Migrate advanced charts from importer `visuals.py`
  - [ ] Add `image_to_base64()` utility
  - [ ] Add chart validation
- [ ] Write unit tests for charting
  - [ ] Test 7d chart generation
  - [ ] Test 12m chart generation
  - [ ] Test importer chart generation
  - [ ] Test chart dimensions and DPI
  - [ ] Test base64 encoding
  - [ ] Test file sizes

### Day 3-4: PDF Rendering

- [ ] Create `forex_core/reporting/pdf_weasy.py`
  - [ ] Migrate `PdfRenderer` from 7d/12m
  - [ ] Add error detection for WeasyPrint
  - [ ] Add Spanish character support validation
  - [ ] Add PDF metadata support
  - [ ] Add fallback to markdown
- [ ] Create `forex_core/reporting/templates/base.html.j2`
  - [ ] Migrate HTML structure from 7d/12m
  - [ ] Add CSS styling
  - [ ] Add UTF-8 charset
  - [ ] Test Spanish characters
- [ ] (Optional) Create `forex_core/reporting/pdf_reportlab.py`
  - [ ] Migrate `pdf_builder.py` from importer
  - [ ] Add cover page support
  - [ ] Add table of contents
  - [ ] Add page numbers
- [ ] Write unit tests for PDF rendering
  - [ ] Test WeasyPrint HTML-to-PDF
  - [ ] Test Spanish characters (á, é, í, ó, ú, ñ)
  - [ ] Test multi-page PDFs
  - [ ] Test PDF metadata
  - [ ] Test file sizes
  - [ ] Test PDF opens in readers

### Day 5: Initial Integration

- [ ] Create simple end-to-end test
- [ ] Generate 7d PDF with test data
- [ ] Generate 12m PDF with test data
- [ ] Validate PDFs manually
- [ ] Fix any critical issues
- [ ] Commit and push Week 1 progress

---

## Week 2: Section Splitting

### Day 1-2: Section Base Classes

- [ ] Create `forex_core/reporting/sections/__init__.py`
- [ ] Create `forex_core/reporting/sections/base.py`
  - [ ] Define `Section` abstract base class
  - [ ] Define `SectionContent` dataclass
  - [ ] Add `to_markdown()` method
  - [ ] Add word limit enforcement
- [ ] Create `forex_core/reporting/sections/forecast.py`
  - [ ] Migrate projection table generation
  - [ ] Add date formatting (Spanish)
  - [ ] Add horizon-specific labels
- [ ] Create `forex_core/reporting/sections/executive.py`
  - [ ] Migrate interpretation logic
  - [ ] Add trend classification
  - [ ] Add confidence scoring
- [ ] Write unit tests for sections
  - [ ] Test forecast section with 7d data
  - [ ] Test forecast section with 12m data
  - [ ] Test executive section
  - [ ] Test word limits

### Day 3-4: More Sections

- [ ] Create `forex_core/reporting/sections/technical.py`
  - [ ] Migrate technical indicators table
  - [ ] Add RSI, MACD, MA, support, resistance
- [ ] Create `forex_core/reporting/sections/fundamental.py`
  - [ ] Migrate drivers ranking logic
  - [ ] Migrate quantitative factors table
  - [ ] Add source citations
- [ ] Create `forex_core/reporting/sections/macro.py`
  - [ ] Migrate importer-specific sections
  - [ ] Add PESTEL matrix
  - [ ] Add Porter's 5 Forces
  - [ ] Add scenario tables
- [ ] Write unit tests for new sections
  - [ ] Test technical section
  - [ ] Test fundamental section
  - [ ] Test macro section (importer)

### Day 5: Unified Builder

- [ ] Create `forex_core/reporting/builder.py`
  - [ ] Implement `ReportBuilder` class
  - [ ] Add horizon detection and configuration
  - [ ] Add section initialization based on horizon
  - [ ] Add markdown body assembly
  - [ ] Add HTML rendering
  - [ ] Add PDF generation with error handling
  - [ ] Add validation
- [ ] Write integration tests
  - [ ] Test 7d full report generation
  - [ ] Test 12m full report generation
  - [ ] Test importer full report generation
  - [ ] Test with empty data
  - [ ] Test with missing fields
- [ ] Commit and push Week 2 progress

---

## Week 3: Email and Validation

### Day 1-2: Email Service

- [ ] Create `forex_core/notifications/__init__.py`
- [ ] Create `forex_core/notifications/email.py`
  - [ ] Migrate from importer `email_client.py` (more robust)
  - [ ] Add TLS and SSL support
  - [ ] Add MIME type detection
  - [ ] Add attachment handling
  - [ ] Add error handling
- [ ] Write unit tests for email
  - [ ] Test email message building
  - [ ] Test MIME type detection
  - [ ] Test attachment handling
  - [ ] (Skip) Integration test with real SMTP (requires setup)

### Day 3-4: Validation

- [ ] Create `forex_core/reporting/validation.py`
  - [ ] Implement `validate_pdf()` function
    - [ ] Check file exists
    - [ ] Check file size (50 KB - 5 MB)
    - [ ] Check can be opened (with PyPDF2 or similar)
    - [ ] Check has content
  - [ ] Implement `validate_chart()` function
    - [ ] Check file exists
    - [ ] Check image not corrupted
    - [ ] Check dimensions (min 600x300)
    - [ ] Check file size (>10 KB)
  - [ ] Add `ValidationResult` dataclass
- [ ] Integrate validation into builder
  - [ ] Validate charts after generation
  - [ ] Validate PDF after generation
  - [ ] Log validation failures
  - [ ] Optionally raise on validation failure
- [ ] Write tests for validation
  - [ ] Test valid PDF passes
  - [ ] Test invalid PDF fails
  - [ ] Test valid chart passes
  - [ ] Test invalid chart fails

### Day 5: End-to-End Tests

- [ ] Create comprehensive integration tests
  - [ ] Test full 7d pipeline (data → charts → PDF → email)
  - [ ] Test full 12m pipeline
  - [ ] Test full importer pipeline
  - [ ] Test error handling (missing data)
  - [ ] Test error handling (WeasyPrint failure)
  - [ ] Test fallback to markdown
- [ ] Test with real production data samples
- [ ] Validate output manually in PDF readers
- [ ] Commit and push Week 3 progress

---

## Week 4: Advanced Features and Polish

### Day 1-2: Importer-Specific Charts

- [ ] Extend `charting.py` with importer charts
  - [ ] Scatter plot (Copper vs CLP/USD) with regression
  - [ ] Bar chart (Retail confidence)
  - [ ] Overlay chart (Freight + congestion)
  - [ ] Risk map (horizontal bar chart)
  - [ ] Forecast overlay charts (SARIMAX, ML)
- [ ] Test importer-specific charts
  - [ ] Generate all 9 charts
  - [ ] Validate dimensions and quality
  - [ ] Validate data visualization

### Day 3-4: Optional Enhancements

- [ ] Add page numbers to WeasyPrint PDFs
  - [ ] Research CSS `@page` rules
  - [ ] Implement page counter
  - [ ] Test with multi-page PDFs
- [ ] Add table of contents to WeasyPrint PDFs
  - [ ] Generate section list
  - [ ] Add ToC template
  - [ ] Add page links (if possible)
- [ ] Add cover page to WeasyPrint PDFs
  - [ ] Create cover template
  - [ ] Add report title and date
  - [ ] Add branding (optional)
- [ ] Optimize performance
  - [ ] Profile chart generation
  - [ ] Profile PDF generation
  - [ ] Optimize slow sections
  - [ ] Add timing logs

### Day 5: Final Validation

- [ ] Run full test suite
  - [ ] Unit tests (all passing)
  - [ ] Integration tests (all passing)
  - [ ] Visual regression tests (if implemented)
- [ ] Generate sample reports from all three services
- [ ] Validate Spanish characters in all PDFs
- [ ] Validate charts in all PDFs
- [ ] Compare with legacy reports (visual inspection)
- [ ] Performance benchmarks
  - [ ] 7d report generation time: <15s
  - [ ] 12m report generation time: <20s
  - [ ] Importer report generation time: <30s
  - [ ] Memory usage: <200 MB
- [ ] Update documentation
  - [ ] Add API documentation (docstrings)
  - [ ] Update README
  - [ ] Add examples
- [ ] Commit and push final version

---

## Migration Completion

### Code Review

- [ ] Request code review from team
- [ ] Address review comments
- [ ] Ensure test coverage >90%
- [ ] Ensure all docstrings present
- [ ] Ensure type hints present
- [ ] Ensure no linting errors

### Deployment Preparation

- [ ] Update `requirements.txt` with new dependencies
- [ ] Update Dockerfile with Cairo/Pango dependencies
- [ ] Update docker-compose.yml if needed
- [ ] Test Docker build
- [ ] Test Docker run with mounted volumes
- [ ] Prepare deployment scripts
- [ ] Document deployment process

### Service Migration

#### 7d Service

- [ ] Update imports to use `forex_core.reporting`
- [ ] Update configuration
- [ ] Run tests
- [ ] Generate sample report
- [ ] Deploy to staging
- [ ] Validate in staging
- [ ] Deploy to production
- [ ] Monitor for 24 hours
- [ ] Mark as migrated

#### 12m Service

- [ ] Update imports to use `forex_core.reporting`
- [ ] Update configuration
- [ ] Run tests
- [ ] Generate sample report
- [ ] Deploy to staging
- [ ] Validate in staging
- [ ] Deploy to production
- [ ] Monitor for 24 hours
- [ ] Mark as migrated

#### Importer Service

- [ ] Update imports to use `forex_core.reporting`
- [ ] Update configuration (use ReportConfig with horizon="monthly")
- [ ] Run tests
- [ ] Generate sample report
- [ ] Deploy to staging
- [ ] Validate in staging
- [ ] Deploy to production
- [ ] Monitor for 24 hours
- [ ] Mark as migrated

---

## Post-Migration

### Monitoring

- [ ] Set up PDF generation monitoring
  - [ ] Alert on failures
  - [ ] Alert on slow generation (>30s)
  - [ ] Alert on large files (>5 MB)
  - [ ] Alert on validation failures
- [ ] Monitor email delivery
  - [ ] Track send success rate
  - [ ] Track delivery failures
- [ ] Monitor error logs
  - [ ] Check for WeasyPrint errors
  - [ ] Check for chart generation errors

### Documentation

- [ ] Update main project README
- [ ] Add migration notes to CHANGELOG
- [ ] Archive legacy code
- [ ] Update API documentation
- [ ] Add troubleshooting guide

### Cleanup

- [ ] Remove deprecated imports from services
- [ ] Archive legacy report modules (after 1 month stability)
- [ ] Remove duplicate code
- [ ] Update CI/CD pipelines
- [ ] Update deployment scripts

### Retrospective

- [ ] Document lessons learned
- [ ] Document issues encountered
- [ ] Document solutions implemented
- [ ] Update migration estimates for future projects
- [ ] Share knowledge with team

---

## Rollback Checklist (If Needed)

### Immediate Rollback (<1 hour)

- [ ] Identify critical failure
- [ ] Alert stakeholders
- [ ] Switch services to markdown backup mode
  - [ ] Set `SKIP_PDF=true` environment variable
  - [ ] Restart services
- [ ] Verify reports still generated (as markdown)
- [ ] Monitor for stability

### Short-Term Rollback (<1 day)

- [ ] Revert to legacy Docker images
  - [ ] 7d: `docker-compose up -d` in `deployment/7d`
  - [ ] 12m: `docker-compose up -d` in `deployment/12m`
  - [ ] Importer: `docker-compose up -d` in `importer_macro_report`
- [ ] Verify legacy services working
- [ ] Generate test reports from legacy services
- [ ] Notify team of rollback

### Post-Rollback

- [ ] Analyze root cause of failure
- [ ] Fix issues in development
- [ ] Test fixes thoroughly
- [ ] Plan re-migration timeline
- [ ] Update migration checklist with lessons learned

---

## Risk Mitigation Checklist

### Technical Risks

- [ ] WeasyPrint dependencies installed and tested
- [ ] Fallback to markdown implemented and tested
- [ ] Error handling comprehensive
- [ ] Validation catches common issues
- [ ] Tests cover edge cases

### Business Risks

- [ ] Sample reports reviewed by stakeholders
- [ ] Spanish characters validated
- [ ] Chart quality acceptable
- [ ] Report content complete
- [ ] No data loss in migration

### Operational Risks

- [ ] Deployment process documented
- [ ] Rollback plan tested
- [ ] Monitoring in place
- [ ] Team trained on new system
- [ ] Support process defined

---

## Success Metrics Checklist

### Quantitative Metrics

- [ ] PDF generation success rate: >99.5%
  - [ ] 7d: _____%
  - [ ] 12m: _____%
  - [ ] Importer: _____%
- [ ] PDF generation time: <3s average
  - [ ] 7d: _____ seconds
  - [ ] 12m: _____ seconds
  - [ ] Importer: _____ seconds
- [ ] Chart generation time: <2s average
  - [ ] 7d: _____ seconds
  - [ ] 12m: _____ seconds
  - [ ] Importer: _____ seconds
- [ ] File sizes within range (50 KB - 5 MB)
  - [ ] 7d: _____ KB
  - [ ] 12m: _____ KB
  - [ ] Importer: _____ KB
- [ ] Memory usage: <200 MB peak
  - [ ] 7d: _____ MB
  - [ ] 12m: _____ MB
  - [ ] Importer: _____ MB
- [ ] Test coverage: >90%
  - [ ] Current: _____%

### Qualitative Metrics

- [ ] PDFs open in all major readers (Adobe, Chrome, Preview)
- [ ] Charts are visually clear and readable
- [ ] Tables are properly formatted
- [ ] Spanish text renders correctly (no boxes or garbled text)
- [ ] Formatting is consistent across horizons
- [ ] Error messages are clear and actionable

---

## Sign-Off

### Development Team

- [ ] Developer 1: _________________________ Date: _________
- [ ] Developer 2: _________________________ Date: _________
- [ ] Code Reviewer: ______________________ Date: _________

### QA Team

- [ ] QA Tester 1: _________________________ Date: _________
- [ ] QA Tester 2: _________________________ Date: _________

### Product/Business

- [ ] Product Owner: _______________________ Date: _________
- [ ] Stakeholder 1: _______________________ Date: _________

### Final Approval

- [ ] Tech Lead: ___________________________ Date: _________
- [ ] Project Manager: _____________________ Date: _________

---

## Notes

Use this section to track issues, decisions, and important information during migration:

```
Date: ___________
Issue:
Solution:

Date: ___________
Issue:
Solution:

Date: ___________
Decision:
Rationale:
```

---

**Last Updated:** 2025-11-12
**Version:** 1.0
**Status:** Ready for Use

**Instructions:**
1. Print or copy this checklist
2. Check off items as you complete them
3. Add notes for any issues encountered
4. Update dates and signatures
5. Archive completed checklist with project documentation
