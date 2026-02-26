import { MODELS, PROVIDER_COLORS } from '../config/models'
import { useMissionStore } from '../store/useMissionStore'

export function ModelUsageBreakdown() {
  const { sessionUsage, activeModel } = useMissionStore()

  const rows = MODELS.map((model) => {
    const usage = sessionUsage[model.id] ?? { inputTokens: 0, outputTokens: 0 }
    const total = usage.inputTokens + usage.outputTokens
    return { model, input: usage.inputTokens, output: usage.outputTokens, total }
  }).sort((a, b) => b.total - a.total)

  const grandTotal = rows.reduce((sum, r) => sum + r.total, 0)

  return (
    <div className="bg-surface-1 border border-border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-widest text-gray-400">Model Usage Mix</h2>
        <span className="text-xs text-gray-500">{grandTotal.toLocaleString()} total tokens</span>
      </div>

      <div className="space-y-2 max-h-64 overflow-auto pr-1">
        {rows.map(({ model, input, output, total }) => {
          const pct = grandTotal > 0 ? (total / grandTotal) * 100 : 0
          const color = PROVIDER_COLORS[model.provider] ?? '#58a6ff'
          const isActive = model.id === activeModel.id

          return (
            <div key={model.id} className={`bg-surface-2 border rounded-lg p-2 ${isActive ? 'border-accent-blue/60' : 'border-border/60'}`}>
              <div className="flex items-center justify-between gap-2 mb-1">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                  <p className="text-xs text-gray-200 truncate">{model.name}</p>
                </div>
                <span className="text-xs num text-gray-400">{pct.toFixed(1)}%</span>
              </div>

              <div className="w-full h-1.5 bg-surface-3 rounded-full overflow-hidden mb-1">
                <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
              </div>

              <div className="flex items-center justify-between text-[11px] text-gray-500 num">
                <span>in {input.toLocaleString()} / out {output.toLocaleString()}</span>
                <span>{total.toLocaleString()}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
