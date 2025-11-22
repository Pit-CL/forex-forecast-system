"""
News service for handling market news and sentiment
"""
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import httpx

from models.schemas import NewsArticle, NewsResponse
from utils.config import settings


class NewsService:
    """Service for managing news data"""

    def __init__(self):
        self.api_key = settings.news_api_key
        self.development_mode = settings.development_mode

    def _generate_mock_news(self, count: int = 10) -> List[NewsArticle]:
        """Generate mock news articles for development"""
        news_templates = [
            {
                "title": "Fed mantiene tasas de interés sin cambios",
                "summary": "La Reserva Federal decidió mantener las tasas en el rango actual, impactando el par USD/CLP",
                "source": "Reuters",
                "sentiment": "neutral",
                "tags": ["Fed", "Tasas", "USD"]
            },
            {
                "title": "Precio del cobre alcanza nuevos máximos",
                "summary": "El metal rojo sube 3% en la jornada, fortaleciendo el peso chileno",
                "source": "Bloomberg",
                "sentiment": "positive",
                "tags": ["Cobre", "Commodities", "CLP"]
            },
            {
                "title": "Banco Central de Chile interviene en mercado cambiario",
                "summary": "El BCCh anuncia medidas para contener la volatilidad del tipo de cambio",
                "source": "El Mercurio",
                "sentiment": "negative",
                "tags": ["BCCh", "Intervención", "Volatilidad"]
            },
            {
                "title": "Inflación en Chile supera expectativas",
                "summary": "IPC mensual llega a 0.8%, presionando al peso chileno",
                "source": "La Tercera",
                "sentiment": "negative",
                "tags": ["Inflación", "IPC", "CLP"]
            },
            {
                "title": "Exportaciones chilenas crecen 5% en el trimestre",
                "summary": "Aumento en exportaciones mineras impulsa balanza comercial",
                "source": "Diario Financiero",
                "sentiment": "positive",
                "tags": ["Exportaciones", "Comercio", "Minería"]
            },
            {
                "title": "Dólar se fortalece globalmente ante datos económicos",
                "summary": "Índice DXY sube 0.5% tras publicación de datos de empleo en EEUU",
                "source": "Financial Times",
                "sentiment": "negative",
                "tags": ["DXY", "USD", "Empleo"]
            },
            {
                "title": "China aumenta demanda de cobre chileno",
                "summary": "Recuperación económica china impulsa importaciones de commodities",
                "source": "WSJ",
                "sentiment": "positive",
                "tags": ["China", "Cobre", "Demanda"]
            },
            {
                "title": "Analistas proyectan estabilidad para USD/CLP",
                "summary": "Consenso de mercado espera rango entre 940-960 para próximas semanas",
                "source": "JP Morgan",
                "sentiment": "neutral",
                "tags": ["Proyecciones", "Análisis", "USD/CLP"]
            },
            {
                "title": "Tensiones geopolíticas impactan mercados emergentes",
                "summary": "Incertidumbre global presiona monedas latinoamericanas",
                "source": "CNN Business",
                "sentiment": "negative",
                "tags": ["Geopolítica", "Emergentes", "Riesgo"]
            },
            {
                "title": "Inversión extranjera en Chile aumenta 12%",
                "summary": "Flujos de capital fortalecen el peso chileno en el corto plazo",
                "source": "InvestChile",
                "sentiment": "positive",
                "tags": ["IED", "Inversión", "Capital"]
            }
        ]

        articles = []
        used_indices = set()

        for i in range(min(count, len(news_templates))):
            # Select a random template not yet used
            idx = random.randint(0, len(news_templates) - 1)
            while idx in used_indices and len(used_indices) < len(news_templates):
                idx = random.randint(0, len(news_templates) - 1)
            used_indices.add(idx)

            template = news_templates[idx]

            # Generate random timestamp within last 24 hours
            hours_ago = random.randint(0, 24)
            published_at = datetime.now() - timedelta(hours=hours_ago)

            articles.append(NewsArticle(
                id=str(uuid.uuid4()),
                title=template["title"],
                summary=template["summary"],
                source=template["source"],
                url=f"https://example.com/news/{uuid.uuid4()}",
                published_at=published_at,
                relevance_score=round(random.uniform(0.6, 1.0), 2),
                sentiment=template["sentiment"],
                tags=template["tags"]
            ))

        # Sort by published date (most recent first)
        articles.sort(key=lambda x: x.published_at, reverse=True)

        return articles

    async def fetch_news_from_api(self) -> Optional[List[NewsArticle]]:
        """Fetch real news from external API if configured"""
        if not self.api_key or self.development_mode:
            return None

        # Example implementation for a news API
        # This would need to be adapted based on the actual API being used
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.example.com/news",
                    params={
                        "keywords": "USD CLP Chile forex",
                        "language": "es",
                        "sortBy": "relevance"
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    # Parse API response into NewsArticle objects
                    # Implementation depends on actual API response structure
                    return []

        except Exception as e:
            print(f"Error fetching news: {e}")

        return None

    async def get_news(self, limit: int = 10, sentiment_filter: Optional[str] = None) -> NewsResponse:
        """Get news articles with optional filtering"""
        # Try to fetch real news first
        articles = await self.fetch_news_from_api()

        # Use mock data if real news not available
        if articles is None:
            articles = self._generate_mock_news(limit * 2)  # Generate extra for filtering

        # Apply sentiment filter if specified
        if sentiment_filter:
            articles = [a for a in articles if a.sentiment == sentiment_filter]

        # Limit the results
        articles = articles[:limit]

        return NewsResponse(
            timestamp=datetime.now(),
            count=len(articles),
            articles=articles
        )

    async def get_news_sentiment_summary(self) -> Dict:
        """Get sentiment analysis summary of recent news"""
        news_response = await self.get_news(limit=50)

        total = len(news_response.articles)
        if total == 0:
            return {
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "overall": "neutral",
                "score": 0
            }

        positive = sum(1 for a in news_response.articles if a.sentiment == "positive")
        negative = sum(1 for a in news_response.articles if a.sentiment == "negative")
        neutral = sum(1 for a in news_response.articles if a.sentiment == "neutral")

        # Calculate sentiment score (-1 to 1)
        score = (positive - negative) / total

        # Determine overall sentiment
        if score > 0.2:
            overall = "positive"
        elif score < -0.2:
            overall = "negative"
        else:
            overall = "neutral"

        return {
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "positive_pct": round((positive / total) * 100, 1),
            "negative_pct": round((negative / total) * 100, 1),
            "neutral_pct": round((neutral / total) * 100, 1),
            "overall": overall,
            "score": round(score, 3),
            "total_articles": total
        }