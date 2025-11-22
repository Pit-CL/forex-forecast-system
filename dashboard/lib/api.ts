const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface ForecastData {
  horizon: string
  model_used: string
  current_rate: number
  predicted_rate: number
  prediction_date: string
  confidence_interval: {
    lower: number
    upper: number
    confidence_level: number
  }
  metadata: {
    features_used?: number
    prediction_timestamp: string
    model_version: string
    accuracy_score?: number
    mape?: number
  }
}

export interface PerformanceData {
  model: string
  mae: number
  rmse: number
  mape: number
  directional_accuracy: number
}

export interface MarketData {
  date: string
  usdclp: number | null
  copper: number | null
  copper_change: number
  oil: number | null
  oil_change: number
  dxy: number | null
  dxy_change: number
  sp500: number | null
  sp500_change: number
  vix: number | null
  vix_change: number
  rate_differential: number | null
}

export interface HistoricalDataPoint {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface HistoricalDataResponse {
  symbol: string
  period: string
  data: HistoricalDataPoint[]
  statistics?: {
    mean: number
    std: number
    min: number
    max: number
  }
}

// API Response interfaces from the actual backend
interface APIForecastResponse {
  timestamp: string
  current_price: number
  forecasts: {
    [key: string]: {
      horizon: string
      horizon_days: number
      current_price: number
      forecast_price: number
      price_change: number
      price_change_pct: number
      confidence_level: number
      forecast_date: string
      data: Array<{
        date: string
        value: number
        lower_bound: number
        upper_bound: number
      }>
      metadata: {
        model: string
        last_updated: string
        accuracy_score: number
        mape: number
      }
    }
  }
}

export async function getAllForecasts(): Promise<ForecastData[]> {
  const response = await fetch(`${API_URL}/api/forecasts`)

  if (!response.ok) {
    throw new Error('Failed to fetch forecasts')
  }

  const data: APIForecastResponse = await response.json()

  // Transform API response to dashboard format
  return Object.entries(data.forecasts).map(([_, forecast]) => {
    const lastDataPoint = forecast.data[forecast.data.length - 1]

    return {
      horizon: forecast.horizon.toUpperCase(),
      model_used: forecast.metadata.model,
      current_rate: forecast.current_price,
      predicted_rate: forecast.forecast_price,
      prediction_date: forecast.forecast_date,
      confidence_interval: {
        lower: lastDataPoint.lower_bound,
        upper: lastDataPoint.upper_bound,
        confidence_level: forecast.confidence_level * 100,
      },
      metadata: {
        prediction_timestamp: forecast.metadata.last_updated,
        model_version: '1.0',
        accuracy_score: forecast.metadata.accuracy_score,
        mape: forecast.metadata.mape,
      },
    }
  })
}


export async function getPerformance(): Promise<PerformanceData[]> {
  try {
    const response = await fetch(`${API_URL}/api/performance`)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: Failed to fetch performance metrics`)
    }
    
    const data = await response.json()
    
    // API returns correct structure, just return it directly
    // No need to calculate anything - all metrics are REAL from backend
    return data.map((item: any) => ({
      model: item.model,
      mae: item.mae,
      rmse: item.rmse,
      mape: item.mape,
      directional_accuracy: item.directional_accuracy,
    }))
  } catch (error) {
    console.error('❌ Error fetching performance metrics:', error)
    // Fallback to empty array (let UI show loading/error state)
    return []
  }
}

export async function getLatestMarketData(): Promise<MarketData> {
  try {
    const response = await fetch(`${API_URL}/api/market-indicators/live`)

    if (!response.ok) {
      throw new Error('Failed to fetch market indicators')
    }

    const data = await response.json()
    const indicators = data.indicators

    return {
      date: data.timestamp || new Date().toISOString(),
      usdclp: indicators.usdclp?.value || null,
      copper: indicators.copper?.value || null,
      copper_change: indicators.copper?.change_percent || 0,
      oil: indicators.oil?.value || null,
      oil_change: indicators.oil?.change_percent || 0,
      dxy: indicators.dxy?.value || null,
      dxy_change: indicators.dxy?.change_percent || 0,
      sp500: indicators.sp500?.value || null,
      sp500_change: indicators.sp500?.change_percent || 0,
      vix: indicators.vix?.value || null,
      vix_change: indicators.vix?.change_percent || 0,
      rate_differential: indicators.rate_differential?.value || null,
    }
  } catch (error) {
    console.error('Error fetching market indicators:', error)
    // Fallback to mock data
    return {
      date: new Date().toISOString(),
      usdclp: 946.63,
      copper: 4.25,
      copper_change: 0,
      oil: 82.50,
      oil_change: 0,
      dxy: 103.45,
      dxy_change: 0,
      sp500: 4567.89,
      sp500_change: 0,
      vix: 15.23,
      vix_change: 0,
      rate_differential: null,
    }
  }
}

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_URL}/api/health`)

  if (!response.ok) {
    throw new Error('API health check failed')
  }

  return response.json()
}

export async function getHistoricalData(days: number = 365): Promise<HistoricalDataResponse> {
  const response = await fetch(`${API_URL}/api/historical?days=${days}`)

  if (!response.ok) {
    throw new Error('Failed to fetch historical data')
  }

  return response.json()
}
