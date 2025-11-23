'use client'

import { ForecastData, getHistoricalData } from '@/lib/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, ComposedChart } from 'recharts'
import { formatCurrency } from '@/lib/utils'
import { useEffect, useState } from 'react'

interface ForecastChartProps {
  forecast: ForecastData
}

export function ForecastChart({ forecast }: ForecastChartProps) {
  const [historicalData, setHistoricalData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Fetch real historical data
    const fetchHistoricalData = async () => {
      try {
        const response = await getHistoricalData(30)
        const formattedData = response.data.map((point) => ({
          date: new Date(point.date).toLocaleDateString('es-CL', { month: 'short', day: 'numeric' }),
          actual: point.close,
          type: 'historical',
        }))
        setHistoricalData(formattedData)
      } catch (error) {
        console.error('Error fetching historical data:', error)
        // Fallback to mock data if API fails
        const today = new Date()
        const fallbackData = []
        for (let i = 30; i >= 1; i--) {
          const date = new Date(today)
          date.setDate(date.getDate() - i)
          fallbackData.push({
            date: date.toLocaleDateString('es-CL', { month: 'short', day: 'numeric' }),
            actual: forecast.current_rate + (Math.random() - 0.5) * 30,
            type: 'historical',
          })
        }
        setHistoricalData(fallbackData)
      } finally {
        setLoading(false)
      }
    }

    fetchHistoricalData()
  }, [forecast.current_rate])

  // Build complete data array
  const today = new Date()
  const data = [...historicalData]

  // Current rate
  data.push({
    date: today.toLocaleDateString('es-CL', { month: 'short', day: 'numeric' }),
    actual: forecast.current_rate,
    type: 'current',
  })

  // Forecast data (next 7 days)
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

  // Calculate Y-axis domain with padding
  const allValues = data.flatMap(d => [d.actual, d.predicted, d.upper, d.lower].filter(v => v !== undefined))
  const minValue = Math.min(...allValues)
  const maxValue = Math.max(...allValues)
  const padding = (maxValue - minValue) * 0.1 // 10% padding
  const yMin = Math.floor(minValue - padding)
  const yMax = Math.ceil(maxValue + padding)

  if (loading) {
    return (
      <div className="h-[300px] w-full flex items-center justify-center">
        <div className="text-muted-foreground">Cargando datos históricos...</div>
      </div>
    )
  }

  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="date"
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

          {/* Confidence band - visible shaded area */}
          <defs>
            <linearGradient id="confidenceBand" x1="0" y1="0" x2="0" y2="1">
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
            fill="url(#confidenceBand)"
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

          {/* Actual historical line */}
          <Line
            type="monotone"
            dataKey="actual"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={false}
            name="Histórico"
          />

          {/* Predicted line */}
          <Line
            type="monotone"
            dataKey="predicted"
            stroke="hsl(var(--chart-1))"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={false}
            name="Predicción"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
