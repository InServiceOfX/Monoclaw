import { ModelSelector } from './components/ModelSelector'
import { ModelStatus } from './components/ModelStatus'
import { TokenMetrics } from './components/TokenMetrics'
import { ContextBar } from './components/ContextBar'
import { HealthGrid } from './components/HealthGrid'

export default function App() {
  return (
    <div className="min-h-screen bg-surface text-gray-200 font-mono">
      {/* Header */}
      <header className="border-b border-border bg-surface-1 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
          <span className="text-sm font-bold tracking-widest uppercase text-gray-300">
            Mission Control
          </span>
        </div>
        <span className="text-xs text-gray-600">LLM Dashboard</span>
      </header>

      {/* Main layout */}
      <main className="max-w-6xl mx-auto px-4 py-6 grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        {/* Column 1 */}
        <div className="space-y-4 lg:col-span-1">
          <ModelSelector />
          <ModelStatus />
        </div>

        {/* Column 2 */}
        <div className="space-y-4 lg:col-span-1">
          <TokenMetrics />
          <ContextBar />
        </div>

        {/* Column 3 — full height health grid */}
        <div className="md:col-span-2 lg:col-span-1">
          <HealthGrid />
        </div>
      </main>
    </div>
  )
}
