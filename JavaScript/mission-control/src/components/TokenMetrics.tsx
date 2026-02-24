import { useRef, useEffect, useState } from 'react'
import { useMissionStore } from '../store/useMissionStore'

function AnimatedNum({ value }: { value: number }) {
  const [flash, setFlash] = useState(false)
  const prev = useRef(value)

  useEffect(() => {
    if (value !== prev.current) {
      prev.current = value
      setFlash(true)
      const t = setTimeout(() => setFlash(false), 400)
      return () => clearTimeout(t)
    }
  }, [value])

  return (
    <span className={`num font-bold text-lg text-gray-100 ${flash ? 'token-flash' : ''}`}>
      {value.toLocaleString()}
    </span>
  )
}

function MetricCard({
  label,
  value,
  sub,
}: {
  label: string
  value: number
  sub?: string
}) {
  return (
    <div className="bg-surface-2 border border-border/60 rounded-lg p-3 space-y-1">
      <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
      <AnimatedNum value={value} />
      {sub && <p className="text-xs text-gray-600 num">{sub}</p>}
    </div>
  )
}

export function TokenMetrics() {
  const { activeModel, sessionUsage, resetSession } = useMissionStore()
  const usage = sessionUsage[activeModel.id] ?? { inputTokens: 0, outputTokens: 0 }

  const total = usage.inputTokens + usage.outputTokens

  const cost =
    (usage.inputTokens / 1000) * activeModel.costPer1kInput +
    (usage.outputTokens / 1000) * activeModel.costPer1kOutput

  return (
    <div className="bg-surface-1 border border-border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-widest text-gray-400">
          Session Tokens
        </h2>
        <button
          onClick={resetSession}
          className="text-xs text-gray-500 hover:text-gray-300 border border-border/60 rounded px-2 py-0.5 hover:border-border transition-colors"
        >
          Reset
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <MetricCard label="Input" value={usage.inputTokens} />
        <MetricCard label="Output" value={usage.outputTokens} />
        <MetricCard
          label="Total"
          value={total}
          sub={`${((total / activeModel.contextWindow) * 100).toFixed(1)}% of ctx`}
        />
        <div className="bg-surface-2 border border-border/60 rounded-lg p-3 space-y-1">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Est. Cost</p>
          <span className="num font-bold text-lg text-gray-100">
            {cost > 0 ? `$${cost.toFixed(4)}` : <span className="text-accent-green">Free</span>}
          </span>
        </div>
      </div>
    </div>
  )
}
