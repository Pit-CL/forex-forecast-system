'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ForecastData, PerformanceData } from '@/lib/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts'

interface PerformanceComparisonProps {
  performance: PerformanceData[]
  forecasts: ForecastData[]
}

export function PerformanceComparison({ performance, forecasts }: PerformanceComparisonProps) {
  // Prepare data for bar chart
  const barChartData = ['7D', '15D', '30D', '90D'].map((horizon) => {
    const perf = performance.find(p => p.model.includes(horizon))
    const forecast = forecasts.find(f => f.horizon === horizon)

    return {
      horizon,
      mape: perf?.mape || 0,
      mae: perf?.mae || 0,
      rmse: perf?.rmse || 0,
      accuracy: perf ? 100 - perf.mape : 0,
      model: forecast?.model_used || 'N/A',
    }
  })

  // Prepare data for radar chart
  const radarData = ['7D', '15D', '30D', '90D'].map((horizon) => {
    const perf = performance.find(p => p.model.includes(horizon))

    return {
      horizon,
      Precisión: perf ? 100 - perf.mape : 0,
      'Dir. Accuracy': perf?.directional_accuracy || 0,
      Estabilidad: perf ? 100 - (perf.rmse / 10) : 0,
    }
  })

  return (
    <div className="space-y-6">
      {/* Comparison Table */}
      <Card>
        <CardHeader>
          <CardTitle>Comparación de Modelos</CardTitle>
          <CardDescription>Métricas detalladas por horizonte</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="p-3 text-left font-semibold">Horizonte</th>
                  <th className="p-3 text-left font-semibold">Modelo</th>
                  <th className="p-3 text-right font-semibold">MAPE</th>
                  <th className="p-3 text-right font-semibold">MAE</th>
                  <th className="p-3 text-right font-semibold">RMSE</th>
                  <th className="p-3 text-right font-semibold">Dir. Accuracy</th>
                  <th className="p-3 text-right font-semibold">Precisión</th>
                </tr>
              </thead>
              <tbody>
                {barChartData.map((row) => (
                  <tr key={row.horizon} className="border-b hover:bg-muted/50">
                    <td className="p-3">
                      <Badge variant="outline">{row.horizon}</Badge>
                    </td>
                    <td className="p-3 font-mono text-xs">{row.model}</td>
                    <td className="p-3 text-right font-mono">{row.mape.toFixed(2)}%</td>
                    <td className="p-3 text-right font-mono">{row.mae.toFixed(2)}</td>
                    <td className="p-3 text-right font-mono">{row.rmse.toFixed(2)}</td>
                    <td className="p-3 text-right font-mono">
                      {performance.find(p => p.model.includes(row.horizon))?.directional_accuracy.toFixed(1)}%
                    </td>
                    <td className="p-3 text-right">
                      <Badge variant={row.accuracy > 95 ? 'success' : row.accuracy > 90 ? 'warning' : 'default'}>
                        {row.accuracy.toFixed(1)}%
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {/* MAPE Comparison */}
        <Card>
          <CardHeader>
            <CardTitle>MAPE por Horizonte</CardTitle>
            <CardDescription>Menor es mejor</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barChartData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="horizon" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                  <YAxis tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                    }}
                  />
                  <Legend />
                  <Bar dataKey="mape" fill="hsl(var(--chart-1))" name="MAPE (%)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Radar Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Radar de Rendimiento</CardTitle>
            <CardDescription>Comparación multidimensional</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid stroke="hsl(var(--border))" />
                  <PolarAngleAxis
                    dataKey="horizon"
                    tick={{ fill: 'hsl(var(--muted-foreground))' }}
                  />
                  <PolarRadiusAxis
                    angle={90}
                    domain={[0, 100]}
                    tick={{ fill: 'hsl(var(--muted-foreground))' }}
                  />
                  <Radar
                    name="Precisión"
                    dataKey="Precisión"
                    stroke="hsl(var(--chart-1))"
                    fill="hsl(var(--chart-1))"
                    fillOpacity={0.6}
                  />
                  <Radar
                    name="Dir. Accuracy"
                    dataKey="Dir. Accuracy"
                    stroke="hsl(var(--chart-2))"
                    fill="hsl(var(--chart-2))"
                    fillOpacity={0.6}
                  />
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Best Performers */}
      <Card>
        <CardHeader>
          <CardTitle>Mejores Modelos</CardTitle>
          <CardDescription>Top performers por métrica</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {/* Best MAPE */}
            <div className="space-y-2 rounded-lg border p-4">
              <p className="text-sm font-semibold text-muted-foreground">Mejor MAPE</p>
              {(() => {
                const best = performance.reduce((prev, curr) => (curr.mape < prev.mape ? curr : prev))
                return (
                  <>
                    <p className="text-2xl font-bold">{best.model}</p>
                    <Badge variant="success">{best.mape.toFixed(2)}% MAPE</Badge>
                  </>
                )
              })()}
            </div>

            {/* Best Directional Accuracy */}
            <div className="space-y-2 rounded-lg border p-4">
              <p className="text-sm font-semibold text-muted-foreground">Mejor Dir. Accuracy</p>
              {(() => {
                const best = performance.reduce((prev, curr) =>
                  curr.directional_accuracy > prev.directional_accuracy ? curr : prev
                )
                return (
                  <>
                    <p className="text-2xl font-bold">{best.model}</p>
                    <Badge variant="success">{best.directional_accuracy.toFixed(1)}%</Badge>
                  </>
                )
              })()}
            </div>

            {/* Most Stable */}
            <div className="space-y-2 rounded-lg border p-4">
              <p className="text-sm font-semibold text-muted-foreground">Más Estable (RMSE)</p>
              {(() => {
                const best = performance.reduce((prev, curr) => (curr.rmse < prev.rmse ? curr : prev))
                return (
                  <>
                    <p className="text-2xl font-bold">{best.model}</p>
                    <Badge variant="success">{best.rmse.toFixed(2)} RMSE</Badge>
                  </>
                )
              })()}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
