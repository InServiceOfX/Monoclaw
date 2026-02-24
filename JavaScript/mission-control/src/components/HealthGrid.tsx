import { useEffect, useCallback } from 'react'
import { MODELS, PROVIDER_COLORS } from '../config/models'
import { useMissionStore } from '../store/useMissionStore'
import type { HealthStatus } from '../store/useMissionStore'
import { healthCheck } from '../api/modelClient'

const STATUS_CONFIG: Record<HealthStatus, { dot: string; label: string; glow: string }> = {
  unknown:     { dot: 'bg-gray-600',         label: '—',          glow: '' },
  checking:    { dot: 'bg-accent-yellow animate-pulse', label: 'Checking', glow: '' },
  healthy:     { dot: 'bg-accent-green',      label: 'Healthy',   glow: 'shadow-confirmed' },
  degraded:    { dot: 'bg-accent-yellow',     label: 'Degraded',  glow: '' },
  unreachable: { dot: 'bg-accent-red',        label: 'Unreachable', glow: 'shadow-error' },
}

function fmtTime(d: Date | null): string {
  if (!d) return '—'
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function HealthGrid() {
  const { healthMap, setHealth, autoRefresh, setAutoRefresh } = useMissionStore()

  const runChecks = useCallback(async () => {
    for (const model of MODELS) {
      setHealth(model.id, 'checking', null)
      const result = await healthCheck(model)
      const status: HealthStatus = result.reachable
        ? result.latencyMs !== null && result.latencyMs > 4000
          ? 'degraded'
          : 'healthy'
        : 'unreachable'
      setHealth(model.id, status, result.latencyMs)
    }
  }, [setHealth])

  // Run on mount
  useEffect(() => {
    runChecks()
  }, [runChecks])

  // Auto-refresh every 30s
  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(runChecks, 30000)
    return () => clearInterval(id)
  }, [autoRefresh, runChecks])

  return (
    <div className="bg-surface-1 border border-border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-widest text-gray-400">
          Endpoint Health
        </h2>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="accent-accent-green"
            />
            Auto (30s)
          </label>
          <button
            onClick={runChecks}
            className="text-xs text-accent-blue hover:text-accent-blue/80 border border-accent-blue/30 rounded px-2 py-0.5 hover:border-accent-blue/60 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="space-y-2">
        {MODELS.map((model) => {
          const health = healthMap[model.id]
          const cfg = STATUS_CONFIG[health?.status ?? 'unknown']
          const providerColor = PROVIDER_COLORS[model.provider] ?? '#58a6ff'

          return (
            <div
              key={model.id}
              className="flex items-center gap-3 py-2 px-3 bg-surface-2 border border-border/40 rounded-lg"
            >
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: providerColor }}
              />

              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-200 truncate">{model.name}</p>
                <p className="text-xs text-gray-600 truncate">{model.provider}</p>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                {health?.latencyMs !== null && health?.latencyMs !== undefined && (
                  <span className="text-xs text-gray-500 num">{health.latencyMs} ms</span>
                )}
                <span className="text-xs text-gray-500 hidden sm:block">
                  {fmtTime(health?.lastChecked ?? null)}
                </span>
                <div className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${cfg.dot} ${cfg.glow}`} />
                  <span
                    className={`text-xs font-medium ${
                      health?.status === 'healthy'
                        ? 'text-accent-green'
                        : health?.status === 'unreachable'
                        ? 'text-accent-red'
                        : health?.status === 'degraded'
                        ? 'text-accent-yellow'
                        : 'text-gray-500'
                    }`}
                  >
                    {cfg.label}
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
