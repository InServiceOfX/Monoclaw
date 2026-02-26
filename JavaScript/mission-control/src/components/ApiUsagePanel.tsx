import { useMemo } from 'react'
import { useMissionStore } from '../store/useMissionStore'

function Stat({ label, value, tone = 'text-gray-100' }: { label: string; value: string; tone?: string }) {
  return (
    <div className="bg-surface-2 border border-border/60 rounded-lg p-3">
      <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
      <p className={`text-lg num font-bold ${tone}`}>{value}</p>
    </div>
  )
}

export function ApiUsagePanel() {
  const { apiMetrics } = useMissionStore()

  const successRate = useMemo(() => {
    if (apiMetrics.totalCalls === 0) return 100
    return ((apiMetrics.successCalls / apiMetrics.totalCalls) * 100)
  }, [apiMetrics])

  return (
    <div className="bg-surface-1 border border-border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-widest text-gray-400">API Usage</h2>
        <span className="text-xs text-gray-500">live session</span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Stat label="Total Calls" value={apiMetrics.totalCalls.toLocaleString()} />
        <Stat label="Success" value={apiMetrics.successCalls.toLocaleString()} tone="text-accent-green" />
        <Stat label="Failures" value={apiMetrics.failedCalls.toLocaleString()} tone={apiMetrics.failedCalls > 0 ? 'text-accent-red' : 'text-gray-100'} />
        <Stat label="Success Rate" value={`${successRate.toFixed(1)}%`} tone={successRate > 95 ? 'text-accent-green' : successRate > 80 ? 'text-accent-yellow' : 'text-accent-red'} />
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500 border-t border-border/40 pt-2">
        <span>Handshake tests: {apiMetrics.handshakeCalls}</span>
        <span>Health probes: {apiMetrics.healthChecks}</span>
      </div>
    </div>
  )
}
