import { ForecastData, HistoricalDataPoint } from './api'

export interface ModelDivergence {
  max_difference: number
  max_difference_pct: number
  consensus: 'fuerte' | 'moderado' | 'débil'
  direction: 'alcista' | 'bajista' | 'lateral'
  direction_agreement: number // % de modelos que coinciden en dirección
}

export interface ConfidenceMetrics {
  band_width: number
  band_width_pct: number
  historical_avg?: number
  vs_historical?: string
}

export interface TrendAnalysis {
  short_term: 'alcista' | 'bajista' | 'lateral'
  medium_term: 'alcista' | 'bajista' | 'lateral'
  strength: number // 0-100
  change_7d: number
  change_30d: number
}

/**
 * Calculate divergence between different forecast models
 */
export function calculateModelDivergence(forecasts: ForecastData[]): ModelDivergence {
  if (forecasts.length < 2) {
    return {
      max_difference: 0,
      max_difference_pct: 0,
      consensus: 'fuerte',
      direction: 'lateral',
      direction_agreement: 100,
    }
  }

  const predictions = forecasts.map(f => f.predicted_rate)
  const minPrediction = Math.min(...predictions)
  const maxPrediction = Math.max(...predictions)
  const maxDifference = maxPrediction - minPrediction
  const avgPrediction = predictions.reduce((a, b) => a + b, 0) / predictions.length
  const maxDifferencePct = (maxDifference / avgPrediction) * 100

  // Determine consensus strength based on divergence
  let consensus: 'fuerte' | 'moderado' | 'débil'
  if (maxDifferencePct < 0.5) {
    consensus = 'fuerte'
  } else if (maxDifferencePct < 1.5) {
    consensus = 'moderado'
  } else {
    consensus = 'débil'
  }

  // Calculate direction agreement
  const currentRate = forecasts[0].current_rate
  const directions = forecasts.map(f => {
    const change = ((f.predicted_rate - currentRate) / currentRate) * 100
    if (change > 0.1) return 'alcista'
    if (change < -0.1) return 'bajista'
    return 'lateral'
  })

  const directionCounts = {
    alcista: directions.filter(d => d === 'alcista').length,
    bajista: directions.filter(d => d === 'bajista').length,
    lateral: directions.filter(d => d === 'lateral').length,
  }

  const maxCount = Math.max(directionCounts.alcista, directionCounts.bajista, directionCounts.lateral)
  const direction = Object.keys(directionCounts).find(
    key => directionCounts[key as keyof typeof directionCounts] === maxCount
  ) as 'alcista' | 'bajista' | 'lateral'

  const directionAgreement = (maxCount / forecasts.length) * 100

  return {
    max_difference: maxDifference,
    max_difference_pct: maxDifferencePct,
    consensus,
    direction,
    direction_agreement: directionAgreement,
  }
}

/**
 * Calculate confidence band width metrics
 */
export function calculateConfidenceMetrics(forecast: ForecastData): ConfidenceMetrics {
  const bandWidth = forecast.confidence_interval.upper - forecast.confidence_interval.lower
  const bandWidthPct = (bandWidth / forecast.predicted_rate) * 100

  return {
    band_width: bandWidth,
    band_width_pct: bandWidthPct,
  }
}

/**
 * Analyze trend from historical data
 */
export function analyzeTrend(historicalRates: number[]): TrendAnalysis {
  if (historicalRates.length < 7) {
    return {
      short_term: 'lateral',
      medium_term: 'lateral',
      strength: 0,
      change_7d: 0,
      change_30d: 0,
    }
  }

  // Calculate 7-day trend
  const last7Days = historicalRates.slice(-7)
  const first7Day = last7Days[0]
  const last7Day = last7Days[last7Days.length - 1]
  const change7d = ((last7Day - first7Day) / first7Day) * 100

  // Calculate 30-day trend if available
  let change30d = 0
  if (historicalRates.length >= 30) {
    const first30Day = historicalRates[historicalRates.length - 30]
    const last30Day = historicalRates[historicalRates.length - 1]
    change30d = ((last30Day - first30Day) / first30Day) * 100
  }

  // Determine short-term trend
  let shortTerm: 'alcista' | 'bajista' | 'lateral'
  if (change7d > 0.3) {
    shortTerm = 'alcista'
  } else if (change7d < -0.3) {
    shortTerm = 'bajista'
  } else {
    shortTerm = 'lateral'
  }

  // Determine medium-term trend
  let mediumTerm: 'alcista' | 'bajista' | 'lateral'
  if (change30d > 0.5) {
    mediumTerm = 'alcista'
  } else if (change30d < -0.5) {
    mediumTerm = 'bajista'
  } else {
    mediumTerm = 'lateral'
  }

  // Calculate trend strength (0-100)
  const strength = Math.min(Math.abs(change7d) * 20, 100)

  return {
    short_term: shortTerm,
    medium_term: mediumTerm,
    strength: Math.round(strength),
    change_7d: change7d,
    change_30d: change30d,
  }
}

/**
 * Extract closing rates from historical data response
 */
export function extractHistoricalRates(historicalData: any[]): number[] {
  return historicalData.map(point => point.close)
}
