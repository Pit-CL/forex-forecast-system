'use client'

import { ForecastData } from '@/lib/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, ComposedChart } from 'recharts'
import { formatCurrency } from '@/lib/utils'

interface DetailedForecastChartProps {
  forecast: ForecastData
  allForecasts?: ForecastData[]
  timeRange: '1M' | '3M' | '6M' | '1Y'
}

export function DetailedForecastChart({ forecast, allForecasts, timeRange }: DetailedForecastChartProps) {
  const daysMap = {
    '1M': 30,
    '3M': 90,
    '6M': 180,
    '1Y': 365,
  }

  const historicalDays = daysMap[timeRange]
  const today = new Date()
  const data = []

  // Generate historical data
  for (let i = historicalDays; i >= 1; i--) {
    const date = new Date(today)
    date.setDate(date.getDate() - i)
    data.push({
      date: date.toLocaleDateString('es-CL', { month: 'short', day: 'numeric' }),
      actual: forecast.current_rate + (Math.random() - 0.5) * 40 * (i / historicalDays),
      type: 'historical',
    })
  }

  // Current point
  data.push({
    date: today.toLocaleDateString('es-CL', { month: 'short', day: 'numeric' }),
    actual: forecast.current_rate,
    type: 'current',
  })

  // If showing all forecasts
  if (allForecasts && allForecasts.length > 0) {
    // Add forecast lines for each horizon
    const maxHorizon = Math.max(...allForecasts.map(f => parseInt(f.horizon.replace('D', ''))))

    for (let i = 1; i <= maxHorizon; i++) {
      const date = new Date(today)
      date.setDate(date.getDate() + i)
      const point: any = {
        date: date.toLocaleDateString('es-CL', { month: 'short', day: 'numeric' }),
        type: 'forecast',
      }

      allForecasts.forEach(f => {
        const horizonDays = parseInt(f.horizon.replace('D', ''))
        if (i <= horizonDays) {
          const progress = i / horizonDays
          point[`forecast_${f.horizon}`] = f.current_rate + (f.predicted_rate - f.current_rate) * progress
        }
      })

      data.push(point)
    }
  } else {
    // Single forecast
    const horizonDays = parseInt(forecast.horizon.replace('D', ''))

    for (let i = 1; i <= horizonDays; i++) {
      const date = new Date(today)
      date.setDate(date.getDate() + i)
      const progress = i / horizonDays
      data.push({
        date: date.toLocaleDateString('es-CL', { month: 'short', day: 'numeric' }),
        predicted: forecast.current_rate + (forecast.predicted_rate - forecast.current_rate) * progress,
        upper: forecast.current_rate + (forecast.confidence_interval.upper - forecast.current_rate) * progress,
        lower: forecast.current_rate + (forecast.confidence_interval.lower - forecast.current_rate) * progress,
        type: 'forecast',
      })
    }
  }

  const colors = {
    '7D': '#3b82f6',
    '15D': '#10b981',
    '30D': '#f59e0b',
    '90D': '#ef4444',
  }

  // Calculate Y-axis domain with padding for better visualization
  const allValues = data.flatMap(d => {
    const values: number[] = []
    if (d.actual) values.push(d.actual)
    if (d.predicted) values.push(d.predicted)
    if (d.upper) values.push(d.upper)
    if (d.lower) values.push(d.lower)
    // Add all forecast lines if showing multiple horizons
    Object.keys(d).forEach(key => {
      if (key.startsWith('forecast_') && typeof d[key] === 'number') {
        values.push(d[key])
      }
    })
    return values
  })
  const minValue = Math.min(...allValues)
  const maxValue = Math.max(...allValues)
  const padding = (maxValue - minValue) * 0.15 // 15% padding for better visibility
  const yMin = Math.floor(minValue - padding)
  const yMax = Math.ceil(maxValue + padding)

  return (
    <div className="h-[400px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 10, right: 30, left: 20, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="date"
            angle={-45}
            textAnchor="end"
            height={80}
            className="text-xs"
            tick={{ fill: 'hsl(var(--muted-foreground))' }}
          />
          <YAxis
            className="text-xs"
            tick={{ fill: 'hsl(var(--muted-foreground))' }}
            tickFormatter={(value) => `$${value.toFixed(0)}`}
            domain={[yMin, yMax]}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
            }}
            formatter={(value: number) => formatCurrency(value)}
          />
          <Legend />

          {/* Confidence bands for single forecast */}
          {!allForecasts && (
            <>
              <defs>
                <linearGradient id="confidenceBandAnalysis" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.2} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="upper"
                stroke="hsl(var(--primary))"
                strokeWidth={1.5}
                strokeOpacity={0.5}
                strokeDasharray="3 3"
                fill="url(#confidenceBandAnalysis)"
                fillOpacity={0.3}
                name="Límite Superior"
              />
              <Area
                type="monotone"
                dataKey="lower"
                stroke="hsl(var(--primary))"
                strokeWidth={1.5}
                strokeOpacity={0.5}
                strokeDasharray="3 3"
                fill="hsl(var(--background))"
                fillOpacity={1}
                name="Límite Inferior"
              />
            </>
          )}

          {/* Actual line */}
          <Line
            type="monotone"
            dataKey="actual"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={false}
            name="Histórico"
          />

          {/* Forecast lines */}
          {allForecasts ? (
            allForecasts.map((f) => (
              <Line
                key={f.horizon}
                type="monotone"
                dataKey={`forecast_${f.horizon}`}
                stroke={colors[f.horizon as keyof typeof colors]}
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                name={`Pronóstico ${f.horizon}`}
              />
            ))
          ) : (
            <Line
              type="monotone"
              dataKey="predicted"
              stroke="hsl(var(--chart-1))"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="Pronóstico"
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
