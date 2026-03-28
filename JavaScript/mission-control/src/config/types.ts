export interface ModelConfig {
  id: string
  name: string
  provider: string
  baseUrl: string
  apiKeyEnv: string
  contextWindow: number
  maxTokens: number
  costPer1kInput: number
  costPer1kOutput: number
}

export interface LocalLLMProfile {
  id: string
  label: string
  description: string
}

export interface MissionControlConfig {
  openclaw?: {
    workspaceDir?: string
  }
  models: ModelConfig[]
  localLLM?: {
    trtllmScriptDir?: string
    port?: number
    profiles?: LocalLLMProfile[]
  }
}
