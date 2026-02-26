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

// In dev, route through Vite proxy to avoid CORS.
// In production, use direct URLs (requires a backend proxy or server-side calls).
const isDev = import.meta.env.DEV

export const MODELS: ModelConfig[] = [
  {
    id: "claude-sonnet-4-6",
    name: "Claude Sonnet 4.6",
    provider: "Anthropic",
    baseUrl: isDev ? "/proxy/anthropic/v1" : "https://api.anthropic.com/v1",
    apiKeyEnv: "VITE_ANTHROPIC_API_KEY",
    contextWindow: 200000,
    maxTokens: 8192,
    costPer1kInput: 0.003,
    costPer1kOutput: 0.015,
  },
  {
    id: "qwen3-1.7b",
    name: "Qwen3-1.7B (local)",
    provider: "SGLang",
    baseUrl: "http://localhost:30000/v1",
    apiKeyEnv: "",
    contextWindow: 163840,
    maxTokens: 8192,
    costPer1kInput: 0,
    costPer1kOutput: 0,
  },
  {
    id: "moonshotai/kimi-k2.5",
    name: "Kimi K2.5 (NIM)",
    provider: "NVIDIA NIM",
    baseUrl: isDev ? "/proxy/nvidia-nim/v1" : "https://integrate.api.nvidia.com/v1",
    apiKeyEnv: "VITE_NVIDIA_NIM_API_KEY",
    contextWindow: 262144,
    maxTokens: 16384,
    costPer1kInput: 0,
    costPer1kOutput: 0,
  },
  {
    id: "grok-4-1-fast",
    name: "Grok 4.1 Fast",
    provider: "xAI",
    baseUrl: isDev ? "/proxy/xai/v1" : "https://api.x.ai/v1",
    apiKeyEnv: "VITE_XAI_API_KEY",
    contextWindow: 2000000,
    maxTokens: 65536,
    costPer1kInput: 0,
    costPer1kOutput: 0,
  },
  {
    id: "openai/gpt-oss-20b",
    name: "GPT-OSS 20B",
    provider: "Groq",
    baseUrl: isDev ? "/proxy/groq/openai/v1" : "https://api.groq.com/openai/v1",
    apiKeyEnv: "VITE_GROQ_API_KEY",
    contextWindow: 200000,
    maxTokens: 8192,
    costPer1kInput: 0,
    costPer1kOutput: 0,
  },
]

export const PROVIDER_COLORS: Record<string, string> = {
  Anthropic: "#cc785c",
  SGLang: "#58a6ff",
  "NVIDIA NIM": "#76b900",
  xAI: "#ffffff",
  Groq: "#f55036",
}
