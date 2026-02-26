import { useState } from 'react'
import { ModelSelector } from './components/ModelSelector'
import { ModelStatus } from './components/ModelStatus'
import { TokenMetrics } from './components/TokenMetrics'
import { ContextBar } from './components/ContextBar'
import { HealthGrid } from './components/HealthGrid'
import { ApiUsagePanel } from './components/ApiUsagePanel'
import { ModelUsageBreakdown } from './components/ModelUsageBreakdown'
import { MemoryScreen } from './components/MemoryScreen'

type ViewMode = 'operations' | 'memory'

export default function App() {
  const [view, setView] = useState<ViewMode>('operations')

  return (
    <div className="min-h-screen bg-surface text-gray-200 font-mono">
      <header className="border-b border-border bg-gradient-to-r from-surface-1 via-surface to-surface-1 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-2.5 h-2.5 rounded-full bg-accent-green animate-pulse" />
              <div className="absolute inset-0 rounded-full bg-accent-green/40 blur-sm" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-gray-500">Mission Control</p>
              <p className="text-sm font-bold text-gray-100">LLM Ops + Memory Intelligence</p>
            </div>
          </div>

          <div className="flex items-center gap-2 bg-surface-2 border border-border rounded-lg p-1">
            <button
              onClick={() => setView('operations')}
              className={`px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider transition-colors ${
                view === 'operations'
                  ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/40'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              Operations
            </button>
            <button
              onClick={() => setView('memory')}
              className={`px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider transition-colors ${
                view === 'memory'
                  ? 'bg-accent-purple/20 text-accent-purple border border-accent-purple/40'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              Memory
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {view === 'operations' ? (
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 xl:grid-cols-4">
            <div className="space-y-4 xl:col-span-1">
              <ModelSelector />
              <ModelStatus />
            </div>

            <div className="space-y-4 xl:col-span-1">
              <TokenMetrics />
              <ContextBar />
              <ApiUsagePanel />
            </div>

            <div className="space-y-4 md:col-span-2 xl:col-span-2">
              <HealthGrid />
              <ModelUsageBreakdown />
            </div>
          </div>
        ) : (
          <MemoryScreen />
        )}
      </main>
    </div>
  )
}
