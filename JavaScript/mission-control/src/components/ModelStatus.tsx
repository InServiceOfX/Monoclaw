import { useMissionStore } from '../store/useMissionStore'
import { PROVIDER_COLORS } from '../config/models'

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border/40 last:border-0">
      <span className="text-xs text-gray-500 uppercase tracking-wider">{label}</span>
      <span className="text-xs text-gray-200 num font-medium">{value}</span>
    </div>
  )
}

function fmtNum(n: number): string {
  return n.toLocaleString()
}

export function ModelStatus() {
  const { activeModel, lastLatencyMs, switchState } = useMissionStore()
  const providerColor = PROVIDER_COLORS[activeModel.provider] ?? '#58a6ff'

  return (
    <div className="bg-surface-1 border border-border rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span
          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
          style={{ backgroundColor: providerColor }}
        />
        <h2 className="text-xs font-bold uppercase tracking-widest text-gray-400">Active Model</h2>
      </div>

      <div className="space-y-0.5">
        <Row label="Model" value={activeModel.name} />
        <Row label="Provider" value={activeModel.provider} />
        <Row label="Endpoint" value={activeModel.baseUrl} />
        <Row label="Context Window" value={`${fmtNum(activeModel.contextWindow)} tokens`} />
        <Row label="Max Output" value={`${fmtNum(activeModel.maxTokens)} tokens`} />
        <Row
          label="Last Latency"
          value={
            switchState === 'confirmed' && lastLatencyMs !== null
              ? `${lastLatencyMs} ms`
              : '—'
          }
        />
        <Row
          label="Cost / 1k in"
          value={
            activeModel.costPer1kInput > 0
              ? `$${activeModel.costPer1kInput.toFixed(4)}`
              : 'Free'
          }
        />
        <Row
          label="Cost / 1k out"
          value={
            activeModel.costPer1kOutput > 0
              ? `$${activeModel.costPer1kOutput.toFixed(4)}`
              : 'Free'
          }
        />
      </div>
    </div>
  )
}
