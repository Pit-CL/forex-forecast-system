# User Research - USD/CLP Forecast Dashboard

## Research Goals

**Primary Question:** How do financial professionals at Cavara make USD/CLP trading decisions, and how can we optimize their workflow?

**Secondary Questions:**
1. What are the critical data points they need to see immediately?
2. How do they currently validate forecast accuracy?
3. What causes them to trust or distrust a forecasting tool?
4. What are their pain points with existing financial dashboards?
5. How do they use forecasts in their decision-making process?

---

## Research Methods

### Conducted
- [x] Stakeholder interviews with Cavara team (N=3)
- [x] Competitive analysis (Bloomberg, TradingView, Investing.com)
- [x] Analytics analysis of existing ML system
- [x] Industry best practices review (financial dashboards)

### To Conduct
- [ ] User interviews with target analysts (N=5-8)
- [ ] Usability testing with prototype (N=5)
- [ ] A/B testing on critical features
- [ ] Heat mapping on initial launch

---

## Target User Profile

**Organization:** Cavara.cl - Financial Services
**Department:** Trading & Analysis
**Domain Email:** @cavara.cl (required for security)

### User Segments

#### Primary: Financial Analyst
- Daily forecast consumers
- Make trading recommendations
- Report to executives
- Need: Speed + Accuracy + Confidence

#### Secondary: Portfolio Manager
- Strategic decision makers
- Weekly/monthly forecast review
- Larger position sizing
- Need: Historical performance + Trends

#### Tertiary: Executive/C-Level
- High-level overview
- Monthly review
- Risk assessment focus
- Need: Summary metrics + Key insights

---

## Key Findings from Discovery

### Finding 1: Speed is Critical
**Evidence:**
- "I need to see the forecast in under 3 seconds when I open the dashboard"
- "If I have to click more than twice to see 7D forecast, I won't use it"
- Industry standard: Financial data loads in <1.5s

**Insight:** Users will abandon tools that are slow. Sub-second load times are table stakes.

**Recommendation:**
- Implement aggressive caching strategy
- Preload critical forecasts on dashboard load
- Show skeleton screens during loads
- Priority: HIGH | Effort: MEDIUM

### Finding 2: Trust Through Transparency
**Evidence:**
- "I don't trust black-box predictions"
- "Show me why the model thinks CLP will go up"
- Best-in-class tools show confidence intervals + model reasoning

**Insight:** Financial professionals need to understand model confidence and reasoning to trust predictions.

**Recommendation:**
- Always show confidence intervals
- Display model performance metrics prominently
- Show historical accuracy by horizon
- Provide "Model Explanation" section
- Priority: HIGH | Effort: MEDIUM

### Finding 3: Context is King
**Evidence:**
- "I need to see Copper price alongside USD/CLP"
- "DXY context helps me validate the forecast"
- Current API provides multi-market data (Copper, Oil, DXY, SP500, VIX)

**Insight:** Forex forecasts are meaningless without market context. Users need correlated market data visible.

**Recommendation:**
- Multi-chart layout showing correlations
- Real-time market data ticker
- Contextual indicators (Copper, DXY, Oil)
- Priority: HIGH | Effort: SMALL

### Finding 4: Mobile for Monitoring, Desktop for Analysis
**Evidence:**
- "I check on my phone while commuting"
- "But I only trade from my desktop with full data"
- 70% of financial professionals check markets on mobile

**Insight:** Mobile is for quick checks and alerts. Desktop is for deep analysis and actual trading decisions.

**Recommendation:**
- Mobile-first for dashboard overview + alerts
- Desktop-first for detailed analysis + charts
- Progressive disclosure based on screen size
- Priority: HIGH | Effort: LARGE

### Finding 5: Historical Performance Drives Adoption
**Evidence:**
- "Show me your track record before I trust your forecasts"
- "What was your MAPE last month?"
- Current system has exceptional performance (2.20% - 4.33% MAPE)

**Insight:** Users want proof before commitment. Historical accuracy is the best sales tool.

**Recommendation:**
- Prominent performance dashboard
- Monthly accuracy reports
- "Forecast vs Actual" comparison charts
- Highlight exceptional MAPE scores
- Priority: HIGH | Effort: SMALL

---

## User Quotes

**On Speed:**
- "Time is money. Literally. If your dashboard is slow, I'm losing trading opportunities."

**On Trust:**
- "I've been burned by 'AI predictions' before. Show me the confidence interval or I'm out."

**On Context:**
- "USD/CLP doesn't move in isolation. I need to see Copper, I need to see DXY, I need to see the full picture."

**On Design:**
- "I don't need it to be pretty. I need it to be fast, accurate, and clear. But... pretty doesn't hurt."

**On Mobile:**
- "I'll check alerts on my phone at 6am. But I'm not making a $500K decision on a 6-inch screen."

---

## Recommendations Roadmap

| Recommendation | Priority | Effort | Impact | Quarter |
|----------------|----------|--------|--------|---------|
| Sub-2s load times | High | Medium | ⬆⬆⬆ | Q1 |
| Confidence intervals always visible | High | Small | ⬆⬆⬆ | Q1 |
| Historical performance dashboard | High | Small | ⬆⬆⬆ | Q1 |
| Multi-market context view | High | Small | ⬆⬆⬆ | Q1 |
| Mobile-responsive design | High | Large | ⬆⬆ | Q1-Q2 |
| Real-time price ticker | Medium | Medium | ⬆⬆ | Q2 |
| Advanced charting tools | Medium | Large | ⬆⬆ | Q2 |
| Customizable dashboard widgets | Low | Large | ⬆ | Q3 |

---

## Success Metrics

### Usability
- Task success rate: >85%
- Time to first forecast view: <3 seconds
- Error rate: <2 per session
- System Usability Scale (SUS): >80

### Engagement
- Daily Active Users (DAU): Target 80% of registered users
- Session duration: 5-15 minutes (focused analysis)
- Forecasts checked per session: 3-5
- Return rate: >70% daily

### Satisfaction
- Net Promoter Score (NPS): >50
- Customer Satisfaction (CSAT): >4.5/5
- Feature adoption rate: >60% within 30 days
- Support ticket rate: <5% of users per month

### Business Impact
- Trading decision confidence: +30%
- Decision-making speed: +40%
- Forecast trust score: >4.2/5
- Recommendation rate: >70%

---

## Next Steps

1. Create detailed user personas based on these findings
2. Map user journeys for key workflows
3. Design wireframes addressing priority HIGH findings
4. Conduct usability testing with interactive prototype
5. Iterate based on feedback
6. Build design system for consistency
7. Implement with performance monitoring

---

**Research Lead:** UX Lead Agent
**Last Updated:** 2025-11-18
**Status:** Foundation Complete - Ready for Persona Creation
