"""
News router for API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from models import NewsResponse
from services.news_service import NewsService

router = APIRouter(prefix="/api/news", tags=["news"])
news_service = NewsService()


@router.get("", response_model=NewsResponse)
async def get_news(
    limit: int = Query(default=10, ge=1, le=100, description="Number of articles to return"),
    sentiment: Optional[str] = Query(default=None, description="Filter by sentiment: positive, negative, neutral")
):
    """
    Get latest news articles related to USD/CLP

    Parameters:
    - limit: Number of articles to return (1-100)
    - sentiment: Optional sentiment filter
    """
    if sentiment and sentiment not in ["positive", "negative", "neutral"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sentiment filter: {sentiment}. Must be: positive, negative, or neutral"
        )

    try:
        news = await news_service.get_news(limit=limit, sentiment_filter=sentiment)
        return news
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment")
async def get_sentiment_analysis():
    """
    Get sentiment analysis summary of recent news

    Returns aggregated sentiment metrics and overall market sentiment
    """
    try:
        sentiment_summary = await news_service.get_news_sentiment_summary()
        return sentiment_summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending")
async def get_trending_topics():
    """
    Get trending topics and tags from recent news
    """
    try:
        news = await news_service.get_news(limit=50)

        # Count tag frequencies
        tag_counts = {}
        for article in news.articles:
            for tag in article.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Sort by frequency
        trending = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "timestamp": news.timestamp,
            "trending_topics": [
                {"tag": tag, "count": count, "percentage": round((count / len(news.articles)) * 100, 1)}
                for tag, count in trending[:10]
            ],
            "total_articles": len(news.articles)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))