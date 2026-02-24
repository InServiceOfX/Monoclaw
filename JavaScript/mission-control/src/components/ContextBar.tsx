import { useMemo } from 'react'
import { useMissionStore } from '../store/useMissionStore'

interface ContextBarProps {
  /** Override context window (for standalone use). Defaults to active model's. */
  usedTokens?: number
  contextWindow?: number
}

export function ContextBar({ usedTokens, contextWindow }: ContextBarProps) {
  const { activeModel, sessionUsage } = useMissionStore()

  const window = contextWindow ?? activeModel.contextWindow
  const usage = sessionUsage[activeModel.id] ?? { inputTokens: 0, outputTokens: 0 }
  const used = usedTokens ?? usage.inputTokens + usage.outputTokens

  const pct = useMemo(() => Math.min((used / window) * 100, 100), [used, window])

  const barColor = pct < 50 ? '#3fb950' : pct < 80 ? '#d29922' : '#f85149'
  const textColor =
    pct < 50 ? 'text-accent-green' : pct < 80 ? 'text-accent-yellow' : 'text-accent-red'

  return (
    <div className="bg-surface-1 border border-border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-widest text-gray-400">
          Context Window
        </h2>
        <span className={`text-xs font-bold num ${textColor}`}>{pct.toFixed(1)}%</span>
      </div>

      <div className="w-full h-2.5 bg-surface-3 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: barColor }}
        />
      </div>

      <div className="flex justify-between text-xs text-gray-500 num">
        <span>{used.toLocaleString()} used</span>
        <span>{window.toLocaleString()} max</span>
      </div>

      {pct > 80 && (
        <p className="text-xs text-accent-red bg-accent-red/10 border border-accent-red/20 rounded px-2 py-1">
          ⚠ Context window {pct > 95 ? 'nearly full' : 'filling up'}
        </p>
      )}
    </div>
  )
}
