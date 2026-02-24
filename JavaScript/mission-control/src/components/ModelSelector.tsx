import { useState } from 'react'
import { MODELS, PROVIDER_COLORS } from '../config/models'
import { useMissionStore } from '../store/useMissionStore'
import { handshake } from '../api/modelClient'

export function ModelSelector() {
  const {
    activeModel,
    switchState,
    switchError,
    lastLatencyMs,
    setActiveModel,
    setSwitchState,
    revertModel,
  } = useMissionStore()

  const [pendingId, setPendingId] = useState<string>(activeModel.id)

  async function handleSwitch() {
    const target = MODELS.find((m) => m.id === pendingId)
    if (!target || target.id === activeModel.id) return

    setSwitchState('testing')
    setActiveModel(target)

    const result = await handshake(target)

    if (result.success) {
      setSwitchState('confirmed', undefined, result.latencyMs)
    } else {
      revertModel()
      setSwitchState('error', result.error)
      setPendingId(activeModel.id)
    }
  }

  const providerColor = PROVIDER_COLORS[activeModel.provider] ?? '#58a6ff'

  return (
    <div className="bg-surface-1 border border-border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-widest text-gray-400">Model Switch</h2>
        {switchState === 'confirmed' && (
          <span className="text-xs font-bold text-accent-green shadow-confirmed px-2 py-0.5 border border-accent-green/40 rounded animate-pulse-once">
            ✓ CONFIRMED
          </span>
        )}
        {switchState === 'error' && (
          <span className="text-xs font-bold text-accent-red px-2 py-0.5 border border-accent-red/40 rounded">
            ✗ FAILED
          </span>
        )}
        {switchState === 'testing' && (
          <span className="text-xs font-bold text-accent-yellow px-2 py-0.5 border border-accent-yellow/40 rounded animate-pulse">
            ⟳ TESTING...
          </span>
        )}
      </div>

      <div className="flex gap-2">
        <select
          className="flex-1 bg-surface-2 border border-border rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-accent-blue cursor-pointer"
          value={pendingId}
          onChange={(e) => setPendingId(e.target.value)}
          disabled={switchState === 'testing'}
        >
          {MODELS.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} ({m.provider})
            </option>
          ))}
        </select>

        <button
          onClick={handleSwitch}
          disabled={switchState === 'testing' || pendingId === activeModel.id}
          className="px-4 py-2 text-sm font-bold bg-accent-blue/10 border border-accent-blue/40 text-accent-blue rounded hover:bg-accent-blue/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {switchState === 'testing' ? 'Testing…' : 'Switch'}
        </button>
      </div>

      {switchError && (
        <p className="text-xs text-accent-red bg-accent-red/10 border border-accent-red/20 rounded px-3 py-2 break-all">
          {switchError}
        </p>
      )}

      <div className="flex items-center gap-2 pt-1">
        <span
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: providerColor }}
        />
        <span className="text-xs text-gray-400">Active:</span>
        <span className="text-xs font-bold text-gray-200">{activeModel.name}</span>
        {lastLatencyMs !== null && switchState === 'confirmed' && (
          <span className="ml-auto text-xs text-gray-500 num">{lastLatencyMs} ms</span>
        )}
      </div>
    </div>
  )
}
