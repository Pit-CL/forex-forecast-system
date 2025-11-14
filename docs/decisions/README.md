# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records documenting significant technical decisions in the forex forecasting system.

## What is an ADR?

An Architecture Decision Record (ADR) captures important architectural decisions along with their context and consequences. Each ADR describes:
- The context and problem statement
- Options considered with trade-offs
- The decision made and why
- Consequences (positive and negative)
- Implementation plan

## ADR Index

### ADR-001: Auto-Retraining Pipeline
**File:** [ADR-001-auto-retraining-pipeline.md](./ADR-001-auto-retraining-pipeline.md)
**Date:** 2025-01-13
**Status:** Proposed

**Summary:**
Automated model optimization pipeline for Chronos forecasting models with trigger detection, hyperparameter optimization, validation, and safe deployment.

**Key Decisions:**
- Container-based architecture (dedicated "Model Optimizer" service)
- Grid search for hyperparameter optimization
- Multi-criteria validation (5 criteria)
- Atomic deployment with automatic rollback

**Impact:**
- 80% automation of model optimizations
- 5-10% expected RMSE improvement
- Zero-downtime deployments
- Reduced manual intervention from 2/month to <0.5/month

---

## ADR Template

When creating a new ADR, use this structure:

```markdown
# ADR-NNN: [Title]

**Date:** YYYY-MM-DD
**Status:** [Proposed | Accepted | Deprecated | Superseded by ADR-XXX]
**Deciders:** [Names]

## Context
[Problem description, forces at play]

## Options Considered
### Option 1: [Name]
- Pros
- Cons
- Effort/Cost/Risk

### Option 2: [Name]
...

## Comparison
[Table comparing options]

## Decision
**Chosen:** Option X
**Justification:** [Why this is best]

## Consequences
- Positive consequences
- Negative consequences (trade-offs)
- Risks and mitigations

## Implementation Plan
[Phases, tasks, timeline]

## Metrics of Success
[How to measure if decision was correct]
```

## ADR Lifecycle

1. **Proposed:** Decision under consideration
2. **Accepted:** Decision approved and being implemented
3. **Deprecated:** Decision no longer recommended
4. **Superseded:** Replaced by newer ADR

## Related Documentation

- **Technical Docs:** [../technical/](../technical/)
- **Summary Docs:** [../AUTO_RETRAINING_SUMMARY.md](../AUTO_RETRAINING_SUMMARY.md)
- **Module README:** [../../src/forex_core/optimization/README.md](../../src/forex_core/optimization/README.md)

---

**Last Updated:** 2025-01-13
