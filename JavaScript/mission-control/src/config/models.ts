import config from './mission-control.json'
import type { ModelConfig } from './types'

export type { ModelConfig }

// Map from config format to ModelConfig (handles both 'displayName' and 'name' keys)
function toModelConfig(m: Record<string, unknown>): ModelConfig {
  return {
    id: String(m.id ?? ''),
    name: String(m.displayName ?? m.name ?? m.id ?? 'Unknown'),
    provider: String(m.provider ?? ''),
    baseUrl: String(m.baseUrl ?? ''),
    apiKeyEnv: String(m.apiKeyEnv ?? ''),
    contextWindow: Number(m.contextWindow ?? 0),
    maxTokens: Number(m.maxTokens ?? 0),
    costPer1kInput: Number(m.costPer1kInput ?? 0),
    costPer1kOutput: Number(m.costPer1kOutput ?? 0),
  }
}

export const MODELS: ModelConfig[] = (
  (config as unknown as { models?: unknown[] }).models ?? []
).map((m) => toModelConfig(m as Record<string, unknown>))

export const PROVIDER_COLORS: Record<string, string> = {
  Anthropic: '#d97757',
  xAI: '#ffffff',
  Groq: '#f55036',
  'NVIDIA NIM': '#76b900',
  Local: '#22c55e',
  SGLang: '#22c55e',
  'OpenAI Codex': '#412991',
}
