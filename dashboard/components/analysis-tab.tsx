'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ForecastData, PerformanceData } from '@/lib/api'
import { Download, BarChart3, TrendingUp, Target } from 'lucide-react'
import { DetailedForecastChart } from '@/components/detailed-forecast-chart'
import { PerformanceComparison } from '@/components/performance-comparison'
import { calculateConfidenceMetrics } from '@/lib/analytics'

interface AnalysisTabProps {
  forecasts: ForecastData[]
  performance: PerformanceData[]
  isLoading: boolean
}

type TimeRange = '1M' | '3M' | '6M' | '1Y'
type Horizon = '7D' | '15D' | '30D' | '90D' | 'ALL'

export function AnalysisTab({ forecasts, performance, isLoading }: AnalysisTabProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('3M')
  const [selectedHorizon, setSelectedHorizon] = useState<Horizon>('7D')
  const [showComparison, setShowComparison] = useState(false)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Cargando análisis...</p>
      </div>
    )
  }

  const selectedForecast = selectedHorizon === 'ALL'
    ? forecasts[0]
    : forecasts.find(f => f.horizon === selectedHorizon)

  const handleExportCSV = () => {
    const csvData = forecasts.map(f => ({
      Horizonte: f.horizon,
      'Tasa Actual': f.current_rate,
      'Tasa Predicha': f.predicted_rate,
      'Límite Superior': f.confidence_interval.upper,
      'Límite Inferior': f.confidence_interval.lower,
      Modelo: f.model_used,
      Fecha: f.prediction_date,
    }))

    const headers = Object.keys(csvData[0]).join(',')
    const rows = csvData.map(row => Object.values(row).join(','))
    const csv = [headers, ...rows].join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `usdclp-forecast-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  const handleExportPNG = () => {
    alert('Funcionalidad de exportación PNG - Por implementar con html2canvas')
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Análisis Detallado
              </CardTitle>
              <CardDescription>Gráficos interactivos y comparaciones de modelos</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleExportCSV}>
                <Download className="mr-2 h-4 w-4" />
                Exportar CSV
              </Button>
              <Button variant="outline" size="sm" onClick={handleExportPNG}>
                <Download className="mr-2 h-4 w-4" />
                Exportar PNG
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Horizon Selector */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Horizonte de Pronóstico</label>
            <div className="flex flex-wrap gap-2">
              {(['7D', '15D', '30D', '90D', 'ALL'] as Horizon[]).map((horizon) => (
                <Button
                  key={horizon}
                  variant={selectedHorizon === horizon ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedHorizon(horizon)}
                >
                  {horizon === 'ALL' ? 'Todos' : horizon}
                </Button>
              ))}
            </div>
          </div>

          {/* Time Range Selector */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Rango de Tiempo (Histórico)</label>
            <div className="flex flex-wrap gap-2">
              {(['1M', '3M', '6M', '1Y'] as TimeRange[]).map((range) => (
                <Button
                  key={range}
                  variant={timeRange === range ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTimeRange(range)}
                >
                  {range}
                </Button>
              ))}
            </div>
          </div>

          {/* Toggle Model Comparison */}
          <div className="flex items-center gap-2">
            <Button
              variant={showComparison ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowComparison(!showComparison)}
            >
              <TrendingUp className="mr-2 h-4 w-4" />
              {showComparison ? 'Ocultar' : 'Mostrar'} Comparación de Modelos
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Detailed Chart */}
      {selectedForecast && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>
                  Gráfico Interactivo - {selectedHorizon === 'ALL' ? 'Todos los Horizontes' : selectedHorizon}
                </CardTitle>
                <CardDescription>
                  Histórico de {timeRange} + Proyección con bandas de confianza
                </CardDescription>
              </div>
              <Badge variant="outline">
                Modelo: {selectedForecast.model_used}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <DetailedForecastChart
              forecast={selectedForecast}
              allForecasts={selectedHorizon === 'ALL' ? forecasts : undefined}
              timeRange={timeRange}
            />
          </CardContent>
        </Card>
      )}

      {/* Model Comparison */}
      {showComparison && (
        <PerformanceComparison performance={performance} forecasts={forecasts} />
      )}

      {/* Confidence Band Analysis */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Análisis de Intervalos de Confianza
          </CardTitle>
          <CardDescription>
            Ancho de las bandas de confianza por horizonte - Menor ancho indica mayor certeza
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {forecasts.map((forecast) => {
              const metrics = calculateConfidenceMetrics(forecast)

              // Calculate quality indicator
              const quality =
                metrics.band_width_pct < 2 ? 'success' :
                metrics.band_width_pct < 4 ? 'default' : 'warning'

              return (
                <div
                  key={forecast.horizon}
                  className="rounded-lg border p-4 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold">{forecast.horizon}</span>
                    <Badge variant={quality}>
                      {metrics.band_width_pct < 2 ? 'Excelente' :
                       metrics.band_width_pct < 4 ? 'Bueno' : 'Amplio'}
                    </Badge>
                  </div>

                  <div className="space-y-2">
                    <div>
                      <p className="text-xs text-muted-foreground">Ancho de Banda</p>
                      <p className="text-xl font-bold font-mono">
                        ${metrics.band_width.toFixed(2)}
                      </p>
                    </div>

                    <div className="flex justify-between items-center text-xs">
                      <span className="text-muted-foreground">Como % del precio</span>
                      <span className="font-semibold">{metrics.band_width_pct.toFixed(2)}%</span>
                    </div>

                    <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${
                          quality === 'success' ? 'bg-green-500' :
                          quality === 'default' ? 'bg-primary' : 'bg-yellow-500'
                        }`}
                        style={{ width: `${Math.min(metrics.band_width_pct * 25, 100)}%` }}
                      />
                    </div>

                    <div className="pt-1 border-t text-xs text-muted-foreground">
                      <div className="flex justify-between">
                        <span>Superior:</span>
                        <span className="font-mono">${forecast.confidence_interval.upper.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Inferior:</span>
                        <span className="font-mono">${forecast.confidence_interval.lower.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="mt-4 p-3 rounded-lg bg-muted/50 text-xs text-muted-foreground">
            <p className="font-semibold mb-1">Interpretación:</p>
            <ul className="space-y-1 list-disc list-inside">
              <li>Ancho menor indica mayor certeza del modelo en la predicción</li>
              <li>Horizontes más largos típicamente tienen bandas más amplias</li>
              <li>Un ancho {'<'} 2% se considera excelente, {'<'} 4% es bueno</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Data Table */}
      <Card>
        <CardHeader>
          <CardTitle>Tabla de Datos</CardTitle>
          <CardDescription>Detalles de todos los pronósticos</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="p-3 text-left font-semibold">Horizonte</th>
                  <th className="p-3 text-left font-semibold">Modelo</th>
                  <th className="p-3 text-right font-semibold">Tasa Actual</th>
                  <th className="p-3 text-right font-semibold">Predicción</th>
                  <th className="p-3 text-right font-semibold">Cambio %</th>
                  <th className="p-3 text-right font-semibold">Confianza 95%</th>
                </tr>
              </thead>
              <tbody>
                {forecasts.map((forecast) => {
                  const change = ((forecast.predicted_rate - forecast.current_rate) / forecast.current_rate) * 100
                  const isPositive = change > 0

                  return (
                    <tr key={forecast.horizon} className="border-b hover:bg-muted/50">
                      <td className="p-3">
                        <Badge variant="outline">{forecast.horizon}</Badge>
                      </td>
                      <td className="p-3 font-mono text-xs">{forecast.model_used}</td>
                      <td className="p-3 text-right font-mono">
                        ${forecast.current_rate.toFixed(2)}
                      </td>
                      <td className="p-3 text-right font-mono font-semibold">
                        ${forecast.predicted_rate.toFixed(2)}
                      </td>
                      <td className={`p-3 text-right font-semibold ${isPositive ? 'text-red-500' : 'text-green-500'}`}>
                        {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                      </td>
                      <td className="p-3 text-right font-mono text-xs">
                        ${forecast.confidence_interval.lower.toFixed(2)} - ${forecast.confidence_interval.upper.toFixed(2)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
