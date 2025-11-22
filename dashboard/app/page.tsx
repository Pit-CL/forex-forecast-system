'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ThemeToggle } from '@/components/theme-toggle'
import { getAllForecasts, getPerformance, getLatestMarketData } from '@/lib/api'
import { OverviewTab } from '@/components/overview-tab'
import { AnalysisTab } from '@/components/analysis-tab'

export default function DashboardPage() {
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const { data: forecasts, isLoading: loadingForecasts } = useQuery({
    queryKey: ['forecasts'],
    queryFn: async () => {
      const data = await getAllForecasts()
      setLastUpdate(new Date())
      return data
    },
    refetchInterval: 300000, // Refresh every 5 minutes
  })

  const { data: performance, isLoading: loadingPerformance } = useQuery({
    queryKey: ['performance'],
    queryFn: getPerformance,
    refetchInterval: 300000, // Refetch every 5 minutes
    staleTime: 240000,       // Consider stale after 4 minutes
  })

  const { data: marketData, isLoading: loadingMarketData } = useQuery({
    queryKey: ['market-data'],
    queryFn: getLatestMarketData,
    refetchInterval: 300000, // Refresh every 5 minutes
  })


  const isLoading = loadingForecasts || loadingPerformance || loadingMarketData

  // Get current rate from market data (includes live USD/CLP via yfinance)
  const forecast7D = forecasts?.find(f => f.horizon === '7D')
  const currentRate = marketData?.usdclp || forecast7D?.current_rate || 0

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">USD/CLP Forecast</h1>
            {!isLoading && (
              <div className="ml-4 flex items-center gap-2 rounded-lg bg-muted px-3 py-1.5 md:px-4 md:py-2">
                <div className="flex flex-col">
                  <span className="text-xs text-muted-foreground">USD/CLP</span>
                  <span className="text-lg md:text-xl font-bold font-mono">
                    ${currentRate.toFixed(2)}
                  </span>
                  <span className="text-xs text-muted-foreground mt-0.5">
                    {Math.floor((Date.now() - lastUpdate.getTime()) / 60000) === 0 ? "<1" : Math.floor((Date.now() - lastUpdate.getTime()) / 60000)}m
                  </span>
                </div>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 md:gap-4">
            <div className="hidden md:flex items-center gap-2 text-xs text-muted-foreground">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              <span>Auto-refresh</span>
            </div>
            <span className="relative flex h-2 w-2 md:hidden">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container px-4 py-6">
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="analysis">Análisis</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <OverviewTab
              forecasts={forecasts || []}
              performance={performance || []}
              marketData={marketData}
              isLoading={isLoading}
            />
          </TabsContent>

          <TabsContent value="analysis" className="space-y-6">
            <AnalysisTab
              forecasts={forecasts || []}
              performance={performance || []}
              isLoading={isLoading}
            />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
