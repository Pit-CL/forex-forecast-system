# Architecture Decision Records (ADRs)

This document tracks key architectural decisions made during the migration from importer_macro_report to forex-forecast-system.

**Last Updated:** 2025-11-12

---

## ADR-001: Use `forex_core` as Shared Library Namespace

**Date:** 2025-11-12
**Status:** ACCEPTED

### Context

The migration requires extracting shared functionality from the monolithic importer_macro_report into a reusable library that multiple services can depend on. We needed to decide on a namespace and package structure.

### Decision

We will use `forex_core` as the namespace for the shared library containing:
- Configuration management
- Data source integrations
- Forecasting models
- Common utilities
- Shared data models

### Rationale

**Pros:**
- Clear, descriptive name that indicates domain (forex/FX trading)
- `_core` suffix indicates foundational/shared nature
- Follows Python naming conventions (lowercase with underscores)
- Avoids conflicts with existing forex-related packages
- Easy to import: `from forex_core.config import Settings`

**Cons:**
- Slightly verbose compared to alternatives like `fx` or `core`
- May need to be published to PyPI if used across multiple repos

### Alternatives Considered

1. **`fx_core`** - Too generic, could conflict with other FX packages
2. **`core`** - Too generic, likely naming conflicts
3. **`importer_core`** - Tied to old system name, not future-proof
4. **`forecast_core`** - Doesn't reflect full scope (data sources, reporting)

### Consequences

- All services will import from `forex_core` namespace
- Package can be installed as editable dependency during development
- Clear separation between shared library and service-specific code
- May publish to private PyPI or use git dependencies

### Implementation

```python
# Directory structure
forex_core/
├── __init__.py
├── config/
├── data_sources/
├── models/
├── forecasting/
└── utils/
```

---

## ADR-002: Microservices Architecture with Three Core Services

**Date:** 2025-11-12
**Status:** ACCEPTED

### Context

The monolithic importer_macro_report combines data collection, forecasting, and report generation in a single application. As we scale and add more report types, this becomes difficult to maintain and deploy.

### Decision

Split the system into three independent microservices:

1. **Data Collector Service** - Fetches and stores data from APIs
2. **Forecast Engine Service** - Runs forecasting models on demand
3. **Report Generator Service** - Creates PDF reports with charts

### Rationale

**Pros:**
- Independent scaling (e.g., scale forecast engine during heavy computation)
- Isolated failures (data collection issue doesn't crash report generation)
- Technology flexibility (could rewrite forecast engine in R/Julia if needed)
- Easier testing and deployment
- Clear separation of concerns
- Multiple teams can work independently

**Cons:**
- Increased complexity in orchestration
- Network latency between services
- More infrastructure to manage
- Distributed system challenges (eventual consistency, etc.)

### Alternatives Considered

1. **Keep monolith** - Doesn't solve scalability/maintainability issues
2. **Two services** (data + compute) - Still couples forecasting and reporting
3. **More fine-grained services** - Over-engineering for current scale

### Consequences

- Need inter-service communication (REST APIs or message queue)
- Require service discovery/orchestration (Docker Compose for now)
- Each service has its own repository or service directory
- Shared data storage strategy needed
- Monitoring and logging must work across services

### Implementation

```
services/
├── data_collector/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
├── forecast_engine/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
└── report_generator/
    ├── Dockerfile
    ├── requirements.txt
    └── src/
```

---

## ADR-003: Pydantic Settings for Configuration Management

**Date:** 2025-11-12
**Status:** ACCEPTED

### Context

The current system uses manual environment variable parsing with `os.getenv()` and has limited validation. As we add more services, we need a robust, type-safe configuration system.

### Decision

Use **Pydantic Settings** for all configuration management across services.

### Rationale

**Pros:**
- Type safety with automatic validation
- Environment variable parsing with type coercion
- Support for .env files
- Nested configuration objects
- IDE autocomplete support
- Excellent documentation
- Validation errors are clear and helpful
- Supports complex types (lists, dicts, enums)

**Cons:**
- Additional dependency
- Learning curve for developers unfamiliar with Pydantic
- Slightly more verbose than simple dict-based config

### Alternatives Considered

1. **python-decouple** - Less type safety, no validation
2. **dynaconf** - More features but heavier, overkill for our needs
3. **configparser** - INI files, outdated approach
4. **Plain dataclasses** - Would need custom env parsing logic

### Consequences

- All configuration classes will inherit from `pydantic_settings.BaseSettings`
- Environment variables will be automatically validated on startup
- Configuration errors will fail fast with clear messages
- Documentation can be auto-generated from Pydantic models

### Implementation

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr

class BCChSettings(BaseSettings):
    """BCCh API configuration."""

    model_config = SettingsConfigDict(
        env_prefix='BCCH_',
        env_file='.env',
        env_file_encoding='utf-8'
    )

    api_user: str = Field(..., description="BCCh API username")
    api_password: SecretStr = Field(..., description="BCCh API password")
    base_url: str = Field(
        default="https://si3.bcentral.cl/SieteWS/SieteWS",
        description="BCCh API base URL"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")
```

---

## ADR-004: Directory Structure Optimized for Microservices

**Date:** 2025-11-12
**Status:** ACCEPTED

### Context

Needed to define a clear directory structure that supports:
- Shared library code (forex_core)
- Multiple independent services
- Shared data storage
- Comprehensive documentation
- Utility scripts

### Decision

Implement the following structure:

```
forex-forecast-system/
├── forex_core/              # Shared library
│   ├── config/             # Configuration management
│   ├── data_sources/       # API clients
│   ├── models/             # Pydantic models
│   ├── forecasting/        # Forecasting engine
│   └── utils/              # Utilities
├── services/
│   ├── data_collector/     # Data collection service
│   ├── forecast_engine/    # Forecasting service
│   └── report_generator/   # Report generation service
├── shared/
│   └── data/              # Shared data storage
├── docs/
│   ├── migration/         # Migration docs
│   ├── architecture/      # Architecture docs
│   └── api/              # API documentation
├── scripts/               # Utility scripts
├── docker-compose.yml     # Service orchestration
└── README.md
```

### Rationale

**Pros:**
- Clear separation between shared library and services
- Each service is self-contained
- Shared data directory for inter-service data exchange
- Documentation is well-organized
- Scripts are easily accessible
- Scales well as services are added

**Cons:**
- More directories to navigate
- Shared data folder could become a bottleneck

### Alternatives Considered

1. **Monorepo with separate git submodules** - Adds complexity
2. **Separate repos per service** - Harder to coordinate during migration
3. **Flat structure** - Doesn't scale, unclear ownership

### Consequences

- Each service can be dockerized independently
- forex_core can be installed as editable package: `pip install -e forex_core`
- Shared data directory needs clear file naming conventions
- Documentation stays with code for easier maintenance

---

## ADR-005: Docker-First Deployment Strategy

**Date:** 2025-11-12
**Status:** ACCEPTED

### Context

Current deployment is manual with shell scripts. As we move to microservices, we need a consistent, reproducible deployment strategy.

### Decision

Adopt a **Docker-first** approach:
- Each service has its own Dockerfile
- Docker Compose for local development and testing
- Kubernetes-ready (future option)
- All dependencies containerized

### Rationale

**Pros:**
- Consistent environments (dev/staging/prod)
- Easy local development setup
- Isolated dependencies per service
- Portable across cloud providers
- Industry standard
- Built-in health checks
- Easy rollback

**Cons:**
- Docker learning curve
- Slightly slower local development (rebuilds)
- Resource overhead (multiple containers)

### Alternatives Considered

1. **Virtual environments only** - No isolation, deployment issues
2. **Ansible/Chef provisioning** - More complex, slower feedback
3. **Serverless (Lambda/Cloud Functions)** - Not suitable for long-running forecasts

### Consequences

- All developers need Docker installed
- CI/CD pipeline will build and push Docker images
- Need Docker registry (Docker Hub or private)
- Each service includes production-ready Dockerfile
- Health check endpoints required for all services

### Implementation

```dockerfile
# Example Dockerfile structure
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install forex_core
COPY forex_core/ /app/forex_core/
RUN pip install -e forex_core

# Copy service code
COPY services/data_collector/ .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "src/main.py"]
```

---

## ADR-006: Keep Existing Forecasting Models (ARIMA, ETS, Prophet)

**Date:** 2025-11-12
**Status:** ACCEPTED

### Context

The current system uses ARIMA, ETS, and Prophet for time series forecasting. During migration, we could keep these or explore newer models (LSTM, Transformers, etc.).

### Decision

**Keep existing models** (ARIMA, ETS, Prophet) during initial migration. Make architecture extensible for adding new models later.

### Rationale

**Pros:**
- Proven models that work for our data
- Reduces migration risk
- Faster migration timeline
- Team is familiar with these models
- Statistical models are interpretable
- Lower computational cost than deep learning

**Cons:**
- May not capture complex patterns
- No immediate performance improvement

### Alternatives Considered

1. **Migrate to LSTM/GRU** - Needs more data, harder to interpret
2. **Add ensemble of deep learning models** - Over-engineering
3. **Use AutoML (auto-sklearn, H2O)** - Black box, less control

### Consequences

- Forecasting engine will implement model interface
- Easy to add new models as plugins later
- Focus migration effort on architecture, not model experimentation
- Can run A/B tests with new models post-migration

### Future Work

- Add model registry for experiment tracking
- Implement A/B testing framework
- Evaluate transformer models (if data volume increases)

---

## ADR-007: Shared Data Storage via Volume Mounts (Phase 1)

**Date:** 2025-11-12
**Status:** ACCEPTED - TEMPORARY

### Context

Services need to share data (raw data, forecasts, generated reports). We need a solution for development and initial production.

### Decision

Use **shared volume mounts** for Phase 1:
- `shared/data/` directory mounted to all containers
- Simple file-based data exchange
- Clear file naming conventions

**Future:** Migrate to proper database (PostgreSQL) or object storage (S3) in Phase 2.

### Rationale

**Pros:**
- Simple to implement
- Works locally and in Docker Compose
- No additional infrastructure needed
- Good for migration phase

**Cons:**
- Not scalable to multiple servers
- No concurrent write safety
- File-based locking issues
- Not cloud-native

### Alternatives Considered

1. **PostgreSQL immediately** - Adds complexity during migration
2. **Redis for caching** - Not suitable for large datasets
3. **Object storage (S3/MinIO)** - Overkill for local dev

### Consequences

- Services must implement file locking
- Clear naming convention: `{service}_{data_type}_{timestamp}.{ext}`
- Migration to database planned for Phase 2
- Works for single-server deployment only

### Migration Path

Phase 2 will implement:
- PostgreSQL for structured data (config, metadata)
- MinIO/S3 for large files (datasets, PDFs)
- Redis for caching and job queues

---

## Future ADRs to Document

As migration progresses, document decisions on:

- [ ] Inter-service communication (REST vs gRPC vs message queue)
- [ ] Authentication/authorization strategy
- [ ] Logging and monitoring approach
- [ ] Error handling and retry policies
- [ ] Testing strategy (unit, integration, e2e)
- [ ] CI/CD pipeline implementation
- [ ] Database schema design
- [ ] API versioning strategy
- [ ] Rate limiting and throttling
- [ ] Backup and disaster recovery

---

**Document Maintenance:**
- Each ADR should be immutable once accepted
- New decisions get new ADR numbers
- Status can be: PROPOSED, ACCEPTED, DEPRECATED, SUPERSEDED
- Always include context, decision, rationale, alternatives, consequences
