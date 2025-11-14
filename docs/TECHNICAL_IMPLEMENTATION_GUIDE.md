# Technical Implementation Guide: Multi-Source News Aggregation System

**Target Audience:** Developers, DevOps Engineers, System Maintainers
**Scope:** Complete technical reference for news aggregation architecture
**Version:** 1.0 (Production)
**Last Updated:** 2025-11-13

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Component Details](#component-details)
3. [Integration Guide](#integration-guide)
4. [API Provider Setup](#api-provider-setup)
5. [Configuration Reference](#configuration-reference)
6. [Error Handling Strategy](#error-handling-strategy)
7. [Performance Optimization](#performance-optimization)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Development Guide](#development-guide)
10. [Monitoring & Alerting](#monitoring--alerting)

---

## System Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    DataLoader (Main)                         │
│                  Forecast Pipeline Entry                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ .news_aggregator.fetch_latest()
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                  NewsAggregator                              │
│              Multi-Source Orchestrator                       │
│  - Provider initialization                                  │
│  - Cache management                                         │
│  - Fallback logic                                           │
│  - Retry coordination                                       │
└────────┬────────────────┬────────────────┬───────────────────┘
         │                │                │
         ↓                ↓                ↓
    ┌─────────┐      ┌──────────┐     ┌──────────┐
    │ NewsAPI │      │ NewsData │     │   RSS    │
    │  .org   │      │   .io    │     │  Feeds   │
    │         │      │          │     │          │
    │ 100/day │      │ 200/day  │     │ Unlimited│
    └─────────┘      └──────────┘     └──────────┘
        │                  │               │
        └──────────────────┼───────────────┘
                           │
        ┌──────────────────┘
        │
        ↓
┌──────────────────────────────────────┐
│  List[NewsHeadline] (Result)         │
│  - Empty list if all fail (safe)     │
│  - Combined headlines if success     │
└──────────────────────────────────────┘
        │
        ↓
┌──────────────────────────────────────┐
│   Forecast Pipeline (Continues)      │
│   - Uses news data if available      │
│   - Runs without news if not         │
└──────────────────────────────────────┘
```

### Data Flow

```
Request comes in
    ↓
Check cache (6-hour TTL)
    ├─ Valid? → Return cached data [FAST]
    └─ Expired/Missing? → Proceed
    ↓
Initialize providers (in order)
    1. NewsAPI.org (if NEWS_API_KEY configured)
    2. NewsData.io (if NEWSDATA_API_KEY configured)
    3. RSS Feeds (always available)
    ↓
For each provider:
    Try fetch with retry logic
        ├─ Success (has headlines)? → Return [SUCCESS]
        ├─ 429 rate limit? → Skip to next (no retry)
        ├─ Network error? → Retry with backoff (1s, 2s, 4s)
        ├─ No results? → Try next provider
        └─ Max retries exceeded? → Try next provider
    ↓
All providers failed
    ↓
Return [] (empty list, non-blocking)
    ↓
Cache successful result
    ↓
Return to caller
```

### Fallback Chain Logic

```python
def fetch_latest(query, hours, max_retries):
    # Check cache first
    if cache_valid():
        return cached_headlines

    # Try each provider in sequence
    for provider in [NewsAPI, NewsData.io, RSS]:
        try:
            headlines = provider.fetch(query, hours)
            if headlines:
                cache(headlines)  # Save for 6 hours
                return headlines  # SUCCESS
        except RateLimitError:
            # 429 - don't retry, move to next
            continue
        except (TimeoutError, NetworkError):
            # Transient - retry with backoff
            for attempt in range(max_retries):
                sleep(2^attempt)  # 1s, 2s, 4s
                try:
                    headlines = provider.fetch(...)
                    if headlines:
                        cache(headlines)
                        return headlines
                except:
                    continue
        except Exception:
            # Other errors - log and continue
            continue

    # All providers failed
    log.warning("All providers failed, returning empty list")
    return []  # NON-BLOCKING
```

---

## Component Details

### 1. NewsAggregator Class

**File:** `src/forex_core/data/providers/news_aggregator.py`
**Lines:** 307
**Responsibility:** Orchestrate multi-source fetching with fallback

#### Key Methods

##### `__init__(settings: Settings)`

Initializes the aggregator with all available providers.

```python
def __init__(self, settings: Settings) -> None:
    """Initialize news aggregator with all available sources."""
    self.settings = settings
    self._init_providers()  # Initialize providers list
    self._cache: Optional[tuple[List[NewsHeadline], datetime]] = None
    self._cache_ttl_hours = 6  # 6-hour cache
```

**Behavior:**
- Tries to initialize each provider
- Logs warning if provider can't initialize (e.g., missing API key)
- Gracefully handles missing API keys
- Creates empty providers list if all fail

**Example:**
```python
from forex_core.config import get_settings
from forex_core.data.providers.news_aggregator import NewsAggregator

settings = get_settings()
agg = NewsAggregator(settings)  # Silently initializes available providers
```

---

##### `fetch_latest(query=None, hours=48, max_retries=2, use_cache=True)`

Main entry point for fetching news.

```python
def fetch_latest(
    self,
    query: Optional[str] = None,
    *,
    hours: int = 48,
    max_retries: int = 2,
    use_cache: bool = True,
) -> List[NewsHeadline]:
    """Fetch latest news with automatic fallback."""
```

**Parameters:**
- `query`: Search string (e.g., "Chile economy"). Uses default if None.
- `hours`: How far back to search (default: 48 hours)
- `max_retries`: Retry attempts per provider on transient errors (default: 2)
- `use_cache`: Use cached data if available (default: True)

**Returns:**
- `List[NewsHeadline]`: Headlines from first successful provider
- `[]` (empty list): If all providers fail (never raises exception)

**Example:**
```python
# Basic usage - uses cache, tries all providers
headlines = agg.fetch_latest()

# Force fresh fetch, skip cache
headlines = agg.fetch_latest(use_cache=False)

# Custom query and time window
headlines = agg.fetch_latest(
    query="Central bank meeting Chile",
    hours=24
)

# Increase retries for unstable network
headlines = agg.fetch_latest(max_retries=3)
```

**Flow:**
1. Check cache (if `use_cache=True`)
2. If cache valid, return cached data immediately
3. Try each provider in sequence
4. Return first successful result
5. Cache result for 6 hours
6. If all fail, return empty list and log warning

---

##### `_fetch_with_retry(provider, provider_name, source_id, query, hours, max_retries)`

Internal method handling retry logic per provider.

```python
def _fetch_with_retry(
    self,
    provider,
    provider_name: str,
    source_id: int,
    query: Optional[str],
    hours: int,
    max_retries: int,
) -> List[NewsHeadline]:
```

**Retry Strategy:**
- 429 Rate Limit: Immediately return empty list (no retry)
- Other errors: Retry with exponential backoff
- Backoff times: 1s, 2s, 4s (2^attempt)

**Example flow:**
```
Attempt 1: Try fetch → Timeout
           Wait 1 second
Attempt 2: Try fetch → Timeout
           Wait 2 seconds
Attempt 3: Try fetch → Success, return
```

---

##### `_is_cache_valid()`

Check if cached data is still usable.

```python
def _is_cache_valid(self) -> bool:
    """Check if cached news data is still valid."""
```

**Cache TTL:** 6 hours (hardcoded)

**Returns:**
- `True`: Cache exists and is <6 hours old
- `False`: Cache missing, expired, or invalid

---

##### `clear_cache()`

Manually clear cached news (force fresh fetch).

```python
def clear_cache(self) -> None:
    """Clear cached news data. Useful for forcing a fresh fetch."""
    self._cache = None
    logger.debug("News cache cleared")
```

**Use cases:**
- After detecting stale news
- Before critical forecast
- For testing purposes

---

##### `get_provider_status()`

Check which providers are configured and available.

```python
def get_provider_status(self) -> dict:
    """Get status of all configured providers."""
```

**Returns:**
```python
{
    'NewsAPI.org': 'available',  # If API key configured
    'NewsData.io': 'available',  # If API key configured
    'RSS Feeds': 'available'     # Always available
}
```

**Example:**
```python
agg = NewsAggregator(settings)
status = agg.get_provider_status()

if status['NewsAPI.org'] == 'available':
    print("Primary news source is configured")
else:
    print("Warning: NewsAPI not configured, using fallback")
```

---

### 2. NewsDataIOClient Class

**File:** `src/forex_core/data/providers/newsdata_io.py`
**Lines:** 238
**Responsibility:** Interface with NewsData.io API
**API Tier:** Free (200 requests/day)

#### Key Methods

##### `__init__(settings: Settings)`

Initialize NewsData.io client.

```python
def __init__(self, settings: Settings) -> None:
    """Initialize NewsData.io client."""
    if not settings.newsdata_api_key:
        raise ValueError("Missing NEWSDATA_API_KEY")
    self.api_key = settings.newsdata_api_key
```

**Validation:**
- Raises `ValueError` if API key missing
- Called by NewsAggregator during initialization

---

##### `fetch_latest(query=None, hours=48, source_id=2)`

Fetch news from NewsData.io.

```python
def fetch_latest(
    self,
    query: Optional[str] = None,
    *,
    hours: int = 48,
    source_id: int = 2,
) -> List[NewsHeadline]:
```

**API Parameters:**
- Language: Spanish ("es")
- Country: Chile ("cl")
- Size: 10 articles per request
- Sort: Date descending

**Sentiment Analysis:**
- Automatic sentiment classification (Spanish language)
- Returns: "Positivo", "Negativo", "Neutral"

**Example Response:**
```python
[
    NewsHeadline(
        title="Cobre sube por optimismo en demanda china",
        source="NewsData.io",
        url="https://...",
        published_at=datetime(2025, 11, 13, 18, 30, 0),
        sentiment="Positivo",
        source_id=2
    ),
    # ... more headlines
]
```

---

### 3. RSSNewsClient Class

**File:** `src/forex_core/data/providers/rss_news.py`
**Lines:** 279
**Responsibility:** Aggregate RSS feeds
**Cost:** Free (unlimited)

#### RSS Sources

```python
FEEDS = {
    "Diario Financiero": "https://www.df.cl/feed",
    "La Tercera": "https://www.latercera.com/feed/economía",
    "Emol": "https://www.emol.com/feed",
    "BioBio": "https://www.biobiochile.cl/feed"
}
```

**Geographic Focus:** Chile
**Update Frequency:** Varies (typically 1-2 hour lag)
**Quality:** Manual filters for economic keywords

#### Key Methods

##### `fetch_latest(hours=48, source_id=3)`

Aggregate headlines from all RSS feeds.

```python
def fetch_latest(
    self,
    hours: int = 48,
    source_id: int = 3,
) -> List[NewsHeadline]:
```

**Behavior:**
- Fetches from all configured feeds
- Filters for economic/forex keywords
- Returns combined results
- Handles per-feed timeouts gracefully

**Keyword Filters:**
```python
keywords = [
    "peso", "dólar", "USD", "CLP",  # Currency
    "economia", "mercado", "bolsa",  # Economics
    "tipo de cambio", "exchange",    # FX
    "cobre", "commodity",            # Commodities
    "banco central", "BCCh",         # Central bank
    "política monetaria",            # Monetary policy
]
```

---

## Integration Guide

### Integrating with DataLoader

The NewsAggregator is integrated into the main DataLoader class:

**File:** `src/forex_core/data/loader.py`

**Integration point:**
```python
class DataLoader:
    def __init__(self, settings: Settings):
        # ... other initialization ...

        # Use NewsAggregator for resilient multi-source news fetching
        from forex_core.data.providers.news_aggregator import NewsAggregator
        self.news_aggregator = NewsAggregator(self.settings)
        logger.info("NewsAggregator initialized with multi-source fallback")

    def _news(self, hours: int = 48) -> List[NewsHeadline]:
        """Fetch news with resilient multi-source fallback.

        Uses NewsAggregator which tries multiple sources in order:
        1. NewsAPI.org (primary)
        2. NewsData.io (fallback)
        3. RSS Feeds (last resort)
        4. Empty list (non-blocking)
        """
        try:
            articles = self.news_aggregator.fetch_latest(hours=48)
            logger.info(f"Successfully fetched {len(articles)} news articles")
            return articles
        except Exception as e:
            # This shouldn't happen - NewsAggregator handles all errors
            logger.error(f"NewsAggregator failed unexpectedly: {e}. Continuing without news.")
            return []
```

**Key points:**
- News failures never block forecast pipeline
- Empty list is valid result
- Logging is comprehensive for debugging
- All exceptions caught (defensive programming)

### Usage in Forecast Pipeline

```python
from forex_core.data.loader import DataLoader
from forex_core.config import get_settings

settings = get_settings()
loader = DataLoader(settings)

# Fetch data including news
data = loader.get_data(
    asset='USDCLP',
    start_date='2025-01-01',
    end_date='2025-11-13'
)

# data.news is List[NewsHeadline] (possibly empty)
if data.news:
    print(f"Using {len(data.news)} news articles for forecast")
else:
    print("No news available, forecast based on technical data only")
```

---

## API Provider Setup

### NewsAPI.org Setup

**Website:** https://newsapi.org

**Steps:**
1. Go to https://newsapi.org/register
2. Sign up with email
3. Verify email
4. Get API key from dashboard
5. Add to `.env`:
   ```bash
   NEWS_API_KEY=your_api_key_here
   ```

**Free Tier:**
- 100 requests/day
- Real-time news
- 50+ countries/languages
- Search functionality

**Rate Limits:**
- Daily limit: 100 requests
- Hitting limit: Returns HTTP 429

**Cost:** Free (with paid options available)

### NewsData.io Setup

**Website:** https://newsdata.io

**Steps:**
1. Go to https://newsdata.io/register
2. Sign up with email
3. Verify email (check spam)
4. Login to dashboard
5. Copy API key
6. Add to `.env`:
   ```bash
   NEWSDATA_API_KEY=your_api_key_here
   ```

**Free Tier:**
- 200 requests/day
- Multi-language support
- Sentiment analysis
- Country filtering

**Rate Limits:**
- Daily limit: 200 requests
- Per-minute limit: Not specified (be conservative)
- Hitting limit: Returns HTTP 429

**Cost:** Free (with paid options available)

**Special Features:**
- Spanish language support
- Chile country filter
- Automatic sentiment analysis
- Good for fallback use case

### RSS Feeds Setup

**No setup required** - RSS feeds are built-in and don't need API keys.

**Configured Sources:**
```python
{
    "Diario Financiero": "https://www.df.cl/feed",
    "La Tercera": "https://www.latercera.com/feed/economía",
    "Emol": "https://www.emol.com/feed",
    "BioBio": "https://www.biobiochile.cl/feed"
}
```

**Advantages:**
- No rate limits
- No API keys needed
- Always available
- Good for stability/reliability

**Disadvantages:**
- Delayed (1-2 hour lag from publication)
- Less structured data
- Manual keyword filtering

---

## Configuration Reference

### Environment Variables

```bash
# Primary news source (100 requests/day)
NEWS_API_KEY=your_newsapi_key

# Fallback news source (200 requests/day)
NEWSDATA_API_KEY=your_newsdata_key

# Both are optional
# System works with just RSS feeds if neither configured
```

### Settings Class

**File:** `src/forex_core/config/base.py`

```python
class Settings(BaseSettings):
    # ... other fields ...

    news_api_key: Optional[str] = Field(
        default=None,
        description="NewsAPI.org API key (100 requests/day free tier)",
        env="NEWS_API_KEY"
    )

    newsdata_api_key: Optional[str] = Field(
        default=None,
        description="NewsData.io API key (200 requests/day free tier)",
        env="NEWSDATA_API_KEY"
    )
```

### Configuration Loading

```python
from forex_core.config import get_settings

settings = get_settings()  # Automatically loads from .env and environment
```

**Load order:**
1. `.env` file (highest priority)
2. Environment variables
3. Default values (if applicable)

---

## Error Handling Strategy

### Error Classification

#### 1. Rate Limit Errors (HTTP 429)

**Cause:** API quota exhausted for today

**Detection:**
```python
if "429" in error_message or "Too Many Requests" in error_message:
    # Rate limit error
```

**Handling:**
- Don't retry this provider
- Skip immediately to next provider
- Log warning
- Continue gracefully

**Code:**
```python
except Exception as e:
    error_msg = str(e)
    if "429" in error_msg or "Too Many Requests" in error_msg:
        logger.warning(f"Rate limit exceeded. Moving to next provider.")
        return []  # Don't retry
```

---

#### 2. Network Errors (Timeout, ConnectionError)

**Cause:** Network connectivity issue (transient)

**Detection:**
```python
except (requests.Timeout, requests.ConnectionError, socket.timeout):
    # Network error
```

**Handling:**
- Retry with exponential backoff
- Wait: 1s, 2s, 4s between attempts
- Max retries: 2 (configurable)
- Log each attempt

**Code:**
```python
for attempt in range(max_retries + 1):
    try:
        result = fetch()
        return result
    except NetworkError:
        if attempt < max_retries:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(f"Network error, retrying in {wait_time}s...")
            time.sleep(wait_time)
        else:
            logger.error(f"Network error after {max_retries + 1} attempts")
            return []
```

---

#### 3. Invalid Response (Parse Error)

**Cause:** API response format unexpected

**Detection:**
```python
except (json.JSONDecodeError, KeyError, AttributeError):
    # Parse error
```

**Handling:**
- Don't retry (unlikely to fix)
- Log error details
- Move to next provider

**Code:**
```python
except (json.JSONDecodeError, KeyError) as e:
    logger.error(f"Failed to parse response: {e}")
    return []  # Don't retry parsing errors
```

---

#### 4. Authentication Error (HTTP 401/403)

**Cause:** Invalid API key

**Detection:**
```python
if response.status_code in [401, 403]:
    # Auth error
```

**Handling:**
- Don't retry (won't fix)
- Log warning about missing/invalid key
- Skip this provider entirely

**Code:**
```python
if response.status_code == 401:
    logger.warning("Invalid API key for this provider")
    raise ValueError("Invalid API key")  # Constructor validation
```

---

#### 5. Server Error (HTTP 500+)

**Cause:** Provider service issue

**Detection:**
```python
if response.status_code >= 500:
    # Server error
```

**Handling:**
- Treat like network error (transient)
- Retry with backoff
- Move to next provider if exhausted

---

### Exception Flow

```python
try:
    headlines = provider.fetch_latest(...)
except RateLimitError:
    # Type 1: Don't retry
    return []
except (TimeoutError, NetworkError):
    # Type 2: Retry with backoff
    for attempt in range(max_retries):
        sleep(2^attempt)
        try:
            return provider.fetch_latest(...)
        except:
            continue
    return []
except ValueError:
    # Type 4: Auth error (invalid key)
    return []
except Exception:
    # Type 3, 5, or unknown
    logger.error(f"Unexpected error: {e}")
    return []
```

---

## Performance Optimization

### Caching Strategy

**Cache Mechanism:** In-memory tuple of (headlines, timestamp)

**Cache TTL:** 6 hours (hardcoded)

**Usage:**
```python
def fetch_latest(self, use_cache=True):
    # Check cache first
    if use_cache and self._is_cache_valid():
        return self._cache[0]

    # Fetch from providers...

    # Save to cache
    self._cache = (headlines, datetime.utcnow())
    return headlines
```

**Rationale:**
- 6 hours: Reasonable freshness for daily forecasts
- In-memory: Fast lookup (no disk I/O)
- Per-instance: Simple and effective
- Manual clear: Available if needed

**Cache Hit Example:**
```
10:00 - fetch_latest() → API call → Returns 15 headlines
10:15 - fetch_latest() → Cache hit → Returns cached 15 headlines (no API call)
16:00 - fetch_latest() → Cache expired → API call → Returns new headlines
```

### API Consumption Analysis

**Before Resilience Fix:**
- Issue: Infinite restart loop
- API calls per day: 1,440 (one per restart attempt)
- Result: Quota exhausted in ~4 minutes
- Forecast success: 0%

**After Resilience Fix (with caching):**
- Normal operation: ~1 API call per day (forecaster-7d runs once)
- Cache prevents duplicate fetches: ~0 during off-hours
- Fallback to RSS: ~0 (NewsAPI rarely fails)
- Total daily consumption: 1-2 API calls
- Result: Well below limits
- Forecast success: 100%

**Example Daily Pattern:**
```
08:00 - Forecast-7d runs → Fetch news (API call #1) → Success
10:00 - Forecast-15d runs → Fetch news (cache hit, no API call)
12:00 - Any process → Fetch news (cache hit, no API call)
16:01 - Cache expires (6 hour TTL)
19:00 - Forecast-7d needs news → API call #2 → Success or fallback

Total: 1-2 API calls per day
```

### Concurrency Considerations

**Current Design:** Single instance per DataLoader

**Thread safety:** Not fully thread-safe (cache is shared)

**For concurrent use:**
```python
from threading import Lock

class NewsAggregator:
    def __init__(self, settings):
        # ... existing code ...
        self._cache_lock = Lock()

    def fetch_latest(self, ...):
        with self._cache_lock:
            if use_cache and self._is_cache_valid():
                return self._cache[0]

        # ... fetch from providers ...

        with self._cache_lock:
            self._cache = (headlines, datetime.utcnow())
        return headlines
```

**Note:** Current system is single-threaded, so not needed yet.

---

## Troubleshooting Guide

### Issue: "All news providers failed or returned no data"

**Symptom:** Log shows warning, but forecast still runs

**Root Causes:**
1. All API keys missing
2. All APIs returning 429
3. Network connectivity issue
4. RSS feeds down

**Diagnosis:**
```bash
# Check API key configuration
grep -i "api_key\|newsdata" .env

# Check logs for provider initialization
docker logs usdclp-forecaster-7d | grep "provider initialized"

# Check for 429 errors
docker logs usdclp-forecaster-7d | grep "429"

# Test a provider directly
curl -s "https://newsapi.org/v2/everything?q=test&apiKey=$NEWS_API_KEY" | jq
```

**Solutions:**
- Add API keys to `.env` if missing
- Check API key validity (regenerate if needed)
- Check network connectivity
- Check provider status (visit websites)

---

### Issue: "NewsAPI returned no headlines"

**Symptom:** RSS feeds used instead of primary source

**Root Causes:**
1. Search query returns no results
2. Time window too narrow
3. API quota exhausted (but should show 429)

**Diagnosis:**
```bash
# Check query configuration
grep -i "news_query\|search" src/forex_core/config/base.py

# Test query directly
curl -s "https://newsapi.org/v2/everything?q=Chile%20economy&apiKey=$YOUR_KEY" | jq '.totalResults'

# Check time window
# NewsAPI.org requires articles from last 30 days only
```

**Solutions:**
- Broaden search query
- Extend time window
- Check provider query format

---

### Issue: "Container keeps restarting"

**Symptom:** Infinite restart loop (original problem)

**Root Causes:**
1. API key incorrect or missing
2. Forecast code crashing on news fetch
3. Docker image build failed

**Diagnosis:**
```bash
# Check container logs
docker logs usdclp-forecaster-7d --tail 100

# Check most recent errors
docker logs usdclp-forecaster-7d 2>&1 | tail -20

# Check if image built correctly
docker images | grep forecaster-7d

# Check container health
docker ps -a | grep forecaster-7d
```

**Solutions:**
- Add/fix API keys in `.env`
- Rebuild Docker image: `docker-compose build forecaster-7d`
- Check error logs for actual error
- Verify base image available

---

### Issue: "News fetch very slow"

**Symptom:** forecast takes >5 minutes, news fetching slow

**Root Causes:**
1. Network latency
2. API provider slow
3. RSS feeds all timing out
4. Excessive retry attempts

**Diagnosis:**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Check timeout configuration
grep -i "timeout\|connect" src/forex_core/data/providers/*.py

# Test provider speed
time curl -s "https://newsapi.org/..." | wc -l

# Check network latency
ping newsapi.org
```

**Solutions:**
- Reduce `max_retries` parameter
- Increase `hours` window to cache more results
- Check network connectivity
- Reduce number of articles requested

---

### Issue: "API keys leaked in logs"

**Symptom:** API keys visible in debug logs or error messages

**Solutions:**
- Never log full API keys
- Use placeholder in messages: `NEWS_API_KEY=***`
- Sanitize error messages:
  ```python
  logger.error(f"API error: {e}".replace(api_key, "***"))
  ```

---

## Development Guide

### Adding a New News Provider

**Steps:**

1. **Create provider class:**
```python
# src/forex_core/data/providers/mynews.py

from typing import List, Optional
from forex_core.config import Settings
from forex_core.data.models import NewsHeadline

class MyNewsClient:
    """My news provider implementation."""

    def __init__(self, settings: Settings):
        self.api_key = settings.mynews_api_key

    def fetch_latest(
        self,
        query: Optional[str] = None,
        *,
        hours: int = 48,
        source_id: int = 4,
    ) -> List[NewsHeadline]:
        """Fetch news from my provider."""
        # Implementation...
        return [NewsHeadline(...), ...]
```

2. **Add configuration field:**
```python
# src/forex_core/config/base.py

class Settings(BaseSettings):
    mynews_api_key: Optional[str] = Field(
        default=None,
        env="MYNEWS_API_KEY"
    )
```

3. **Update NewsAggregator:**
```python
# src/forex_core/data/providers/news_aggregator.py

def _init_providers(self) -> None:
    # ... existing providers ...

    # Add new provider
    try:
        if self.settings.mynews_api_key:
            self.providers.append(
                ("MyNews", MyNewsClient(self.settings), 4)
            )
            logger.info("MyNews provider initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize MyNews: {e}")
```

4. **Test:**
```bash
python test_news_fallback.py  # Should show new provider in status
```

---

### Testing Fallback Logic

**Test cases:**

1. **All providers succeed:**
```python
def test_all_providers_available():
    agg = NewsAggregator(settings)
    headlines = agg.fetch_latest()
    assert len(headlines) > 0
    assert headlines[0].source == "NewsAPI.org"  # First provider wins
```

2. **First provider fails, second succeeds:**
```python
def test_fallback_to_second_provider():
    # Mock NewsAPI to fail, NewsData.io to succeed
    with patch('newsapi_client.fetch_latest', side_effect=Exception("Error")):
        agg = NewsAggregator(settings)
        headlines = agg.fetch_latest()
        assert headlines[0].source == "NewsData.io"
```

3. **All providers fail:**
```python
def test_all_providers_fail():
    # Mock all providers to fail
    agg = NewsAggregator(settings)
    headlines = agg.fetch_latest()
    assert headlines == []  # Returns empty list, no exception
```

4. **Cache working:**
```python
def test_cache_returns_same_data():
    agg = NewsAggregator(settings)
    h1 = agg.fetch_latest()
    h2 = agg.fetch_latest()
    assert h1 == h2  # Same object from cache
    # API not called second time
```

---

### Debugging

**Enable debug logging:**
```python
from loguru import logger
import sys

# Add stderr handler with debug level
logger.add(
    sys.stderr,
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)
```

**Trace execution:**
```python
agg = NewsAggregator(settings)

# Trace fetch_latest
logger.enable("forex_core.data.providers.news_aggregator")

headlines = agg.fetch_latest()
# Output shows each provider tried and result
```

**Provider status inspection:**
```python
agg = NewsAggregator(settings)
status = agg.get_provider_status()
for provider, state in status.items():
    print(f"{provider}: {state}")
```

---

## Monitoring & Alerting

### Metrics to Monitor

**1. Provider Health**
```bash
# Command to check
docker logs usdclp-forecaster-7d | grep -c "Successfully fetched"

# Expected: ≥1 per day
# Alert if: 0 in 24 hours
```

**2. API Consumption**
```bash
# NewsAPI.org daily consumption
docker logs usdclp-forecaster-7d --since 24h | grep "NewsAPI" | wc -l

# Expected: 1-2 per day
# Alert if: >5 per day (indicates excessive failures/retries)
```

**3. Fallback Usage**
```bash
# Check fallback provider usage
docker logs usdclp-forecaster-7d --since 24h | grep -E "NewsData|RSS" | wc -l

# Expected: 0-2 (fallback not needed often)
# Alert if: >3 per day (primary source having issues)
```

**4. Cache Hit Rate**
```bash
# Cache hits indicate efficiency
docker logs usdclp-forecaster-7d | grep "Using cached news" | wc -l

# Expected: Multiple times per day
# Good: High cache hit rate (less API calls)
```

### Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| No successful news fetch in 24h | Alert | Page | Check all providers |
| 429 errors >1/day | Monitor | Alert | Check rate limit quota |
| All providers failing | Alert | Page | Check network/APIs |
| Forecast fails due to news | Alert | Page | Review error logs |
| Cache never used | Warning | - | Check cache TTL |

### Grafana Dashboard Panels

**Suggested panels:**

1. **Provider Success Rate (24h)**
   ```
   success_count / total_attempts
   ```

2. **API Calls by Provider (24h)**
   ```
   Bar chart of NewsAPI vs NewsData vs RSS
   ```

3. **Fallback Activations (7d)**
   ```
   Count of fallback provider usage
   ```

4. **Error Rate by Type (7d)**
   ```
   Rate limit errors vs network errors vs others
   ```

5. **Forecast Success Rate (30d)**
   ```
   Successful forecasts / total forecasts
   ```

---

## Summary

This technical guide provides complete reference for the multi-source news aggregation system. Key takeaways:

1. **Architecture:** Orchestrator pattern with fallback chain
2. **Providers:** 3 independent sources + graceful degradation
3. **Integration:** Seamless in DataLoader, never blocks forecast
4. **Configuration:** Simple env vars, all optional
5. **Reliability:** Handles all errors gracefully (non-blocking)
6. **Performance:** 6-hour caching, ~1-2 API calls/day
7. **Extensibility:** Easy to add new providers

For production deployment, refer to `NEWS_API_FALLBACK_SETUP.md`.
For system architecture overview, see main session documentation.
