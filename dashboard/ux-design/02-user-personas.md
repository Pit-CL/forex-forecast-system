# User Personas - USD/CLP Forecast Dashboard

---

# Persona 1: Carlos "The Trader"

## Demographics
- **Age:** 32-38
- **Location:** Santiago, Chile
- **Occupation:** Senior FX Trader at Cavara
- **Education:** Master's in Finance, Universidad Católica
- **Income:** $80,000-$120,000 USD/year

## Psychographics
- **Tech savviness:** High - comfortable with APIs, terminal commands, complex software
- **Personality:** Analytical, detail-oriented, competitive, data-driven
- **Values:** Accuracy, speed, transparency, competitive edge
- **Work style:** Fast-paced, multi-screen setup, works 7am-7pm

---

## Goals & Motivations

**Primary Goal:**
Make profitable USD/CLP trading decisions faster than competitors

**Secondary Goals:**
- Validate his own market analysis with ML forecasts
- Reduce time spent on manual technical analysis
- Increase win rate on FX positions
- Build trust in automated forecasting tools

**Motivations:**
- Performance bonuses tied to trading P&L
- Professional reputation among peers
- Stay ahead of market movements
- Prove value to management

---

## Pain Points & Frustrations

### 1. Information Overload
- **Frequency:** Daily
- **Severity:** High
- **Issue:** Too many data sources, charts, terminals open
- **Current workaround:** Multiple monitors, manual synthesis
- **Our solution:** Unified dashboard with key metrics consolidated

### 2. Forecast Unreliability
- **Frequency:** Weekly
- **Severity:** High
- **Issue:** Past ML tools had poor accuracy, destroyed trust
- **Current workaround:** Only trusts his own TA + fundamentals
- **Our solution:** Transparent confidence scores + proven 2.20% MAPE

### 3. Slow Tools
- **Frequency:** Daily
- **Severity:** Medium
- **Issue:** Bloomberg lags, Excel crashes, APIs timeout
- **Current workaround:** Pre-load data, manual refresh loops
- **Our solution:** Sub-2s loads, real-time WebSocket updates

### 4. Mobile Limitations
- **Frequency:** Daily (commute + after hours)
- **Severity:** Medium
- **Issue:** Can't check forecasts properly on phone
- **Current workaround:** Wait until desktop, sometimes miss moves
- **Our solution:** Mobile-optimized dashboard for quick checks

---

## Behavior Patterns

**How he discovers solutions:**
- Recommendations from other traders (high trust)
- Financial tech conferences
- LinkedIn groups (FX traders community)
- Trial and error with free trials

**Decision-making process:**
1. See recommendation from peer (1 day)
2. Google reviews + track record (2 days)
3. Sign up for trial (immediate if looks good)
4. Test against his own analysis for 2 weeks
5. If 80%+ alignment → adopt fully
6. Recommend to team if successful

**Technology usage:**
- **Devices:**
  - Primary: Desktop PC (triple monitor setup, Windows)
  - Secondary: iPhone 13 Pro (market checks, alerts)
  - Occasionally: iPad Pro (weekend analysis)
- **Preferred platforms:** Desktop web apps > Mobile apps > APIs
- **Apps he uses:** Bloomberg Terminal, TradingView, MetaTrader 5, Excel, Slack
- **Active hours:** 7am-7pm weekdays, occasional weekend checks

---

## Scenarios & Use Cases

### Scenario 1: Morning Forecast Check
**Context:** 7:15am, just arrived at office, coffee in hand, needs to plan day's trades

**Current workflow (without our tool):**
1. Opens Bloomberg Terminal - 30s load time - Pain: slow startup
2. Checks overnight USD/CLP movement - 1 minute
3. Opens Excel with his prediction model - 45s - Pain: manual data entry
4. Cross-references with TradingView charts - 2 minutes
5. Reads news headlines - 3 minutes
6. Makes decision by 7:30am (15 min total)

**Ideal workflow (with our dashboard):**
1. Opens USD/CLP Forecast Dashboard - <2s load - Better: instant
2. Sees current rate + 7D/15D forecasts immediately - 10s - Better: no navigation
3. Reviews confidence intervals + model accuracy - 20s
4. Checks correlated markets (Copper, DXY) in same view - 15s
5. Makes informed decision by 7:20am (under 1 min total)
**Time saved: 14 minutes per morning = 70 minutes/week**

### Scenario 2: Mid-Day Position Adjustment
**Context:** 2pm, USD/CLP spiked 0.8%, needs to decide: hold, add, or exit position?

**Current workflow:**
1. Panics, checks Bloomberg for news - 1 minute - Pain: information scattered
2. Opens TradingView to see if spike is real or noise - 1 minute
3. Calls analyst colleague for opinion - 3 minutes - Pain: delays decision
4. Checks his Excel model (outdated data) - Pain: not real-time
5. Makes gut-feel decision under pressure - 5+ minutes

**Ideal workflow:**
1. Gets mobile alert: "USD/CLP +0.8%, forecast still within confidence interval"
2. Opens dashboard on phone - sees spike is within predicted range
3. Reviews 15D forecast - still bullish with 85% confidence
4. Decides to hold position with confidence - under 1 minute
**Stress reduced, decision confidence improved**

### Scenario 3: Weekly Performance Review
**Context:** Friday 5pm, reviewing week's forecast accuracy vs actual moves

**Current workflow:**
1. Downloads USD/CLP data from Bloomberg to Excel - 5 minutes
2. Compares to his Monday predictions - manual chart - 10 minutes
3. Calculates error rates - Excel formulas - 5 minutes
4. Realizes he can't compare to ML model easily - Pain: no benchmark
5. Gives up on quantitative review - Pain: no learning

**Ideal workflow:**
1. Opens "Performance" page on dashboard
2. Sees: "This Week: 7D Forecast MAPE 2.1% | Your Best Week Yet!"
3. Reviews interactive "Forecast vs Actual" chart with annotations
4. Sees which horizons were most accurate this week
5. Exports report for team meeting - 2 minutes total
**Learn from model, improve own analysis**

---

## Quotes
- "I don't have time for pretty dashboards. Show me the number, show me the confidence, let me trade."
- "If your forecast is wrong 3 times in a row, I'll never open your app again. Trust is everything."
- "Bloomberg costs us $2,000/month per seat. If you can give me better FX forecasts for less, I'm in."
- "I need to know: is this prediction based on fundamentals, technicals, or just random forest guessing?"

---

## Design Implications

**For Carlos, we should:**
- ✅ Optimize for SPEED above all else (<2s loads, instant updates)
- ✅ Show confidence intervals ALWAYS (he won't trade without them)
- ✅ Provide historical accuracy data prominently
- ✅ Design for multi-screen desktop setups (he'll put this on monitor #2)
- ✅ Mobile alerts for critical forecast changes
- ✅ Export functionality (Excel, CSV, PDF) for reporting
- ✅ Keyboard shortcuts for power users
- ❌ Avoid tutorials/onboarding (he'll figure it out)
- ❌ Don't hide features behind menus (he wants everything visible)
- ❌ No fluff or marketing copy (just data)

---

# Persona 2: María "The Analyst"

## Demographics
- **Age:** 28-34
- **Location:** Santiago, Chile
- **Occupation:** Financial Analyst at Cavara
- **Education:** Bachelor's in Economics, Universidad de Chile
- **Income:** $50,000-$75,000 USD/year

## Psychographics
- **Tech savviness:** Medium-High - uses Excel, BI tools, learning Python
- **Personality:** Methodical, thorough, risk-averse, collaborative
- **Values:** Accuracy, methodology, learning, teamwork
- **Work style:** Structured, 9am-6pm, detail-oriented reports

---

## Goals & Motivations

**Primary Goal:**
Provide accurate, well-researched USD/CLP forecasts to portfolio managers

**Secondary Goals:**
- Understand the "why" behind forecast movements
- Compare ML predictions to her fundamental analysis
- Create professional reports for management
- Learn from ML model to improve her skills

**Motivations:**
- Career growth to Senior Analyst
- Be seen as the "go-to" person for USD/CLP insights
- Reduce time on repetitive analysis tasks
- Deliver value to decision-makers

---

## Pain Points & Frustrations

### 1. Data Collection is Tedious
- **Frequency:** Daily
- **Severity:** Medium
- **Issue:** Pulls data from 5+ sources manually (BCCh, Yahoo, Bloomberg)
- **Current workaround:** Excel macros that break frequently
- **Our solution:** All data pre-integrated, one dashboard

### 2. Hard to Explain Forecasts to Non-Technical Stakeholders
- **Frequency:** Weekly
- **Severity:** High
- **Issue:** PMs don't understand "MAPE" or "confidence intervals"
- **Current workaround:** Simplifies to "bullish/bearish" - loses nuance
- **Our solution:** Visual explanations, plain-language insights

### 3. No Easy Way to Track Forecast Accuracy Over Time
- **Frequency:** Monthly
- **Severity:** Medium
- **Issue:** Manual comparison of predictions vs actuals
- **Current workaround:** Messy Excel file with formulas
- **Our solution:** Automated performance tracking dashboard

---

## Behavior Patterns

**How she discovers solutions:**
- Recommendations from colleagues
- LinkedIn articles on financial tools
- Webinars on ML in finance
- Free trials before purchase decisions

**Decision-making process:**
1. Sees colleague using tool (1 day)
2. Asks for demo or trial (same day)
3. Tests with small dataset (3-5 days)
4. Presents to manager with pros/cons (1 week)
5. If approved → adoption (requires team buy-in)

**Technology usage:**
- **Devices:** Work laptop (MacBook Pro), iPhone 12
- **Preferred platforms:** Web apps (Chrome), Excel, PowerPoint
- **Apps she uses:** Excel, Bloomberg (limited), Tableau, Notion, Google Workspace
- **Active hours:** 9am-6pm weekdays, rare weekend work

---

## Scenarios & Use Cases

### Scenario 1: Preparing Weekly Report
**Context:** Thursday afternoon, preparing Friday morning report for Portfolio Manager

**Current workflow:**
1. Opens Excel with historical USD/CLP data - 2 minutes
2. Updates with latest data from Bloomberg - 5 minutes - Pain: manual copy-paste
3. Calculates technical indicators manually - 10 minutes
4. Writes commentary on trends - 15 minutes
5. Creates charts in Excel - 10 minutes - Pain: not visually appealing
6. Exports to PowerPoint, formats - 10 minutes
7. Reviews and sends - Total: 52 minutes

**Ideal workflow:**
1. Opens dashboard "Export Report" page
2. Selects date range (last 7 days)
3. Reviews auto-generated insights: "USD/CLP +1.2% this week, 7D forecast suggests continued uptrend"
4. Customizes commentary if needed - 5 minutes
5. Exports professional PDF report - 1-click
6. Sends to PM - Total: 8 minutes
**Time saved: 44 minutes per week**

### Scenario 2: Explaining Forecast to Portfolio Manager
**Context:** Meeting with PM who asks: "Why does the model predict CLP weakness?"

**Current workflow:**
1. Tries to explain model internals - PM's eyes glaze over
2. Shows complex Excel chart - PM: "I don't understand"
3. Resorts to: "The model says so, it's usually accurate" - Pain: not convincing
4. PM makes decision without full confidence - Pain: credibility issue

**Ideal workflow:**
1. Opens "Model Explanation" page on dashboard
2. Shows visual: "Top factors driving this forecast:"
   - Copper price down 3.2% → CLP weaker (30% influence)
   - DXY up 1.1% → CLP weaker (25% influence)
   - Historical pattern match: 85% similarity to Oct 2023 → CLP weakened then
3. PM: "Ah, that makes sense. Copper is key for Chile."
4. PM makes confident decision based on understanding
**Credibility increased, PM trust improved**

---

## Quotes
- "I need to understand WHY before I can recommend a trade. 'The AI said so' isn't good enough."
- "My reports need to look professional. Excel charts don't cut it anymore."
- "If I can save 2 hours a week on data collection, I can spend that on actual analysis."
- "I want to learn from the model. What patterns is it seeing that I'm missing?"

---

## Design Implications

**For María, we should:**
- ✅ Provide "Explain this forecast" feature with plain language
- ✅ Easy export to PDF/PowerPoint for reports
- ✅ Visual, professional charts (not just raw data)
- ✅ Historical tracking and trend analysis
- ✅ Educational tooltips ("What is MAPE?" → short explanation)
- ✅ Collaborative features (share reports, comments)
- ✅ Onboarding tutorial (she'll appreciate guidance)
- ❌ Avoid overwhelming with too many technical metrics upfront
- ❌ Don't require coding or API knowledge

---

# Persona 3: Roberto "The Executive"

## Demographics
- **Age:** 45-55
- **Location:** Santiago, Chile
- **Occupation:** VP of Trading / Portfolio Director at Cavara
- **Education:** MBA, top-tier business school
- **Income:** $200,000+ USD/year

## Psychographics
- **Tech savviness:** Medium - delegates technical work, uses tools strategically
- **Personality:** Strategic, decisive, results-focused, time-constrained
- **Values:** ROI, risk management, competitive advantage, team performance
- **Work style:** High-level oversight, many meetings, quick decision windows

---

## Goals & Motivations

**Primary Goal:**
Optimize trading team performance and reduce portfolio risk

**Secondary Goals:**
- Validate that ML forecasting investment delivers ROI
- Monitor team's use of forecasting tools
- Ensure competitive edge over other trading desks
- Report positive results to C-suite / board

**Motivations:**
- Bonus tied to portfolio performance
- Reputation as innovative leader
- Reduce team overhead costs
- Stay ahead of market competitors

---

## Pain Points & Frustrations

### 1. Can't Quickly Assess Forecast Performance
- **Frequency:** Weekly
- **Severity:** High
- **Issue:** Asks team "how accurate are the forecasts?" → gets anecdotes, not data
- **Current workaround:** Trusts team's gut feel
- **Our solution:** Executive dashboard with clear KPIs

### 2. Difficult to Justify ML Investment to CFO
- **Frequency:** Quarterly
- **Severity:** High
- **Issue:** CFO asks "What's the ROI on this forecasting system?"
- **Current workaround:** Vague estimates, hard to quantify
- **Our solution:** ROI tracking, performance vs benchmarks

### 3. No Visibility into System Usage
- **Frequency:** Monthly
- **Severity:** Medium
- **Issue:** Is the team actually using the tool we paid for?
- **Current workaround:** Asks in meetings (self-reported, unreliable)
- **Our solution:** Usage analytics dashboard

---

## Behavior Patterns

**How he discovers solutions:**
- Executive briefings from vendors
- Peer recommendations at industry events
- Internal proposals from team leads
- Board member suggestions

**Decision-making process:**
1. Sees proposal or pitch (15-30 min meeting)
2. Asks for ROI projection and case studies (same day)
3. Delegates evaluation to team lead (1 week)
4. Reviews team recommendation (1 meeting)
5. If ROI > 3x and risk is low → approves budget
6. Expects quarterly performance reviews

**Technology usage:**
- **Devices:** iPad Pro (primary for reviews), iPhone, rarely desktop
- **Preferred platforms:** Mobile-friendly dashboards, email summaries
- **Apps he uses:** Outlook, Tableau dashboards, Slack (sparingly), Teams
- **Active hours:** 8am-7pm but fragmented (meetings), weekend email checks

---

## Scenarios & Use Cases

### Scenario 1: Monday Morning Portfolio Review
**Context:** 8:30am, reviewing weekend developments before team meeting at 9am

**Current workflow:**
1. Asks assistant to compile weekend FX movements - 15 min wait
2. Reads email summaries from analysts - 10 minutes - Pain: inconsistent format
3. Calls senior trader for verbal update - 5 minutes - Pain: subjective opinions
4. Goes into meeting without full quantitative picture - Total: 30+ minutes

**Ideal workflow:**
1. Opens dashboard on iPad - <3s
2. Sees "Executive Summary" page:
   - "USD/CLP: 948.30 (+0.6% week)"
   - "7D Forecast: 952.15 (bullish, 87% confidence)"
   - "Model Accuracy This Month: 2.1% MAPE (Excellent)"
   - "Team checked forecasts 47 times this week"
3. Confident for meeting - Total: 2 minutes
**Saves 28 minutes, better informed**

### Scenario 2: Quarterly Board Presentation
**Context:** Preparing slides to show board the value of ML forecasting investment

**Current workflow:**
1. Asks analysts to prepare performance data - 2 days
2. Receives inconsistent Excel files - Pain: not presentation-ready
3. Asks assistant to make PowerPoint - 1 day
4. Reviews and has to request revisions - 0.5 days
5. Hopes the data is accurate - Pain: no confidence in numbers
**Total: 3.5 days of team time**

**Ideal workflow:**
1. Opens "Performance" dashboard
2. Clicks "Export Quarterly Report" → auto-generated professional PDF
3. Shows:
   - Forecast accuracy by month (trend chart showing improvement)
   - ROI calculation: "Trading decisions informed by forecasts: +12% P&L vs benchmark"
   - Team adoption: "87% daily active usage"
   - Cost savings: "Reduced external forecast subscriptions by $30k/year"
4. Downloads, adds to board deck - Total: 15 minutes
**Saves 3+ days of team time, data-driven story**

---

## Quotes
- "I don't need to see every chart. Just tell me: Are we winning or losing?"
- "If we're paying for this ML system, I want to see the ROI in dollars, not MAPE percentages."
- "My traders better be using this tool. If they're not, why did we build it?"
- "I'll give you 60 seconds in our Monday meeting. Show me what I need to know."

---

## Design Implications

**For Roberto, we should:**
- ✅ Create dedicated "Executive Summary" dashboard (high-level KPIs only)
- ✅ Mobile-first design for iPad (he won't use desktop much)
- ✅ One-click PDF export for presentations
- ✅ ROI tracking and reporting
- ✅ Usage analytics (team adoption metrics)
- ✅ Alerts for significant forecast changes or accuracy issues
- ✅ Comparison to benchmarks (industry standard, previous models)
- ❌ Avoid technical jargon (use plain business language)
- ❌ Don't require him to navigate deep menus (everything on homepage)
- ❌ No training required (must be instantly intuitive)

---

## Summary: Design Priorities by Persona

| Feature | Carlos (Trader) | María (Analyst) | Roberto (Executive) |
|---------|-----------------|-----------------|---------------------|
| Speed (<2s loads) | CRITICAL | Important | Important |
| Confidence Intervals | CRITICAL | Important | Nice to have |
| Historical Performance | CRITICAL | CRITICAL | CRITICAL |
| Mobile Experience | Alerts only | Nice to have | CRITICAL |
| Export/Reports | Medium | CRITICAL | CRITICAL |
| Explanations | Low | CRITICAL | Medium |
| Executive Summary | Not needed | Not needed | CRITICAL |
| Technical Depth | CRITICAL | Medium | Low |
| Keyboard Shortcuts | CRITICAL | Medium | Not needed |

---

**Next Step:** Create user journey maps for each persona's critical workflows.
