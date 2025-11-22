'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatCurrency, formatPercentage, formatDate } from '@/lib/utils'
import { ForecastData, PerformanceData, MarketData, getHistoricalData } from '@/lib/api'
import { TrendingUp, TrendingDown, Activity, BarChart3, Target, Gauge } from 'lucide-react'
import { ForecastChart } from '@/components/forecast-chart'
import { MarketIndicators } from '@/components/market-indicators'
import { calculateModelDivergence, analyzeTrend, extractHistoricalRates } from '@/lib/analytics'
import { useState, useEffect } from 'react'

interface OverviewTabProps {
  forecasts: ForecastData[]
  performance: PerformanceData[]
  marketData: MarketData | undefined
  isLoading: boolean
}

export function OverviewTab({ forecasts, performance, marketData, isLoading }: OverviewTabProps) {
  const [historicalRates, setHistoricalRates] = useState<number[]>([])
  const [isLoadingHistorical, setIsLoadingHistorical] = useState(true)

  // Load historical data on mount
  useEffect(() => {
    async function loadHistoricalData() {
      try {
        const data = await getHistoricalData(30)
        const rates = extractHistoricalRates(data.data)
        setHistoricalRates(rates)
      } catch (error) {
        console.error('Error loading historical data:', error)
        setHistoricalRates([])
      } finally {
        setIsLoadingHistorical(false)
      }
    }

    loadHistoricalData()
  }, [])

  if (isLoading || isLoadingHistorical) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Activity className="mx-auto h-8 w-8 animate-pulse text-muted-foreground" />
          <p className="mt-4 text-sm text-muted-foreground">Cargando datos...</p>
        </div>
      </div>
    )
  }

  const forecast7D = forecasts.find(f => f.horizon === '7D')
  const forecast15D = forecasts.find(f => f.horizon === '15D')
  const forecast30D = forecasts.find(f => f.horizon === '30D')
  const forecast90D = forecasts.find(f => f.horizon === '90D')

  const performance7D = performance.find(p => p.model.includes('7D'))

  if (!forecast7D) {
    return <div className="text-center py-12">No hay datos disponibles</div>
  }

  const changePercent = ((forecast7D.predicted_rate - forecast7D.current_rate) / forecast7D.current_rate) * 100
  const isPositive = changePercent > 0

  // Calculate analytics metrics
  const divergence = calculateModelDivergence(forecasts)
  const trend = analyzeTrend(historicalRates)

  return (
    <div className="space-y-6">
      {/* Main Forecast Card - 7 Days */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl">Pronóstico Principal - 7 Días</CardTitle>
              <CardDescription>Predicción más confiable a corto plazo</CardDescription>
            </div>
            <div className="flex flex-col gap-2">
              {performance7D && (
                <Badge variant="success" className="text-sm">
                  ✓ {(100 - performance7D.mape).toFixed(1)}% Precisión
                </Badge>
              )}
              <div className="flex gap-2">
                <Badge
                  variant={
                    divergence.consensus === 'fuerte'
                      ? 'success'
                      : divergence.consensus === 'moderado'
                      ? 'default'
                      : 'warning'
                  }
                  className="text-xs"
                >
                  <Target className="h-3 w-3 mr-1" />
                  Consenso: {divergence.consensus.toUpperCase()}
                </Badge>
                <Badge
                  variant={
                    divergence.direction === 'alcista'
                      ? 'warning'
                      : divergence.direction === 'bajista'
                      ? 'success'
                      : 'default'
                  }
                  className="text-xs"
                >
                  {divergence.direction === 'alcista' ? (
                    <TrendingUp className="h-3 w-3 mr-1" />
                  ) : divergence.direction === 'bajista' ? (
                    <TrendingDown className="h-3 w-3 mr-1" />
                  ) : (
                    <Activity className="h-3 w-3 mr-1" />
                  )}
                  {divergence.direction.charAt(0).toUpperCase() + divergence.direction.slice(1)}
                </Badge>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Current & Predicted Rates */}
            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Tasa Actual</p>
                <p className="text-3xl font-bold font-mono">
                  {formatCurrency(forecast7D.current_rate)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Predicción 7 Días</p>
                <div className="flex items-center gap-2">
                  <p className="text-3xl font-bold font-mono">
                    {formatCurrency(forecast7D.predicted_rate)}
                  </p>
                  <div className={`flex items-center gap-1 ${isPositive ? 'text-red-500' : 'text-green-500'}`}>
                    {isPositive ? (
                      <TrendingUp className="h-6 w-6" />
                    ) : (
                      <TrendingDown className="h-6 w-6" />
                    )}
                    <span className="text-xl font-semibold">
                      {formatPercentage(changePercent)}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Confidence Interval */}
            <div className="flex flex-col justify-center space-y-2 rounded-lg bg-muted p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Intervalo de Confianza</span>
                <Badge variant="outline">{forecast7D.confidence_interval.confidence_level}%</Badge>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-sm">Límite Superior:</span>
                  <span className="font-mono font-semibold">
                    {formatCurrency(forecast7D.confidence_interval.upper)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Predicción:</span>
                  <span className="font-mono font-semibold">
                    {formatCurrency(forecast7D.predicted_rate)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Límite Inferior:</span>
                  <span className="font-mono font-semibold">
                    {formatCurrency(forecast7D.confidence_interval.lower)}
                  </span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground pt-2">
                Modelo: {forecast7D.model_used} | Fecha: {formatDate(forecast7D.prediction_date)}
              </p>
            </div>
          </div>

          {/* Forecast Chart */}
          <ForecastChart forecast={forecast7D} />
        </CardContent>
      </Card>

      {/* Additional Horizons */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Horizontes Adicionales
          </CardTitle>
          <CardDescription>Pronósticos a mediano y largo plazo</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {[forecast15D, forecast30D, forecast90D].map((forecast) => {
              if (!forecast) return null

              const change = ((forecast.predicted_rate - forecast.current_rate) / forecast.current_rate) * 100
              const isUp = change > 0
              const perf = performance.find(p => p.model.includes(forecast.horizon))

              return (
                <div
                  key={forecast.horizon}
                  className="flex flex-col gap-2 rounded-lg border p-4 hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold">{forecast.horizon}</span>
                    {perf && (
                      <Badge variant="outline" className="text-xs">
                        MAPE: {perf.mape.toFixed(2)}%
                      </Badge>
                    )}
                  </div>
                  <div className="space-y-1">
                    <p className="text-2xl font-bold font-mono">
                      {formatCurrency(forecast.predicted_rate)}
                    </p>
                    <div className={`flex items-center gap-1 text-sm ${isUp ? 'text-red-500' : 'text-green-500'}`}>
                      {isUp ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                      <span className="font-semibold">{formatPercentage(change)}</span>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Confianza: {formatCurrency(forecast.confidence_interval.lower)} - {formatCurrency(forecast.confidence_interval.upper)}
                  </p>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Trend Analysis */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Gauge className="h-5 w-5" />
            Análisis de Tendencia
          </CardTitle>
          <CardDescription>Dirección y fuerza del mercado basado en datos históricos</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {/* Short-term trend */}
            <div className="rounded-lg border p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">Tendencia 7 días</span>
                <Badge
                  variant={
                    trend.short_term === 'alcista'
                      ? 'warning'
                      : trend.short_term === 'bajista'
                      ? 'success'
                      : 'default'
                  }
                >
                  {trend.short_term === 'alcista' ? (
                    <TrendingUp className="h-3 w-3 mr-1" />
                  ) : trend.short_term === 'bajista' ? (
                    <TrendingDown className="h-3 w-3 mr-1" />
                  ) : (
                    <Activity className="h-3 w-3 mr-1" />
                  )}
                  {trend.short_term.charAt(0).toUpperCase() + trend.short_term.slice(1)}
                </Badge>
              </div>
              <p className="text-2xl font-bold">{formatPercentage(trend.change_7d)}</p>
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Fuerza</span>
                  <span>{trend.strength}%</span>
                </div>
                <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${
                      trend.short_term === 'alcista'
                        ? 'bg-yellow-500'
                        : trend.short_term === 'bajista'
                        ? 'bg-green-500'
                        : 'bg-muted-foreground'
                    }`}
                    style={{ width: `${trend.strength}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Medium-term trend */}
            <div className="rounded-lg border p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">Tendencia 30 días</span>
                <Badge
                  variant={
                    trend.medium_term === 'alcista'
                      ? 'warning'
                      : trend.medium_term === 'bajista'
                      ? 'success'
                      : 'default'
                  }
                >
                  {trend.medium_term === 'alcista' ? (
                    <TrendingUp className="h-3 w-3 mr-1" />
                  ) : trend.medium_term === 'bajista' ? (
                    <TrendingDown className="h-3 w-3 mr-1" />
                  ) : (
                    <Activity className="h-3 w-3 mr-1" />
                  )}
                  {trend.medium_term.charAt(0).toUpperCase() + trend.medium_term.slice(1)}
                </Badge>
              </div>
              <p className="text-2xl font-bold">{formatPercentage(trend.change_30d)}</p>
              <p className="text-xs text-muted-foreground">
                Cambio en últimos 30 días
              </p>
            </div>

            {/* Model consensus */}
            <div className="rounded-lg border p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">Consenso de Modelos</span>
                <Badge
                  variant={
                    divergence.consensus === 'fuerte'
                      ? 'success'
                      : divergence.consensus === 'moderado'
                      ? 'default'
                      : 'warning'
                  }
                >
                  {divergence.consensus.toUpperCase()}
                </Badge>
              </div>
              <p className="text-2xl font-bold">
                {divergence.direction_agreement.toFixed(0)}%
              </p>
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Acuerdo en dirección</span>
                  <span>Divergencia: ${divergence.max_difference.toFixed(2)}</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Los modelos {divergence.consensus === 'fuerte' ? 'están muy alineados' : divergence.consensus === 'moderado' ? 'tienen diferencias moderadas' : 'muestran alta divergencia'}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Market Indicators */}
      <MarketIndicators marketData={marketData} />

      {/* Model Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Precisión del Modelo</CardTitle>
          <CardDescription>Métricas de rendimiento por horizonte</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {['7D', '15D', '30D', '90D'].map((horizon) => {
              const perf = performance.find(p => p.model.includes(horizon))
              if (!perf) return null

              const accuracy = 100 - perf.mape
              const barWidth = `${accuracy}%`

              return (
                <div key={horizon} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-semibold">{horizon}</span>
                    <div className="flex items-center gap-4">
                      <span className="text-muted-foreground">
                        MAPE: {perf.mape.toFixed(2)}%
                      </span>
                      <span className="font-semibold text-green-500">
                        {accuracy.toFixed(1)}% Precisión
                      </span>
                    </div>
                  </div>
                  <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500 transition-all duration-500"
                      style={{ width: barWidth }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
