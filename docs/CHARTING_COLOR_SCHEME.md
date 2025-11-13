# Charting Color Scheme - USD/CLP Forecast System

## Official Color Palette

### Confidence Interval Colors

| Element | Color Name | Hex Code | RGB | Alpha | Usage |
|---------|-----------|----------|-----|-------|-------|
| IC 80% Band | DarkOrange | `#FF8C00` | (255, 140, 0) | 0.35 | More probable range (80% confidence) |
| IC 95% Band | DarkViolet | `#8B00FF` | (139, 0, 255) | 0.25 | Extended range (95% confidence) |

### Line Colors

| Element | Color Name | Hex Code | RGB | Width | Usage |
|---------|-----------|----------|-----|-------|-------|
| Historical Data | Steel Blue | `#1f77b4` | (31, 119, 180) | 2 | Past USD/CLP data (Chart 1) |
| Forecast Mean | Crimson Red | `#d62728` | (214, 39, 40) | 2 | Central projection (Chart 1) |
| Forecast Mean | Green | `#2ca02c` | (44, 160, 44) | 2 | Central projection (Chart 2) |

## Visual Specification

### Chart 1: Historical + Forecast

```
Historical Data (Blue) ━━━━┓
                            ┃
                            ┃  Forecast Mean (Red) ━━━━━━━
                            ┃  ╱╱╱╱╱╱ 80% CI (Orange) ╱╱╱╱╱
                            ┃  ░░░░░ 95% CI (Violet) ░░░░░
                            ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━►
                          Today                       +7d
```

### Chart 2: Forecast Intervals Only

```
    Mean (Green) ━━━━━━━━━━━━━━━━━━━
    ╱╱╱╱╱╱╱ 80% CI (Orange) ╱╱╱╱╱╱╱╱
    ░░░░░░ 95% CI (Violet) ░░░░░░░░
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━►
    Today                      +7d
```

## Color Psychology & Rationale

### Why Orange for 80% CI?
- **Attention-grabbing:** Orange naturally draws the eye
- **Warm color:** Suggests "more probable/closer" range
- **High contrast:** Stands out against blue historical data
- **Industry standard:** Commonly used in finance for primary confidence bands

### Why Violet for 95% CI?
- **Cool color:** Suggests "extended/outer" range
- **Distinctive:** Clearly different from orange, no confusion possible
- **Professional:** Purple/violet conveys sophistication in financial reporting
- **Accessibility:** Good contrast for most forms of color blindness when paired with orange

### Alpha Transparency Values

| Band | Alpha | Rationale |
|------|-------|-----------|
| 80% | 0.35 | More opaque to emphasize higher probability range |
| 95% | 0.25 | More transparent to show it's a wider, less certain range |

## Implementation Reference

### Matplotlib Code

```python
# Chart 1 & 2: Confidence Intervals
ax.fill_between(
    dates,
    ci_80_low,
    ci_80_high,
    color="#FF8C00",  # DarkOrange
    alpha=0.35,
    label="IC 80%",
    zorder=2
)

ax.fill_between(
    dates,
    ci_95_low,
    ci_95_high,
    color="#8B00FF",  # DarkViolet
    alpha=0.25,
    label="IC 95%",
    zorder=1
)
```

### Z-order Layering
1. **Background:** 95% CI (violet, z=1)
2. **Middle:** 80% CI (orange, z=2)
3. **Foreground:** Mean line (z=3)

## Text Descriptions

### Spanish (for PDF reports)
- "La banda naranja (IC 80%) muestra el rango más probable"
- "La banda violeta (IC 95%) captura escenarios extremos"

### English (for international reports)
- "The orange band (80% CI) shows the most probable range"
- "The violet band (95% CI) captures extreme scenarios"

## Accessibility Considerations

### Color Blindness Compatibility

| Type | Affected % | Orange Visible? | Violet Visible? | Distinguishable? |
|------|-----------|----------------|-----------------|------------------|
| Protanopia (Red-blind) | ~1% | Brownish | Blue-ish | ✅ Yes |
| Deuteranopia (Green-blind) | ~1% | Yellow-ish | Purple-ish | ✅ Yes |
| Tritanopia (Blue-blind) | ~0.01% | Orange | Pink-ish | ⚠️ Similar |

**Recommendation:** Current scheme works for 98%+ of users. If tritanopia support needed, consider Orange + Blue instead.

## Testing Checklist

Before releasing charts, verify:

- [ ] 80% CI band appears ORANGE (not red, not pink, not green)
- [ ] 95% CI band appears VIOLET (not blue, not green, not light purple)
- [ ] Both bands are clearly visible (not too transparent)
- [ ] Bands are distinguishable from each other
- [ ] Legend labels match actual colors
- [ ] Text descriptions mention "naranja" and "violeta"
- [ ] PDF renders colors correctly when printed

## Version History

| Date | Version | Change |
|------|---------|--------|
| 2025-11-12 | 1.0 | Initial specification after fixing green/pink bug |

## Contact

For color scheme questions or changes, contact: Forex Forecast System Team
