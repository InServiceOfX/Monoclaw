import { create } from 'zustand'
import { MODELS } from '../config/models'
import type { ModelConfig } from '../config/models'

export type HealthStatus = 'unknown' | 'checking' | 'healthy' | 'degraded' | 'unreachable'

export interface EndpointHealth {
  modelId: string
  status: HealthStatus
  latencyMs: number | null
  lastChecked: Date | null
}

export interface TokenUsage {
  inputTokens: number
  outputTokens: number
}

export type SwitchState = 'idle' | 'testing' | 'confirmed' | 'error'

export interface MissionState {
  // Active model
  activeModel: ModelConfig
  previousModel: ModelConfig | null
  switchState: SwitchState
  switchError: string | null
  lastLatencyMs: number | null

  // Token usage
  sessionUsage: Record<string, TokenUsage>

  // Health
  healthMap: Record<string, EndpointHealth>
  autoRefresh: boolean

  // Actions
  setActiveModel: (model: ModelConfig) => void
  setSwitchState: (state: SwitchState, error?: string, latencyMs?: number) => void
  revertModel: () => void
  addTokenUsage: (modelId: string, input: number, output: number) => void
  resetSession: () => void
  setHealth: (modelId: string, status: HealthStatus, latencyMs: number | null) => void
  setAutoRefresh: (val: boolean) => void
}

const initialHealth = (): Record<string, EndpointHealth> =>
  Object.fromEntries(
    MODELS.map((m) => [
      m.id,
      { modelId: m.id, status: 'unknown' as HealthStatus, latencyMs: null, lastChecked: null },
    ])
  )

const initialUsage = (): Record<string, TokenUsage> =>
  Object.fromEntries(MODELS.map((m) => [m.id, { inputTokens: 0, outputTokens: 0 }]))

export const useMissionStore = create<MissionState>((set) => ({
  activeModel: MODELS[0],
  previousModel: null,
  switchState: 'idle',
  switchError: null,
  lastLatencyMs: null,

  sessionUsage: initialUsage(),
  healthMap: initialHealth(),
  autoRefresh: true,

  setActiveModel: (model) =>
    set((s) => ({
      previousModel: s.activeModel,
      activeModel: model,
      switchState: 'idle',
      switchError: null,
    })),

  setSwitchState: (state, error, latencyMs) =>
    set({
      switchState: state,
      switchError: error ?? null,
      ...(latencyMs !== undefined ? { lastLatencyMs: latencyMs } : {}),
    }),

  revertModel: () =>
    set((s) => ({
      activeModel: s.previousModel ?? s.activeModel,
      previousModel: null,
      switchState: 'error',
    })),

  addTokenUsage: (modelId, input, output) =>
    set((s) => {
      const current = s.sessionUsage[modelId] ?? { inputTokens: 0, outputTokens: 0 }
      return {
        sessionUsage: {
          ...s.sessionUsage,
          [modelId]: {
            inputTokens: current.inputTokens + input,
            outputTokens: current.outputTokens + output,
          },
        },
      }
    }),

  resetSession: () => set({ sessionUsage: initialUsage() }),

  setHealth: (modelId, status, latencyMs) =>
    set((s) => ({
      healthMap: {
        ...s.healthMap,
        [modelId]: {
          modelId,
          status,
          latencyMs,
          lastChecked: new Date(),
        },
      },
    })),

  setAutoRefresh: (val) => set({ autoRefresh: val }),
}))
