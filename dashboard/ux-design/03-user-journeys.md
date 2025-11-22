# User Journey Maps - USD/CLP Forecast Dashboard

---

## Journey 1: First-Time User (Carlos - The Trader)

**Scenario:** Carlos heard about the new USD/CLP forecast tool from a colleague. He's skeptical but willing to try.

---

### Stage 1: Discovery & Awareness

**Actions:**
- Colleague mentions "new ML forecast tool at Cavara"
- Googles "USD CLP forecast machine learning"
- Receives email from IT: "New Trading Tool Available"
- Clicks link in email

**Thoughts:**
- "Another 'AI' tool that probably doesn't work..."
- "But if it's good, could save me hours per week"
- "Let me check it out for 5 minutes"

**Emotions:** 😐 Skeptical, mildly curious

**Pain points:**
- Tired of overhyped "AI" tools that underdeliver
- Burned by previous ML forecasts that were wildly inaccurate
- Doesn't want to waste time learning another tool

**Opportunities:**
- Clear, honest messaging about accuracy (show MAPE upfront)
- "No BS" landing page - just the facts
- Instant access (no lengthy approval process)
- Social proof (which colleagues already use it)

**Touchpoints:**
- Colleague recommendation (highest trust)
- Email from IT
- Internal Cavara portal
- Login page

---

### Stage 2: Registration & First Login

**Actions:**
- Arrives at login page
- Sees "Sign Up" button
- Enters @cavara.cl email
- Creates password (strong requirements shown)
- Receives verification email
- Clicks link, email verified
- Redirected to dashboard

**Thoughts:**
- "Okay, simple enough"
- "Good, they require strong passwords - they take security seriously"
- "I hope this doesn't have a painful onboarding tutorial..."

**Emotions:** 😐 Neutral, cautiously optimistic

**Pain points:**
- Hates long registration forms
- Annoyed by verification delays
- Dreads mandatory tutorials

**Opportunities:**
- FAST registration (4 fields max: email, name, password, confirm)
- Instant email verification (no waiting)
- Skip/dismiss onboarding tour (Carlos will explore himself)
- Show value immediately on first screen

**Touchpoints:**
- Registration page
- Email inbox (verification)
- Dashboard (first impression)

**Design Requirements:**
```
Registration Form:
- Email (auto-detect @cavara.cl domain)
- Full Name
- Password (with strength indicator)
- Confirm Password

Success Flow:
- Register → Email sent → Verify → Login → Dashboard (total time <90 seconds)

Email Template:
"Welcome to USD/CLP Forecast Dashboard
Click here to verify: [BUTTON]
Link expires in 24 hours"
```

---

### Stage 3: First Impression (Critical!)

**Actions:**
- Dashboard loads in <2 seconds
- Sees current USD/CLP rate: **948.30 CLP** (large, prominent)
- Sees 7D forecast: **952.15 CLP** (+0.41%) with green up arrow
- Sees confidence: **87%** (high)
- Sees historical accuracy: **"7D MAPE: 2.20%"** (excellent)
- Sees main chart with historical data + forecast line
- Eyes scan: Copper price, DXY, Oil (correlated markets)

**Thoughts:**
- "Okay, this is FAST. I like that."
- "2.20% MAPE? That's... actually impressive. Is that real?"
- "Confidence 87%? Let me see why..."
- "Clean layout. No clutter. Good."

**Emotions:** 🤔 Intrigued, cautiously impressed

**Pain points:**
- Wants to verify MAPE is real (trust issue)
- Needs to understand why confidence is 87%
- Wants to see historical forecast vs actual

**Opportunities:**
- PROMINENT accuracy display (can't miss it)
- One-click to "Forecast vs Actual" historical chart
- Tooltip on confidence: "Based on model performance + market volatility"
- Visual design that screams "professional" not "startup toy"

**Touchpoints:**
- Dashboard homepage
- Main forecast chart
- Confidence display
- Performance metrics

**Design Requirements:**
```
Dashboard Hero Section:
┌─────────────────────────────────────────────┐
│ USD/CLP SPOT: 948.30 ▲ +0.6% (2.5 hours ago)│
│                                              │
│ 7D FORECAST: 952.15 CLP   ▲ +0.41%          │
│ Confidence: ████████░░ 87%                   │
│ [Why?] ← clickable                          │
│                                              │
│ Model Accuracy (Last 30 Days): 2.20% MAPE   │
│ [See Full History] ← clickable              │
│                                              │
│ ╔═══════════════════════════════════════╗   │
│ ║        [MAIN CHART - 60% width]       ║   │
│ ║  Historical (solid) + Forecast (dash) ║   │
│ ║  With confidence interval (shaded)    ║   │
│ ╚═══════════════════════════════════════╝   │
└─────────────────────────────────────────────┘
```

---

### Stage 4: Exploration (First 5 Minutes)

**Actions:**
- Clicks on confidence tooltip → sees explanation modal
  - "87% confidence based on: historical 7D forecast accuracy (92%), current market volatility (low), data quality (high)"
- Closes modal, satisfied
- Clicks on "See Full History" link
- Sees beautiful "Forecast vs Actual" comparison chart
- Notices: last 30 forecasts, 27 were within confidence interval
- Thinks: "This is legit."
- Clicks on "15D" tab to see longer forecast
- Clicks on "30D", "90D" - sees confidence decreases for longer horizons (good sign)
- Checks Copper chart - sees it's updated real-time

**Thoughts:**
- "Okay, this is actually good. The accuracy checks out."
- "They're honest about uncertainty (lower confidence for 90D) - I respect that"
- "Real-time data. No delays. Perfect."
- "I can use this."

**Emotions:** 😊 Impressed, gaining trust

**Pain points:**
- None! Smooth experience.
- Maybe: "I wish I could see intraday forecasts" (future feature)

**Opportunities:**
- Delight moment: Show animation when forecast updates real-time
- Gamification: "You're one of the first 20 users! Check daily for early adopter badge"
- Social proof: "47 Cavara traders checked forecasts today"

**Touchpoints:**
- Confidence explanation modal
- Historical performance page
- Multiple horizon tabs (7D, 15D, 30D, 90D)
- Real-time data updates

---

### Stage 5: First Trading Decision

**Actions:**
- It's 9:30am, Carlos needs to decide: open USD long position?
- Opens dashboard (he kept tab open)
- Checks 7D forecast: bullish (952.15 vs current 948.30)
- Checks 15D forecast: also bullish (955.80)
- Confidence both >80%
- Checks Copper: down slightly (aligns with USD/CLP up)
- Checks DXY: up (aligns with USD strength)
- Thinks: "Macro aligns with forecast. Let's do it."
- Opens trading terminal
- **Places USD long trade**
- Adds note: "Per ML forecast 7D+15D bullish"

**Thoughts:**
- "This gave me the confidence to trade larger size"
- "I'm combining my analysis + ML forecast = better edge"
- "Let's see if it plays out..."

**Emotions:** 😊 Confident, hopeful

**Pain points:**
- None in this moment
- Future: "I wish I could set alert if forecast changes significantly"

**Opportunities:**
- Track user's implicit "trades" (when they check forecast then close)
- Future: Integration with trading terminal (API)
- Alert feature: "7D forecast changed from bullish to bearish - review?"

**Touchpoints:**
- Dashboard (decision support)
- Trading terminal (external)

---

### Stage 6: Follow-Up (2 Days Later)

**Actions:**
- USD/CLP moved to 951.20 (forecasted 952.15)
- Carlos opens dashboard
- Sees: "Your 7D forecast is tracking well! Current: 951.20, Forecast: 952.15 (diff: -0.10%)"
- Smiles

**Thoughts:**
- "It's working! Within margin of error."
- "I'm going to use this every day now."

**Emotions:** 😄 Delighted, trust solidified

**Pain points:**
- Wants to share this win with team

**Opportunities:**
- Automatic "forecast accuracy update" notification
- "Share your forecast success" feature (internal leaderboard?)
- Prompt: "Enjoying the dashboard? Invite a colleague"

**Touchpoints:**
- Dashboard
- Email notification (optional)
- Slack integration (future)

---

### Stage 7: Advocacy (1 Week Later)

**Actions:**
- Team meeting, discussing USD/CLP strategy
- Carlos: "By the way, the new ML forecast tool is actually really good. 2% MAPE. I've been using it all week."
- Another trader: "Really? I ignored that email..."
- Carlos: "Check it out. It's fast, accurate, and doesn't BS you."
- Two more traders sign up that day

**Thoughts:**
- "I'm glad I tried this. Competitive edge."
- "Hope too many people don't start using it... but it's internal so okay"

**Emotions:** 😊 Satisfied, advocate

**Touchpoints:**
- Word of mouth
- Team meetings
- Slack channels

---

## Emotions Over Time (Carlos)

```
😄 Delighted   |                            ╱─────
😊 Pleased     |                    ╱──────╱
🤔 Intrigued   |              ╱────╱
😐 Skeptical   |  ───────────╱
😟 Frustrated  |
               |_________________________________________
                Discovery Register First Use Trade Follow-up Advocate
                          |<-- Critical Window -->|
                             (First 5 minutes)
```

---

## Key Insights - Carlos's Journey

### Drop-off Risk Points
1. **Registration:** If too complex → Abandon
   - **Fix:** 4 fields max, instant verification
2. **First Load:** If >3 seconds → Skepticism confirmed → Leave
   - **Fix:** Sub-2s load, cached data, skeleton screens
3. **First Impression:** If accuracy not obvious → No trust → Leave
   - **Fix:** MAPE front and center, "See proof" link prominent

### Delight Moments
1. **Fast Load:** "Wow, that was instant"
2. **Accuracy Reveal:** "2.20% MAPE... that's Bloomberg-level"
3. **First Correct Forecast:** "It actually worked!"

### Conversion Points
- Discovery → Registration: Show MAPE in email (credibility)
- Registration → Active Use: Flawless first 5 minutes
- Active Use → Advocate: Consistent accuracy over 1 week

---

## Journey 2: Daily Active User (María - The Analyst)

**Scenario:** María has been using the dashboard for 2 weeks. She needs to create her weekly report for Friday morning.

---

### Stage 1: Report Preparation (Thursday 3pm)

**Actions:**
- Opens dashboard (bookmarked, loads <2s)
- Navigates to "Reports" section
- Clicks "Weekly Performance Report"
- Selects date range: Last 7 days
- Reviews auto-generated summary:
  - "USD/CLP ranged 945-952 this week (+0.7%)"
  - "7D forecasts were 2.1% MAPE (excellent)"
  - "15D forecasts trending bullish with 82% confidence"
  - "Key drivers: Copper -2.3%, DXY +1.1%"

**Thoughts:**
- "Perfect, this is exactly what I need"
- "I'll just add some commentary on why Copper dropped"

**Emotions:** 😊 Efficient, satisfied

**Pain points:**
- Wants to customize the report template
- Needs to add client-specific commentary

**Opportunities:**
- Customizable report templates
- "Add commentary" text box
- Save favorite reports

**Touchpoints:**
- Reports section
- Report generator
- Export functionality

---

### Stage 2: Export & Presentation

**Actions:**
- Adds custom commentary: "Copper weakness driven by China demand concerns, expect continued USD/CLP upside if trend persists"
- Selects export format: PDF (for email) + PowerPoint (for meeting)
- Clicks "Export Report"
- Downloads in 3 seconds
- Opens PDF: beautifully formatted, professional charts, Cavara branding
- Attaches to email to Portfolio Manager
- Subject: "Weekly USD/CLP Forecast Report - Week of Nov 18"
- Sends

**Thoughts:**
- "This used to take me 45 minutes. I just did it in 8 minutes."
- "The charts look so much better than my Excel ones"

**Emotions:** 😄 Delighted, relieved

**Opportunities:**
- Email integration (send report directly from dashboard)
- Schedule automated weekly reports
- Template library (different stakeholder versions)

**Touchpoints:**
- Export functionality
- Email client (external)

---

## Journey 3: Executive Review (Roberto - VP)

**Scenario:** Roberto needs to present ML forecasting ROI to the CFO in 30 minutes.

---

### Stage 1: Last-Minute Prep (Panic Mode)

**Actions:**
- Opens dashboard on iPad
- Taps "Executive Summary" (his default view)
- Sees key metrics:
  - **Model Performance This Quarter: 2.8% MAPE**
  - **Trading Decisions Informed: 342**
  - **Estimated P&L Impact: +$1.2M** (compared to benchmark)
  - **Team Adoption: 87% daily active users**
  - **Cost Savings: $45,000/year** (vs external forecasts)
- Taps "Export Summary" → PDF generated
- AirDrops to MacBook
- Adds to CFO presentation

**Thoughts:**
- "Thank god for this dashboard. I would've scrambled otherwise."
- "These numbers tell a clear story. CFO will be pleased."

**Emotions:** 😌 Relieved, confident

**Opportunities:**
- Scheduled executive reports (every Monday morning)
- Benchmarking vs industry standards
- ROI calculator (input: team time saved, output: $ value)

**Touchpoints:**
- Executive summary page (iPad)
- Export functionality
- Presentation software (external)

---

### Stage 2: CFO Meeting

**Actions:**
- Shows PDF in meeting
- CFO: "So we spent $X building this. What's the return?"
- Roberto: "Model has informed 342 trading decisions this quarter with +$1.2M P&L vs benchmark. That's a 15x ROI."
- CFO: "And the team is actually using it?"
- Roberto: "87% daily active users. It's become essential."
- CFO: "Approved for ongoing funding."

**Thoughts:**
- "Data-driven decision making. Love it."

**Emotions:** 😄 Successful, validated

**Touchpoints:**
- Presentation
- CFO approval

---

## Emotions Over Time (María - Weekly Cycle)

```
😊 Satisfied   |  ╱─╲─╱─╲─╱─╲─╱─╲─╱ (consistent positive)
😐 Neutral     |─╱   ╲   ╲   ╲   ╲
😟 Frustrated  |
               |_________________________________
                Mon Tue Wed Thu Fri Weekend
                            ▲
                      Report day (used to be stressful,
                       now smooth)
```

---

## Summary: Critical UX Moments

| Journey Stage | Make-or-Break Moment | Design Solution |
|---------------|----------------------|-----------------|
| **First Impression** | "Is this tool credible?" | Show MAPE immediately, "Forecast vs Actual" prominent |
| **First Use** | "Is this fast?" | <2s loads, real-time updates |
| **Daily Use** | "Does this save me time?" | One-click reports, export functionality |
| **Trust Building** | "Is this accurate?" | Historical performance tracking, transparent confidence |
| **Advocacy** | "Should I recommend?" | Consistent accuracy, team adoption visible |
| **Executive Buy-In** | "What's the ROI?" | Automated executive reports, P&L tracking |

---

**Next Step:** Create wireframes for key pages identified in user journeys.
