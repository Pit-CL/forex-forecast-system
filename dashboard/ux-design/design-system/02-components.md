# Component Library - USD/CLP Forecast Dashboard

---

## Button Components

### Primary Button

**Purpose:** Main call-to-action, most important action on screen (limit 1-2 per view)

**Visual Specs:**
```css
.button-primary {
  /* Base */
  font-size: 16px (var(--font-size-base));
  font-weight: 600 (var(--font-weight-semibold));
  padding: 12px 24px (var(--space-3) var(--space-6));
  border-radius: 6px (var(--radius-base));

  /* Colors */
  background: #2563EB (var(--color-primary-600));
  color: #FFFFFF;
  border: none;

  /* Elevation */
  box-shadow: var(--shadow-sm);

  /* Interaction */
  cursor: pointer;
  transition: all 200ms ease-out;
}

/* States */
.button-primary:hover {
  background: #1D4ED8 (var(--color-primary-700));
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.button-primary:active {
  background: #1E40AF (var(--color-primary-800));
  transform: translateY(0);
}

.button-primary:focus {
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.5);
  outline: none;
}

.button-primary:disabled {
  background: #D1D5DB (var(--color-neutral-300));
  color: #9CA3AF (var(--color-neutral-400));
  cursor: not-allowed;
  box-shadow: none;
}
```

**Sizes:**
```
Small:  padding: 8px 16px,  font-size: 14px, height: 32px
Medium: padding: 12px 24px, font-size: 16px, height: 40px (default)
Large:  padding: 16px 32px, font-size: 18px, height: 48px
```

**Usage:**
```jsx
<Button variant="primary" size="medium">
  Get Forecast
</Button>

<Button variant="primary" size="large" loading>
  Generating Report...
</Button>
```

---

### Secondary Button

**Purpose:** Alternative actions, less emphasis than primary

**Visual Specs:**
```css
.button-secondary {
  background: transparent;
  color: #2563EB (var(--color-primary-600));
  border: 2px solid #2563EB;
  /* Rest same as primary */
}

.button-secondary:hover {
  background: #EFF6FF (var(--color-primary-50));
  border-color: #1D4ED8 (var(--color-primary-700));
}
```

---

### Tertiary Button (Ghost)

**Purpose:** Subtle actions, high-density interfaces

**Visual Specs:**
```css
.button-tertiary {
  background: transparent;
  color: #4B5563 (var(--color-neutral-600));
  border: none;
  padding: 8px 16px;
}

.button-tertiary:hover {
  background: #F3F4F6 (var(--color-neutral-100));
  color: #1F2937 (var(--color-neutral-800));
}
```

---

### Danger Button

**Purpose:** Destructive actions (delete, remove, cancel trade)

**Visual Specs:**
```css
.button-danger {
  background: #DC2626 (var(--color-danger-600));
  color: white;
  /* Rest same as primary */
}

.button-danger:hover {
  background: #B91C1C (var(--color-danger-700));
}
```

---

### Icon Button

**Purpose:** Actions represented by icon only (save space)

**Visual Specs:**
```css
.button-icon {
  width: 40px;
  height: 40px;
  padding: 8px;
  border-radius: 6px;
  background: transparent;
  color: #4B5563;
}

.button-icon:hover {
  background: #F3F4F6;
  color: #1F2937;
}
```

**Usage:**
```jsx
<IconButton icon={<RefreshIcon />} aria-label="Refresh data" />
```

---

## Input Components

### Text Input

**Visual Specs:**
```css
.input {
  /* Base */
  font-size: 16px;
  font-family: var(--font-primary);
  padding: 12px 16px;
  width: 100%;

  /* Colors */
  background: white;
  color: #1F2937 (var(--color-neutral-800));
  border: 1px solid #D1D5DB (var(--color-neutral-300));
  border-radius: 6px;

  /* Interaction */
  transition: border-color 150ms, box-shadow 150ms;
}

.input:hover {
  border-color: #9CA3AF (var(--color-neutral-400));
}

.input:focus {
  border-color: #2563EB (var(--color-primary-600));
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  outline: none;
}

.input::placeholder {
  color: #9CA3AF (var(--color-neutral-400));
}

.input:disabled {
  background: #F3F4F6 (var(--color-neutral-100));
  color: #9CA3AF;
  cursor: not-allowed;
}

.input.error {
  border-color: #DC2626 (var(--color-danger-600));
}

.input.success {
  border-color: #16A34A (var(--color-success-600));
}
```

**Anatomy:**
```
┌─────────────────────────────────────┐
│ Label *                              │  ← Label (required indicator)
├─────────────────────────────────────┤
│ [  Placeholder text...          ] │  ← Input field
├─────────────────────────────────────┤
│ Helper text (optional)               │  ← Helper/Error text
└─────────────────────────────────────┘

```

**With Icon:**
```
┌─────────────────────────────────────┐
│ [🔍]  Search forecasts...          │  ← Leading icon
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Email address                  [✓] │  ← Trailing icon (validation)
└─────────────────────────────────────┘
```

**Usage:**
```jsx
<Input
  label="Email"
  type="email"
  placeholder="you@cavara.cl"
  required
  error="Must be a @cavara.cl email"
/>
```

---

### Password Input

**Special Features:**
- Toggle visibility icon
- Strength indicator
- Requirements checklist (on focus)

```jsx
<PasswordInput
  label="Password"
  showStrength
  requirements={[
    { text: "At least 8 characters", met: true },
    { text: "One uppercase letter", met: false },
    { text: "One number", met: true }
  ]}
/>
```

---

### Select Dropdown

**Visual Specs:**
```css
.select {
  /* Same as .input */
  appearance: none;
  background-image: url("data:image/svg+xml,..."); /* Chevron down icon */
  background-position: right 12px center;
  background-repeat: no-repeat;
  padding-right: 40px; /* Space for icon */
}
```

**Usage:**
```jsx
<Select label="Forecast Horizon" value="7D">
  <option value="7D">7 Days</option>
  <option value="15D">15 Days</option>
  <option value="30D">30 Days</option>
  <option value="90D">90 Days</option>
</Select>
```

---

### Checkbox

**Visual Specs:**
```css
.checkbox {
  width: 20px;
  height: 20px;
  border: 2px solid #D1D5DB;
  border-radius: 4px;
  background: white;
}

.checkbox:checked {
  background: #2563EB;
  border-color: #2563EB;
  /* Show checkmark SVG */
}

.checkbox:focus {
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}
```

---

### Radio Button

**Visual Specs:**
```css
.radio {
  width: 20px;
  height: 20px;
  border: 2px solid #D1D5DB;
  border-radius: 50%;
  background: white;
}

.radio:checked {
  border-color: #2563EB;
  border-width: 6px; /* Filled circle effect */
}
```

---

## Card Components

### Base Card

**Purpose:** Container for related content

**Visual Specs:**
```css
.card {
  background: white;
  border: 1px solid #E5E7EB (var(--color-neutral-200));
  border-radius: 8px (var(--radius-md));
  padding: 24px (var(--space-6));
  box-shadow: var(--shadow-sm);
  transition: box-shadow 200ms;
}

.card:hover {
  box-shadow: var(--shadow-md);
}
```

**Anatomy:**
```
┌───────────────────────────────────────┐
│ Card Title              [Icon Button] │ ← Header (optional)
├───────────────────────────────────────┤
│                                       │
│  Card content goes here...            │ ← Body
│  Can contain any elements             │
│                                       │
├───────────────────────────────────────┤
│ Footer text          [Action Button]  │ ← Footer (optional)
└───────────────────────────────────────┘
```

**Usage:**
```jsx
<Card>
  <CardHeader>
    <CardTitle>7-Day Forecast</CardTitle>
    <IconButton icon={<RefreshIcon />} />
  </CardHeader>
  <CardBody>
    <ForecastChart data={data} />
  </CardBody>
  <CardFooter>
    <Text size="sm" color="muted">Last updated: 2 min ago</Text>
  </CardFooter>
</Card>
```

---

### Stat Card

**Purpose:** Display key metrics prominently

**Visual Specs:**
```
┌─────────────────────────────────────┐
│ Current USD/CLP Rate                │ ← Label (small, muted)
│                                     │
│         948.30 CLP                  │ ← Value (large, prominent)
│         ▲ +0.62%                    │ ← Change indicator
│                                     │
│ ▁▂▃▄▅▆▇█ Sparkline (optional)       │ ← Micro chart
└─────────────────────────────────────┘
```

**Visual Specs:**
```css
.stat-card {
  /* Extends .card */
  padding: 24px;
  min-height: 140px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.stat-card-label {
  font-size: 14px;
  color: #6B7280 (var(--color-neutral-500));
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-card-value {
  font-size: 48px (var(--font-size-3xl));
  font-weight: 600;
  font-family: var(--font-mono);
  color: #111827;
  line-height: 1;
  margin-top: 8px;
}

.stat-card-change {
  font-size: 16px;
  font-weight: 600;
  margin-top: 8px;
}

.stat-card-change.positive {
  color: #16A34A (var(--color-success-600));
}

.stat-card-change.negative {
  color: #DC2626 (var(--color-danger-600));
}

.stat-card-change.neutral {
  color: #6B7280 (var(--color-neutral-500));
}
```

**Usage:**
```jsx
<StatCard
  label="7-Day Forecast"
  value="952.15"
  unit="CLP"
  change="+0.41%"
  trend="up"
  sparkline={[945, 946, 948, 947, 950, 951, 952]}
/>
```

---

### Forecast Card (Specialized)

**Purpose:** Display forecast with confidence interval

**Visual Specs:**
```
┌─────────────────────────────────────┐
│ 7-Day Forecast           [Model: ▾] │ ← Header with model selector
├─────────────────────────────────────┤
│         952.15 CLP                  │ ← Forecast value (large)
│         ▲ +0.41%                    │ ← Change from current
│                                     │
│ Confidence: ████████░░ 87%          │ ← Confidence bar
│ [i] Why this confidence?            │ ← Explainer link
│                                     │
│ Range: 948.30 - 956.00 CLP          │ ← Confidence interval
│ ├─────────────┼─────────────┤       │ ← Visual range
│                                     │
├─────────────────────────────────────┤
│ Last updated: 5 min ago             │ ← Footer
│ Model accuracy: 2.20% MAPE          │
└─────────────────────────────────────┘
```

---

## Badge Components

### Status Badge

**Purpose:** Indicate state or category

**Visual Specs:**
```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px (var(--space-1) var(--space-3));
  border-radius: 9999px (var(--radius-full));
  font-size: 14px (var(--font-size-sm));
  font-weight: 500;
  line-height: 1;
}

/* Variants */
.badge-success {
  background: #DCFCE7 (var(--color-success-100));
  color: #15803D (var(--color-success-700));
}

.badge-danger {
  background: #FEE2E2 (var(--color-danger-100));
  color: #B91C1C (var(--color-danger-700));
}

.badge-warning {
  background: #FEF3C7 (var(--color-warning-100));
  color: #B45309 (var(--color-warning-700));
}

.badge-info {
  background: #DBEAFE (var(--color-primary-100));
  color: #1E40AF (var(--color-primary-800));
}

.badge-neutral {
  background: #F3F4F6 (var(--color-neutral-100));
  color: #1F2937 (var(--color-neutral-800));
}
```

**Usage:**
```jsx
<Badge variant="success">Excellent</Badge>
<Badge variant="warning">Moderate</Badge>
<Badge variant="danger">Poor</Badge>

<Badge variant="info">Primary Model</Badge>
<Badge variant="neutral">Backup Model</Badge>
```

**With Icon:**
```jsx
<Badge variant="success" icon={<CheckIcon />}>
  Verified
</Badge>
```

---

### Numeric Badge (Notification)

**Purpose:** Show counts (notifications, alerts)

**Visual Specs:**
```css
.badge-numeric {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: #DC2626;
  color: white;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
```

**Usage:**
```jsx
<IconButton icon={<BellIcon />} badge={3} />
```

---

## Alert Components

### Alert Box

**Purpose:** Important messages, errors, warnings, success feedback

**Anatomy:**
```
┌─────────────────────────────────────┐
│ [Icon] Alert Title           [✕]    │ ← Header (dismissable)
├─────────────────────────────────────┤
│ Alert message goes here. It can be  │ ← Body
│ multi-line and contain additional   │
│ information or instructions.        │
│                                     │
│ [Action Button]  [Secondary Button] │ ← Actions (optional)
└─────────────────────────────────────┘
```

**Visual Specs:**
```css
.alert {
  padding: 16px;
  border-radius: 8px;
  border-left: 4px solid; /* Accent border */
  display: flex;
  gap: 12px;
}

/* Variants */
.alert-success {
  background: #F0FDF4 (var(--color-success-50));
  border-color: #22C55E (var(--color-success-500));
  color: #15803D;
}

.alert-danger {
  background: #FEF2F2 (var(--color-danger-50));
  border-color: #EF4444 (var(--color-danger-500));
  color: #B91C1C;
}

.alert-warning {
  background: #FFFBEB (var(--color-warning-50));
  border-color: #F59E0B (var(--color-warning-500));
  color: #B45309;
}

.alert-info {
  background: #EFF6FF (var(--color-info-50));
  border-color: #3B82F6 (var(--color-info-500));
  color: #1E40AF;
}
```

**Usage:**
```jsx
<Alert variant="success" dismissable>
  <AlertTitle>Forecast Updated</AlertTitle>
  <AlertDescription>
    7-day forecast has been updated with latest data.
  </AlertDescription>
</Alert>

<Alert variant="danger" action={<Button size="sm">Fix Now</Button>}>
  <AlertTitle>Model Accuracy Below Threshold</AlertTitle>
  <AlertDescription>
    7D MAPE is 5.2%, above the 3% threshold. Retraining recommended.
  </AlertDescription>
</Alert>
```

---

### Toast Notification

**Purpose:** Non-intrusive feedback for user actions

**Position:** Top-right corner, stacks vertically

**Visual Specs:**
```css
.toast {
  min-width: 320px;
  max-width: 420px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  box-shadow: var(--shadow-xl);
  border: 1px solid #E5E7EB;

  /* Animation */
  animation: slideInRight 300ms ease-out;
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
```

**Auto-dismiss:** 5 seconds default (adjustable)

**Usage:**
```jsx
toast.success("Forecast generated successfully");
toast.error("Failed to load data");
toast.info("New forecast available", {
  action: <Button size="sm">View</Button>,
  duration: 10000
});
```

---

## Modal Components

### Base Modal

**Purpose:** Focus user attention on critical task

**Anatomy:**
```
[Dark Overlay - 50% opacity]

        ┌─────────────────────────────────┐
        │ Modal Title            [✕]      │ ← Header
        ├─────────────────────────────────┤
        │                                 │
        │  Modal content...               │ ← Body (scrollable if needed)
        │                                 │
        ├─────────────────────────────────┤
        │     [Cancel]  [Confirm Action]  │ ← Footer (actions)
        └─────────────────────────────────┘
```

**Visual Specs:**
```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: var(--z-modal-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 200ms ease-out;
}

.modal {
  background: white;
  border-radius: 12px (var(--radius-lg));
  box-shadow: var(--shadow-2xl);
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow: hidden;
  z-index: var(--z-modal);
  animation: scaleIn 200ms ease-out;
}

@keyframes scaleIn {
  from {
    transform: scale(0.95);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

.modal-header {
  padding: 24px;
  border-bottom: 1px solid #E5E7EB;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  max-height: 60vh;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #E5E7EB;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
```

**Accessibility:**
- Trap focus within modal
- Close on Escape key
- Close on overlay click (optional)
- Return focus to trigger element on close

**Usage:**
```jsx
<Modal open={isOpen} onClose={handleClose}>
  <ModalHeader>
    <ModalTitle>Export Report</ModalTitle>
  </ModalHeader>
  <ModalBody>
    <Select label="Format">
      <option>PDF</option>
      <option>Excel</option>
    </Select>
  </ModalBody>
  <ModalFooter>
    <Button variant="tertiary" onClick={handleClose}>
      Cancel
    </Button>
    <Button variant="primary" onClick={handleExport}>
      Export
    </Button>
  </ModalFooter>
</Modal>
```

---

### Confirmation Modal

**Purpose:** Confirm destructive actions

**Visual Specs:** Same as base modal, but with danger styling

**Usage:**
```jsx
<ConfirmModal
  open={confirmDelete}
  title="Delete Forecast?"
  description="This action cannot be undone. Are you sure?"
  confirmText="Delete"
  confirmVariant="danger"
  onConfirm={handleDelete}
  onCancel={handleCancel}
/>
```

---

## Table Components

### Data Table

**Purpose:** Display tabular data (forecast history, performance metrics)

**Visual Specs:**
```css
.table {
  width: 100%;
  border-collapse: collapse;
}

.table th {
  background: #F9FAFB (var(--color-neutral-50));
  padding: 12px 16px;
  text-align: left;
  font-size: 14px;
  font-weight: 600;
  color: #374151 (var(--color-neutral-700));
  border-bottom: 2px solid #E5E7EB;
}

.table td {
  padding: 16px;
  border-bottom: 1px solid #E5E7EB;
  font-size: 14px;
  color: #1F2937;
}

.table tr:hover {
  background: #F9FAFB;
}

/* Numeric columns - right-align, monospace */
.table td.numeric {
  text-align: right;
  font-family: var(--font-mono);
  font-feature-settings: 'tnum' 1;
}
```

**Features:**
- Sortable columns (click header)
- Pagination
- Row selection (checkbox)
- Expandable rows
- Sticky header (on scroll)

**Usage:**
```jsx
<Table
  data={forecastHistory}
  columns={[
    { key: 'date', label: 'Date', sortable: true },
    { key: 'forecast', label: 'Forecast', numeric: true },
    { key: 'actual', label: 'Actual', numeric: true },
    { key: 'error', label: 'Error %', numeric: true, format: 'percentage' }
  ]}
  pagination
  pageSize={10}
/>
```

---

## Tooltip Component

**Purpose:** Explain terms, show additional info on hover

**Visual Specs:**
```css
.tooltip {
  background: #1F2937 (var(--color-neutral-800));
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  max-width: 250px;
  box-shadow: var(--shadow-lg);
  z-index: var(--z-tooltip);

  /* Arrow */
  position: relative;
}

.tooltip::after {
  content: '';
  position: absolute;
  border: 6px solid transparent;
  border-top-color: #1F2937;
  bottom: -12px;
  left: 50%;
  transform: translateX(-50%);
}
```

**Positioning:** Auto (smart positioning to stay on screen)

**Trigger:** Hover (desktop) + Focus (keyboard) + Long-press (mobile)

**Usage:**
```jsx
<Tooltip content="Mean Absolute Percentage Error - lower is better">
  <span>MAPE: 2.20%</span>
</Tooltip>

<Tooltip content="Confidence based on historical accuracy">
  <IconButton icon={<InfoIcon />} />
</Tooltip>
```

---

## Loading States

### Spinner

**Visual Specs:**
```css
.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #E5E7EB;
  border-top-color: #2563EB;
  border-radius: 50%;
  animation: spin 600ms linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

**Sizes:** sm (16px), md (24px), lg (32px), xl (48px)

---

### Skeleton Screen

**Purpose:** Show content structure while loading

**Visual Specs:**
```css
.skeleton {
  background: linear-gradient(
    90deg,
    #F3F4F6 0%,
    #E5E7EB 50%,
    #F3F4F6 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 6px;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
```

**Usage:**
```jsx
<CardSkeleton>
  <Skeleton height="24px" width="60%" /> {/* Title */}
  <Skeleton height="48px" width="100%" style={{ marginTop: '16px' }} /> {/* Value */}
  <Skeleton height="200px" width="100%" style={{ marginTop: '24px' }} /> {/* Chart */}
</CardSkeleton>
```

---

### Progress Bar

**Purpose:** Show determinate progress (e.g., report generation)

**Visual Specs:**
```css
.progress {
  width: 100%;
  height: 8px;
  background: #E5E7EB;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: #2563EB;
  border-radius: 4px;
  transition: width 300ms ease-out;
}
```

**Usage:**
```jsx
<Progress value={65} max={100} label="Generating report: 65%" />
```

---

## Navigation Components

### Breadcrumbs

**Purpose:** Show hierarchy, allow backward navigation

**Visual Specs:**
```
Home > Forecasts > 7-Day Forecast > Details
```

```css
.breadcrumbs {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #6B7280;
}

.breadcrumb-link {
  color: #6B7280;
  text-decoration: none;
}

.breadcrumb-link:hover {
  color: #2563EB;
}

.breadcrumb-current {
  color: #1F2937;
  font-weight: 500;
}

.breadcrumb-separator {
  color: #D1D5DB;
}
```

---

### Tabs

**Purpose:** Switch between related views without navigation

**Visual Specs:**
```css
.tabs {
  border-bottom: 2px solid #E5E7EB;
  display: flex;
  gap: 32px;
}

.tab {
  padding: 12px 0;
  font-size: 16px;
  font-weight: 500;
  color: #6B7280;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color 200ms, border-color 200ms;
}

.tab:hover {
  color: #1F2937;
}

.tab.active {
  color: #2563EB;
  border-bottom-color: #2563EB;
}
```

**Usage:**
```jsx
<Tabs value={activeTab} onChange={setActiveTab}>
  <Tab value="7D">7 Days</Tab>
  <Tab value="15D">15 Days</Tab>
  <Tab value="30D">30 Days</Tab>
  <Tab value="90D">90 Days</Tab>
</Tabs>

<TabPanel value="7D">
  <ForecastChart horizon="7D" />
</TabPanel>
```

---

## Empty States

**Purpose:** Show when no data available

**Anatomy:**
```
┌─────────────────────────────────────┐
│                                     │
│          [Illustration]             │ ← Simple icon/image
│                                     │
│     No Forecasts Available          │ ← Title
│                                     │
│  Get started by generating your     │ ← Description
│  first forecast using the button    │
│  below.                             │
│                                     │
│      [Generate Forecast]            │ ← Primary CTA
│                                     │
└─────────────────────────────────────┘
```

**Visual Specs:**
```css
.empty-state {
  padding: 64px 32px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.empty-state-icon {
  width: 64px;
  height: 64px;
  color: #D1D5DB;
}

.empty-state-title {
  font-size: 20px;
  font-weight: 600;
  color: #1F2937;
}

.empty-state-description {
  font-size: 16px;
  color: #6B7280;
  max-width: 400px;
}
```

---

## Component Checklist

**Every Component Must Have:**
- ✅ Light & Dark mode styles
- ✅ Hover, Focus, Active, Disabled states
- ✅ Keyboard accessibility (Tab, Enter, Space, Escape)
- ✅ ARIA labels and roles
- ✅ Mobile responsive design
- ✅ Loading state (if async)
- ✅ Error state (if applicable)
- ✅ Consistent spacing (8px grid)
- ✅ Consistent colors (design tokens)
- ✅ Consistent typography (font scale)

---

**Next:** Wireframes showing these components in actual layouts
