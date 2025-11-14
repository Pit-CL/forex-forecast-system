#!/usr/bin/env python
"""
Quick test script for multi-source news aggregator.

Tests the fallback chain without requiring actual API keys.
"""

import sys
sys.path.insert(0, 'src')

from forex_core.config import get_settings
from forex_core.data.providers.news_aggregator import NewsAggregator

def main():
    print("=" * 70)
    print("TESTING MULTI-SOURCE NEWS AGGREGATOR WITH FALLBACK")
    print("=" * 70)
    print()

    # Get settings
    settings = get_settings()

    # Check what API keys are configured
    print("📋 Configured API Keys:")
    print(f"  - NEWS_API_KEY: {'✓ Set' if settings.news_api_key else '✗ Not set'}")
    print(f"  - NEWSDATA_API_KEY: {'✓ Set' if settings.newsdata_api_key else '✗ Not set'}")
    print()

    # Initialize aggregator
    print("🔧 Initializing NewsAggregator...")
    aggregator = NewsAggregator(settings)
    print()

    # Check provider status
    print("📊 Provider Status:")
    status = aggregator.get_provider_status()
    for provider, state in status.items():
        icon = "✓" if state == "available" else "⚠"
        print(f"  {icon} {provider}: {state}")
    print()

    # Test fetching news
    print("📰 Fetching news with automatic fallback...")
    print("-" * 70)
    try:
        headlines = aggregator.fetch_latest(hours=48, use_cache=False)

        if headlines:
            print(f"\n✅ SUCCESS: Fetched {len(headlines)} headlines")
            print("\nSample headlines:")
            for i, headline in enumerate(headlines[:5], 1):
                print(f"\n{i}. [{headline.sentiment}] {headline.title}")
                print(f"   Source: {headline.source}")
                print(f"   Published: {headline.published_at}")
        else:
            print("\n⚠️  No headlines fetched (all sources failed or no API keys configured)")
            print("   This is OK - forecast will continue without news data")

        print("\n" + "=" * 70)
        print("✓ Test completed successfully")
        print("  The system is resilient and will not fail even when APIs are down.")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nThis should never happen! The aggregator should handle all errors gracefully.")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
