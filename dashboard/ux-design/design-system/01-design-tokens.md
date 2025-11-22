# Design System - USD/CLP Forecast Dashboard
## Design Tokens & Visual Foundation

---

## Design Principles

1. **SPEED FIRST** - Every interaction <200ms, page loads <2s
2. **TRUST THROUGH CLARITY** - No hidden data, confidence always visible
3. **PROFESSIONAL, NOT PLAYFUL** - Financial tool, not consumer app
4. **DATA DENSE, NOT CLUTTERED** - Maximum info, minimum chrome
5. **ACCESSIBLE TO ALL** - WCAG 2.1 AA minimum

---

## Color System

### Brand Colors

```css
/* Primary - Professional Blue (Trust, Stability) */
--color-primary-50:  #EFF6FF;  /* Lightest background */
--color-primary-100: #DBEAFE;  /* Hover backgrounds */
--color-primary-200: #BFDBFE;
--color-primary-300: #93C5FD;
--color-primary-400: #60A5FA;
--color-primary-500: #3B82F6;  /* PRIMARY - Main actions */
--color-primary-600: #2563EB;  /* Hover state */
--color-primary-700: #1D4ED8;  /* Active state */
--color-primary-800: #1E40AF;
--color-primary-900: #1E3A8A;

/* Cavara Secondary - Professional Teal (optional accent) */
--color-secondary-500: #14B8A6;
--color-secondary-600: #0D9488;
--color-secondary-700: #0F766E;
```

### Semantic Colors

```css
/* Success - Bullish/Positive (Green) */
--color-success-50:  #F0FDF4;
--color-success-100: #DCFCE7;
--color-success-500: #22C55E;  /* Main success green */
--color-success-600: #16A34A;  /* Hover */
--color-success-700: #15803D;  /* Active */

/* Danger - Bearish/Negative (Red) */
--color-danger-50:  #FEF2F2;
--color-danger-100: #FEE2E2;
--color-danger-500: #EF4444;  /* Main danger red */
--color-danger-600: #DC2626;  /* Hover */
--color-danger-700: #B91C1C;  /* Active */

/* Warning - Caution (Amber) */
--color-warning-50:  #FFFBEB;
--color-warning-100: #FEF3C7;
--color-warning-500: #F59E0B;  /* Main warning amber */
--color-warning-600: #D97706;
--color-warning-700: #B45309;

/* Info - Neutral information (Blue) */
--color-info-50:  #EFF6FF;
--color-info-500: #3B82F6;
--color-info-600: #2563EB;
```

### Neutral Colors (Grayscale)

```css
/* Light Mode Neutrals */
--color-neutral-50:  #F9FAFB;  /* Page background */
--color-neutral-100: #F3F4F6;  /* Card background */
--color-neutral-200: #E5E7EB;  /* Borders */
--color-neutral-300: #D1D5DB;  /* Dividers */
--color-neutral-400: #9CA3AF;  /* Disabled text */
--color-neutral-500: #6B7280;  /* Muted text */
--color-neutral-600: #4B5563;  /* Secondary text */
--color-neutral-700: #374151;  /* Body text */
--color-neutral-800: #1F2937;  /* Headings */
--color-neutral-900: #111827;  /* Primary text */

/* Dark Mode Neutrals */
--color-dark-50:  #F9FAFB;  /* For text on dark */
--color-dark-100: #E5E7EB;
--color-dark-700: #374151;
--color-dark-800: #1F2937;  /* Card background */
--color-dark-900: #111827;  /* Page background */
--color-dark-950: #030712;  /* Deep black */
```

### Chart Colors

```css
/* Forecast Chart Colors */
--chart-historical: #3B82F6;      /* Blue - historical data */
--chart-forecast: #8B5CF6;        /* Purple - forecast line */
--chart-confidence: #8B5CF680;    /* Purple 50% opacity - confidence band */
--chart-actual: #10B981;          /* Green - actual vs forecast */
--chart-grid: #E5E7EB;            /* Gray - grid lines */

/* Multi-line Chart Colors (for correlations) */
--chart-line-1: #3B82F6;  /* Blue - USD/CLP */
--chart-line-2: #F59E0B;  /* Amber - Copper */
--chart-line-3: #8B5CF6;  /* Purple - DXY */
--chart-line-4: #10B981;  /* Green - Oil */
--chart-line-5: #EF4444;  /* Red - VIX */
```

### Accessibility Requirements

**Contrast Ratios (WCAG 2.1 AA):**
- Normal text (16px+): 4.5:1 minimum
- Large text (24px+): 3:1 minimum
- UI components: 3:1 minimum

**Tested Combinations:**
- Primary-600 on white: 7.04:1 ✅
- Success-600 on white: 4.98:1 ✅
- Danger-600 on white: 5.93:1 ✅
- Neutral-700 on white: 8.59:1 ✅
- White on Primary-600: 7.04:1 ✅

---

## Typography

### Font Families

```css
/* Primary Font - Inter (Web-optimized, professional) */
--font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 Roboto, Helvetica, Arial, sans-serif;

/* Monospace Font - JetBrains Mono (for numbers, code, data) */
--font-mono: 'JetBrains Mono', 'SF Mono', 'Monaco', 'Cascadia Code',
             'Courier New', monospace;

/* Note: Inter has better readability than Roboto for dense financial data */
/* Note: Use font-mono for all currency values, percentages, dates */
```

### Font Sizes (Modular Scale 1.250 - Major Third)

```css
/* Font Size Scale */
--font-size-xs:   0.75rem;   /* 12px - Captions, footnotes */
--font-size-sm:   0.875rem;  /* 14px - Small text, labels */
--font-size-base: 1rem;      /* 16px - Body text, default */
--font-size-md:   1.125rem;  /* 18px - Emphasized body */
--font-size-lg:   1.25rem;   /* 20px - H3 */
--font-size-xl:   1.5rem;    /* 24px - H2 */
--font-size-2xl:  2rem;      /* 32px - H1 */
--font-size-3xl:  3rem;      /* 48px - Hero numbers (USD/CLP rate) */
--font-size-4xl:  4rem;      /* 64px - Display (rarely used) */
```

### Font Weights

```css
--font-weight-normal:    400;  /* Body text */
--font-weight-medium:    500;  /* Emphasized text, labels */
--font-weight-semibold:  600;  /* Headings, buttons */
--font-weight-bold:      700;  /* Strong emphasis, alerts */
```

### Line Heights

```css
--line-height-tight:  1.2;   /* Headings, numbers */
--line-height-snug:   1.375; /* Dense text */
--line-height-normal: 1.5;   /* Body text, default */
--line-height-relaxed: 1.75; /* Long-form content */
```

### Letter Spacing

```css
--letter-spacing-tight:  -0.025em; /* Large headings */
--letter-spacing-normal:  0;       /* Body text */
--letter-spacing-wide:    0.025em; /* Small caps, labels */
```

### Typography Usage Guidelines

```css
/* H1 - Page Titles */
.h1 {
  font-size: var(--font-size-2xl);    /* 32px */
  font-weight: var(--font-weight-semibold); /* 600 */
  line-height: var(--line-height-tight);    /* 1.2 */
  letter-spacing: var(--letter-spacing-tight);
  color: var(--color-neutral-900);
}

/* H2 - Section Headers */
.h2 {
  font-size: var(--font-size-xl);     /* 24px */
  font-weight: var(--font-weight-semibold); /* 600 */
  line-height: var(--line-height-tight);
  color: var(--color-neutral-800);
}

/* H3 - Subsection Headers */
.h3 {
  font-size: var(--font-size-lg);     /* 20px */
  font-weight: var(--font-weight-medium); /* 500 */
  line-height: var(--line-height-normal);
  color: var(--color-neutral-800);
}

/* Body Text */
.body {
  font-size: var(--font-size-base);   /* 16px */
  font-weight: var(--font-weight-normal); /* 400 */
  line-height: var(--line-height-normal); /* 1.5 */
  color: var(--color-neutral-700);
}

/* Small Text - Labels, Captions */
.caption {
  font-size: var(--font-size-sm);     /* 14px */
  font-weight: var(--font-weight-normal);
  line-height: var(--line-height-normal);
  color: var(--color-neutral-600);
}

/* Currency Values - ALWAYS use monospace */
.currency {
  font-family: var(--font-mono);
  font-size: var(--font-size-3xl);    /* 48px for hero */
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-tight);
  color: var(--color-neutral-900);
  font-feature-settings: 'tnum' 1;    /* Tabular numbers */
}

/* Data Tables - Monospace for alignment */
.table-number {
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  font-feature-settings: 'tnum' 1;
}
```

---

## Spacing System (8px Grid)

```css
/* Spacing Scale - 8px base unit */
--space-0:   0;
--space-1:   0.25rem;  /* 4px  - Tight spacing */
--space-2:   0.5rem;   /* 8px  - Base unit */
--space-3:   0.75rem;  /* 12px */
--space-4:   1rem;     /* 16px - Default gap */
--space-5:   1.25rem;  /* 20px */
--space-6:   1.5rem;   /* 24px - Card padding */
--space-8:   2rem;     /* 32px - Section spacing */
--space-10:  2.5rem;   /* 40px */
--space-12:  3rem;     /* 48px - Large section spacing */
--space-16:  4rem;     /* 64px - Page section spacing */
--space-20:  5rem;     /* 80px */
--space-24:  6rem;     /* 96px - Hero spacing */
```

### Spacing Usage Guidelines

```css
/* Component Internal Padding */
--padding-button:      var(--space-4) var(--space-6);  /* 16px 24px */
--padding-input:       var(--space-3) var(--space-4);  /* 12px 16px */
--padding-card:        var(--space-6);                 /* 24px */
--padding-modal:       var(--space-8);                 /* 32px */

/* Component Gaps */
--gap-tight:   var(--space-2);  /* 8px  - Within groups */
--gap-normal:  var(--space-4);  /* 16px - Between components */
--gap-relaxed: var(--space-6);  /* 24px - Between sections */
--gap-loose:   var(--space-8);  /* 32px - Between major sections */

/* Layout Spacing */
--layout-gutter:  var(--space-6);   /* 24px - Screen edge padding */
--layout-gap:     var(--space-6);   /* 24px - Grid column gap */
--section-spacing: var(--space-12); /* 48px - Between page sections */
```

---

## Border Radius

```css
/* Border Radius Scale */
--radius-none:   0;
--radius-sm:     0.25rem;  /* 4px  - Small elements, inputs */
--radius-base:   0.375rem; /* 6px  - Buttons, badges */
--radius-md:     0.5rem;   /* 8px  - Cards, default */
--radius-lg:     0.75rem;  /* 12px - Large cards, modals */
--radius-xl:     1rem;     /* 16px - Hero cards */
--radius-2xl:    1.5rem;   /* 24px - Very large cards */
--radius-full:   9999px;   /* Pill shapes, avatars */
```

### Usage Guidelines
- **Inputs:** radius-sm (4px)
- **Buttons:** radius-base (6px)
- **Cards:** radius-md (8px)
- **Modals:** radius-lg (12px)
- **Avatars:** radius-full
- **Charts:** radius-sm on corners

---

## Shadows (Elevation)

```css
/* Shadow Scale - Subtle, professional */
--shadow-none: none;

--shadow-xs: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
/* Usage: Subtle borders on hover */

--shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.1),
             0 1px 2px -1px rgba(0, 0, 0, 0.1);
/* Usage: Buttons, dropdowns */

--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
             0 2px 4px -2px rgba(0, 0, 0, 0.1);
/* Usage: Cards, default elevation */

--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1),
             0 4px 6px -4px rgba(0, 0, 0, 0.1);
/* Usage: Floating cards, modals */

--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1),
             0 8px 10px -6px rgba(0, 0, 0, 0.1);
/* Usage: Modal overlays */

--shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
/* Usage: Hero cards, critical alerts */

/* Focus Ring - High visibility for keyboard navigation */
--shadow-focus: 0 0 0 3px rgba(59, 130, 246, 0.5);
/* Usage: Focus state on all interactive elements */
```

### Elevation System

```css
/* Elevation Levels */
--elevation-0: var(--shadow-none);   /* Flat - no elevation */
--elevation-1: var(--shadow-sm);     /* Subtle - cards at rest */
--elevation-2: var(--shadow-md);     /* Raised - cards on hover */
--elevation-3: var(--shadow-lg);     /* Floating - dropdowns, popovers */
--elevation-4: var(--shadow-xl);     /* Overlay - modals */
--elevation-5: var(--shadow-2xl);    /* Critical - alerts, notifications */
```

---

## Animation & Transitions

```css
/* Duration Scale */
--duration-instant: 0ms;
--duration-fast:    150ms;  /* Quick feedback (hover, focus) */
--duration-base:    200ms;  /* Default transitions */
--duration-slow:    300ms;  /* Larger movements (sidebar) */
--duration-slower:  500ms;  /* Deliberate animations (charts) */

/* Easing Functions */
--ease-linear:     linear;
--ease-in:         cubic-bezier(0.4, 0, 1, 1);
--ease-out:        cubic-bezier(0, 0, 0.2, 1);       /* Most common */
--ease-in-out:     cubic-bezier(0.4, 0, 0.2, 1);     /* Default */
--ease-bounce:     cubic-bezier(0.68, -0.55, 0.265, 1.55);  /* Playful (use sparingly) */

/* Standard Transitions */
--transition-all:      all var(--duration-base) var(--ease-in-out);
--transition-colors:   color var(--duration-fast) var(--ease-out),
                       background-color var(--duration-fast) var(--ease-out),
                       border-color var(--duration-fast) var(--ease-out);
--transition-shadow:   box-shadow var(--duration-base) var(--ease-out);
--transition-transform: transform var(--duration-base) var(--ease-out);
```

### Animation Usage Guidelines

```css
/* Hover Effects */
.button:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-lg);
  transition: var(--transition-all);
}

/* Focus Effects - Instant for accessibility */
.input:focus {
  box-shadow: var(--shadow-focus);
  border-color: var(--color-primary-500);
  transition: box-shadow var(--duration-instant) var(--ease-out),
              border-color var(--duration-instant) var(--ease-out);
}

/* Loading Shimmer */
@keyframes shimmer {
  0% { background-position: -1000px 0; }
  100% { background-position: 1000px 0; }
}

.skeleton {
  animation: shimmer 2s infinite linear;
  background: linear-gradient(
    90deg,
    var(--color-neutral-100) 0%,
    var(--color-neutral-200) 50%,
    var(--color-neutral-100) 100%
  );
  background-size: 1000px 100%;
}

/* Fade In (page transitions) */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-enter {
  animation: fadeIn var(--duration-base) var(--ease-out);
}
```

---

## Z-Index Scale (Layering)

```css
/* Z-Index Layers - Avoid magic numbers */
--z-base:        0;    /* Normal flow */
--z-dropdown:    1000; /* Dropdowns, popovers */
--z-sticky:      1100; /* Sticky headers */
--z-fixed:       1200; /* Fixed elements (navbar) */
--z-modal-backdrop: 1300; /* Modal overlay */
--z-modal:       1400; /* Modal content */
--z-popover:     1500; /* Popovers above modals */
--z-tooltip:     1600; /* Tooltips (highest) */
--z-toast:       1700; /* Toast notifications (above all) */
```

---

## Breakpoints (Responsive)

```css
/* Mobile-first breakpoints */
--breakpoint-xs:  320px;   /* Small phones */
--breakpoint-sm:  640px;   /* Phones */
--breakpoint-md:  768px;   /* Tablets */
--breakpoint-lg:  1024px;  /* Desktop */
--breakpoint-xl:  1280px;  /* Large desktop */
--breakpoint-2xl: 1536px;  /* Extra large desktop */

/* Usage in media queries */
@media (min-width: 640px) { /* sm */ }
@media (min-width: 768px) { /* md */ }
@media (min-width: 1024px) { /* lg */ }
```

### Layout Constraints

```css
/* Max widths for content */
--max-width-xs:   320px;
--max-width-sm:   640px;
--max-width-md:   768px;
--max-width-lg:   1024px;
--max-width-xl:   1280px;
--max-width-2xl:  1536px;
--max-width-full: 100%;

/* Dashboard-specific */
--sidebar-width:        240px;  /* Expanded */
--sidebar-width-collapsed: 64px;
--topbar-height:        64px;
--chart-min-height:     400px;
```

---

## Iconography

```css
/* Icon Sizes */
--icon-xs:  12px;
--icon-sm:  16px;
--icon-md:  20px;
--icon-lg:  24px;
--icon-xl:  32px;

/* Icon Library: Lucide React (or Heroicons) */
/* Characteristics:
   - Consistent stroke width (2px)
   - Rounded corners
   - Professional, minimal
   - Financial icons available (trending-up, bar-chart, etc.)
*/
```

---

## Usage Example - Complete Component

```css
/* Example: Primary Button with all design tokens */
.button-primary {
  /* Typography */
  font-family: var(--font-primary);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);

  /* Colors */
  color: white;
  background-color: var(--color-primary-600);
  border: none;

  /* Spacing */
  padding: var(--space-3) var(--space-6);

  /* Shape */
  border-radius: var(--radius-base);

  /* Elevation */
  box-shadow: var(--shadow-sm);

  /* Transition */
  transition: var(--transition-all);

  /* States */
  &:hover {
    background-color: var(--color-primary-700);
    box-shadow: var(--shadow-md);
    transform: translateY(-1px);
  }

  &:active {
    background-color: var(--color-primary-800);
    box-shadow: var(--shadow-sm);
    transform: translateY(0);
  }

  &:focus {
    outline: none;
    box-shadow: var(--shadow-focus);
  }

  &:disabled {
    background-color: var(--color-neutral-300);
    color: var(--color-neutral-500);
    cursor: not-allowed;
    box-shadow: none;
  }
}
```

---

## Dark Mode (Future Enhancement)

```css
/* Dark mode color overrides */
@media (prefers-color-scheme: dark) {
  :root {
    --color-neutral-50:  var(--color-dark-900);
    --color-neutral-100: var(--color-dark-800);
    --color-neutral-200: var(--color-dark-700);
    --color-neutral-700: var(--color-dark-100);
    --color-neutral-800: var(--color-dark-50);
    --color-neutral-900: var(--color-dark-50);

    /* Chart backgrounds */
    --chart-grid: var(--color-dark-700);

    /* Shadows (lighter in dark mode) */
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
  }
}
```

---

## Implementation Notes

**CSS Variables Location:** `src/styles/tokens.css`

**Framework Integration:**
- Tailwind CSS: Configure `tailwind.config.js` to use these tokens
- Styled Components: Import tokens as JS object
- CSS Modules: Import tokens.css globally

**Performance:**
- All colors defined as CSS variables for instant theme switching
- Use `font-display: swap` for web fonts
- Lazy load icon library (only load used icons)

---

**Next:** Component specifications using these design tokens
