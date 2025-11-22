# Interactions & Animations Specification

---

## Design Philosophy

**Financial dashboards require:**
1. **SPEED** - Instant feedback, no perceived lag
2. **CLARITY** - Animations guide attention, not distract
3. **PREDICTABILITY** - Same action = same result every time
4. **PROFESSIONALISM** - Subtle, refined, never gimmicky

**Animation Principles:**
- Duration: 150-300ms (fast enough to feel instant, slow enough to see)
- Easing: Ease-out for entrances, ease-in for exits
- Purpose: Every animation must serve a function (not decoration)

---

## 1. Page Transitions

### Initial Page Load

**Sequence:**
```
1. TopBar fades in (0ms)
2. Sidebar slides in from left (100ms delay)
3. Stat cards fade + slide up (150ms delay, staggered 50ms each)
4. Main chart skeleton → data (300ms delay)
5. Secondary cards fade in (400ms delay)

Total: ~700ms from blank to full content
```

**Implementation:**
```css
.page-enter {
  animation: fadeInUp 300ms ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Stagger children */
.stat-card:nth-child(1) { animation-delay: 150ms; }
.stat-card:nth-child(2) { animation-delay: 200ms; }
.stat-card:nth-child(3) { animation-delay: 250ms; }
.stat-card:nth-child(4) { animation-delay: 300ms; }
```

---

### Route Changes (Dashboard → Forecast Detail)

**Sequence:**
```
1. Current page fades out (150ms)
2. New page fades in + slides (200ms)
3. Breadcrumbs update
4. Focus moves to main content
```

**Implementation:**
```css
/* Exit animation */
.page-exit-active {
  animation: fadeOut 150ms ease-in;
}

/* Enter animation */
.page-enter-active {
  animation: fadeInSlide 200ms ease-out;
}

@keyframes fadeInSlide {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
```

**User Experience:**
- Never jarring
- Maintains spatial awareness
- Fast enough not to wait

---

## 2. Hover States

### Buttons

**Primary Button:**
```css
.button-primary {
  transition: all 200ms ease-out;
}

.button-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(37, 99, 235, 0.25);
  background-color: var(--color-primary-700);
}

.button-primary:active {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(37, 99, 235, 0.15);
}
```

**Visual Result:**
- Lifts on hover (subtle 3D effect)
- Darkens slightly
- Presses down on click
- Total duration: 200ms

---

### Cards

**Stat Card:**
```css
.stat-card {
  transition: box-shadow 300ms ease-out,
              transform 300ms ease-out;
  cursor: pointer;
}

.stat-card:hover {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-4px);
}
```

**Visual Result:**
- Elevation increases (floating effect)
- Lifts 4px
- Shadow spreads
- Indicates clickability

---

### Chart Elements

**Data Point Hover:**
```css
.chart-point {
  r: 4; /* radius */
  transition: r 150ms ease-out;
}

.chart-point:hover {
  r: 6;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}
```

**Tooltip Appearance:**
```css
.tooltip {
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 150ms ease-out,
              transform 150ms ease-out;
}

.tooltip.visible {
  opacity: 1;
  transform: translateY(0);
}
```

**User Experience:**
- Point grows slightly
- Tooltip fades in smoothly
- No delay (instant response)

---

## 3. Focus States (Keyboard Navigation)

### All Interactive Elements

**Specification:**
```css
*:focus {
  outline: 3px solid rgba(59, 130, 246, 0.5);
  outline-offset: 2px;
  transition: outline 0ms; /* Instant for accessibility */
}

/* Never remove focus outlines */
button:focus,
a:focus,
input:focus {
  outline: 3px solid rgba(59, 130, 246, 0.5);
}
```

**Skip to Main Content:**
```css
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--color-primary-600);
  color: white;
  padding: 8px 16px;
  z-index: 9999;
  transition: top 0ms; /* Instant */
}

.skip-link:focus {
  top: 0;
}
```

---

## 4. Loading States

### Skeleton Screens

**Shimmer Animation:**
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
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
```

**Visual Result:**
- Soft wave of light moving across
- Continuous (loops)
- Indicates loading without spinner

---

### Spinner (When Necessary)

**Use Cases:** Small actions (refresh button, form submit)

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

**In Button:**
```html
<button class="loading">
  <span class="spinner"></span>
  Loading...
</button>
```

---

### Progress Bar

**Determinate Progress:**
```css
.progress-bar {
  width: 0%;
  height: 8px;
  background: var(--color-primary-600);
  transition: width 300ms ease-out;
}

/* JavaScript updates width */
progressBar.style.width = `${progress}%`;
```

**With Pulse (Indeterminate):**
```css
.progress-bar.indeterminate {
  width: 30%;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(300%); }
}
```

---

## 5. Real-Time Updates

### Price Change Animation

**When USD/CLP price updates:**

```javascript
// On WebSocket price update
function updatePrice(newPrice, oldPrice) {
  const direction = newPrice > oldPrice ? 'up' : 'down';

  // 1. Flash background
  priceElement.classList.add(`flash-${direction}`);

  // 2. Animate number change
  animateValue(oldPrice, newPrice, 500);

  // 3. Remove flash after animation
  setTimeout(() => {
    priceElement.classList.remove(`flash-${direction}`);
  }, 500);
}
```

**CSS:**
```css
.price {
  transition: background-color 500ms ease-out;
}

.price.flash-up {
  background-color: rgba(34, 197, 94, 0.2); /* Green */
}

.price.flash-down {
  background-color: rgba(239, 68, 68, 0.2); /* Red */
}

/* Number animation handled in JS */
```

**Visual Result:**
- Price flashes green (up) or red (down)
- Number counts up/down smoothly
- Fades back to normal
- Total: 500ms

---

### New Forecast Available

**Toast Notification:**
```css
.toast-enter {
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

.toast-exit {
  animation: slideOutRight 200ms ease-in;
}

@keyframes slideOutRight {
  to {
    transform: translateX(100%);
    opacity: 0;
  }
}
```

**Auto-dismiss:**
- Appears from right
- Stays 5 seconds
- Fades out automatically
- Can be dismissed early (click X)

---

### Chart Data Update

**Smooth Data Transition:**
```javascript
// Using D3.js or Chart.js
chart.data = newData;
chart.update({
  duration: 500,
  easing: 'easeOutQuad'
});
```

**Visual Result:**
- New data points morph in
- Lines smoothly redraw
- No jarring jumps
- Maintains user's focus

---

## 6. Modals & Overlays

### Modal Open

**Sequence:**
```
1. Overlay fades in (200ms)
2. Modal scales + fades in (250ms)
3. Focus moves to modal (first input or close button)
4. Body scroll locked
```

**CSS:**
```css
.modal-overlay {
  animation: fadeIn 200ms ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal {
  animation: scaleIn 250ms ease-out;
}

@keyframes scaleIn {
  from {
    transform: scale(0.9);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}
```

---

### Modal Close

**Sequence:**
```
1. Modal scales down + fades (200ms)
2. Overlay fades out (200ms)
3. Focus returns to trigger element
4. Body scroll unlocked
```

**Triggers:**
- Click [X] button
- Click overlay (optional)
- Press Escape key
- Submit form successfully

---

## 7. Form Interactions

### Input Focus

**Sequence:**
```
1. Border color changes (instant)
2. Focus ring appears (instant)
3. Label moves up (if floating label) (150ms)
```

**CSS:**
```css
.input {
  border: 1px solid #D1D5DB;
  transition: border-color 150ms ease-out,
              box-shadow 150ms ease-out;
}

.input:focus {
  border-color: #2563EB;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}
```

---

### Form Validation

**Real-Time Validation:**
```javascript
// On input change (debounced 300ms)
input.addEventListener('input', debounce(() => {
  validate();
}, 300));
```

**Visual Feedback:**

**Success:**
```css
.input.valid {
  border-color: #16A34A;
  background-image: url('checkmark.svg');
  background-position: right 12px center;
}
```

**Error:**
```css
.input.invalid {
  border-color: #DC2626;
  animation: shake 300ms;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-8px); }
  75% { transform: translateX(8px); }
}
```

**Error Message:**
```css
.error-message {
  animation: slideDown 200ms ease-out;
}

@keyframes slideDown {
  from {
    max-height: 0;
    opacity: 0;
  }
  to {
    max-height: 100px;
    opacity: 1;
  }
}
```

---

### Password Strength Indicator

**Progressive Enhancement:**
```javascript
// As user types
function updateStrength(password) {
  const strength = calculateStrength(password);

  // Animate bar width
  strengthBar.style.width = `${strength}%`;

  // Change color
  if (strength < 40) strengthBar.className = 'weak';
  else if (strength < 70) strengthBar.className = 'medium';
  else strengthBar.className = 'strong';
}
```

**CSS:**
```css
.strength-bar {
  height: 4px;
  border-radius: 2px;
  transition: width 300ms ease-out,
              background-color 300ms ease-out;
}

.strength-bar.weak { background-color: #DC2626; }
.strength-bar.medium { background-color: #F59E0B; }
.strength-bar.strong { background-color: #16A34A; }
```

---

## 8. Sidebar Interactions

### Collapse/Expand

**Trigger:** Click hamburger or [☰] button

**Animation:**
```css
.sidebar {
  width: 240px;
  transition: width 300ms ease-in-out;
}

.sidebar.collapsed {
  width: 64px;
}

/* Text fades out */
.sidebar-text {
  opacity: 1;
  transition: opacity 150ms ease-out;
}

.sidebar.collapsed .sidebar-text {
  opacity: 0;
}

/* Icons stay visible */
.sidebar-icon {
  opacity: 1;
}
```

**Content Adjustment:**
```css
.main-content {
  margin-left: 240px;
  transition: margin-left 300ms ease-in-out;
}

.sidebar.collapsed + .main-content {
  margin-left: 64px;
}
```

**User Experience:**
- Smooth 300ms transition
- Icons remain visible
- Text fades out gracefully
- More screen space for content

---

### Active Navigation Highlight

**On Click:**
```css
.nav-item {
  position: relative;
  color: #6B7280;
  transition: color 200ms ease-out,
              background-color 200ms ease-out;
}

.nav-item.active {
  color: #2563EB;
  background-color: #EFF6FF;
}

/* Active indicator bar */
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background-color: #2563EB;
  animation: slideIn 200ms ease-out;
}

@keyframes slideIn {
  from { width: 0; }
  to { width: 4px; }
}
```

---

## 9. Chart Interactions

### Zoom

**Mouse Wheel + Ctrl:**
```javascript
chart.addEventListener('wheel', (e) => {
  if (e.ctrlKey) {
    e.preventDefault();
    const zoomDirection = e.deltaY > 0 ? -0.1 : 0.1;
    animateZoom(currentZoom + zoomDirection, 200);
  }
});
```

**Pinch (Touch):**
```javascript
// Using Hammer.js or native touch events
hammer.on('pinch', (e) => {
  animateZoom(e.scale, 200);
});
```

**Animation:**
```javascript
function animateZoom(targetZoom, duration) {
  const startZoom = currentZoom;
  const startTime = Date.now();

  function frame() {
    const elapsed = Date.now() - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = easeOutQuad(progress);

    currentZoom = startZoom + (targetZoom - startZoom) * eased;
    chart.zoom(currentZoom);

    if (progress < 1) requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);
}
```

---

### Pan

**Click + Drag:**
```javascript
let isDragging = false;
let startX = 0;

chart.addEventListener('mousedown', (e) => {
  isDragging = true;
  startX = e.clientX;
  chart.style.cursor = 'grabbing';
});

chart.addEventListener('mousemove', (e) => {
  if (!isDragging) return;

  const deltaX = e.clientX - startX;
  chart.pan(deltaX);
  startX = e.clientX;
});

chart.addEventListener('mouseup', () => {
  isDragging = false;
  chart.style.cursor = 'grab';
});
```

---

### Tooltip Follow Cursor

**Smooth Following:**
```javascript
let targetX = 0;
let targetY = 0;
let currentX = 0;
let currentY = 0;

chart.addEventListener('mousemove', (e) => {
  targetX = e.clientX;
  targetY = e.clientY;
});

// Smooth interpolation (60fps)
function animateTooltip() {
  const ease = 0.15;
  currentX += (targetX - currentX) * ease;
  currentY += (targetY - currentY) * ease;

  tooltip.style.transform = `translate(${currentX}px, ${currentY}px)`;

  requestAnimationFrame(animateTooltip);
}

animateTooltip();
```

**Result:** Tooltip follows cursor with slight lag (smooth, not jittery)

---

## 10. Micro-Interactions

### Copy to Clipboard

**On Click:**
```javascript
copyButton.addEventListener('click', async () => {
  await navigator.clipboard.writeText(value);

  // Visual feedback
  copyButton.classList.add('copied');
  copyButton.innerHTML = '✓ Copied!';

  setTimeout(() => {
    copyButton.classList.remove('copied');
    copyButton.innerHTML = 'Copy';
  }, 2000);
});
```

**CSS:**
```css
.copy-button.copied {
  background-color: #16A34A;
  color: white;
  animation: pulse 500ms;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}
```

---

### Checkbox Check

**Animation:**
```css
.checkbox {
  position: relative;
}

.checkbox::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 6px;
  width: 5px;
  height: 10px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg) scale(0);
  transition: transform 200ms ease-out;
}

.checkbox:checked::after {
  transform: rotate(45deg) scale(1);
}
```

**Result:** Checkmark swoops in when checked

---

### Like/Favorite

**Animation:**
```css
.favorite-button {
  transition: transform 150ms ease-out;
}

.favorite-button.active {
  animation: heartbeat 300ms;
}

@keyframes heartbeat {
  0%, 100% { transform: scale(1); }
  25% { transform: scale(1.2); }
  50% { transform: scale(1); }
  75% { transform: scale(1.1); }
}
```

---

## 11. Error States

### Network Error

**Toast:**
```html
<div class="toast error">
  <span class="icon">⚠️</span>
  <div>
    <strong>Connection Lost</strong>
    <p>Retrying in 5 seconds...</p>
  </div>
  <button class="retry">Retry Now</button>
</div>
```

**Animation:**
```css
.toast.error {
  background-color: #FEF2F2;
  border-left: 4px solid #DC2626;
  animation: shake 300ms, slideInRight 300ms;
}
```

---

### Form Error

**Shake + Highlight:**
```css
.form.error {
  animation: shake 300ms;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
  20%, 40%, 60%, 80% { transform: translateX(5px); }
}
```

---

## 12. Success States

### Action Success

**Checkmark Animation:**
```css
.checkmark {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: 4px solid #16A34A;
  animation: scaleIn 200ms ease-out;
}

.checkmark::after {
  content: '';
  display: block;
  width: 16px;
  height: 28px;
  border: solid #16A34A;
  border-width: 0 4px 4px 0;
  transform: rotate(45deg);
  animation: drawCheck 400ms 200ms ease-out forwards;
  transform-origin: center;
  opacity: 0;
}

@keyframes drawCheck {
  to {
    opacity: 1;
    transform: rotate(45deg) scale(1);
  }
}
```

**Result:** Circle appears, then checkmark draws in

---

## Performance Optimization

**Critical Animations:**
- Use `transform` and `opacity` only (GPU-accelerated)
- Avoid animating: width, height, top, left (causes reflow)
- Use `will-change` sparingly

**Good:**
```css
.card {
  transform: translateY(0);
  transition: transform 300ms;
}

.card:hover {
  transform: translateY(-4px);
}
```

**Bad:**
```css
.card {
  top: 0;
  transition: top 300ms;
}

.card:hover {
  top: -4px; /* Causes reflow */
}
```

---

## Accessibility Considerations

**Respect User Preferences:**
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Result:** Users with motion sensitivity see instant state changes

---

**Next:** Accessibility comprehensive checklist
