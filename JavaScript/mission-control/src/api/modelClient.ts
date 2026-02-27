import type { ModelConfig } from '../config/models'

const HANDSHAKE_PROMPT = 'Return exactly this token: VC_OK'
const HANDSHAKE_EXPECTED = 'VC_OK'

export interface HandshakeResult {
  success: boolean
  latencyMs: number
  error?: string
}

export interface HealthCheckResult {
  latencyMs: number | null
  reachable: boolean
  error?: string
}

function getApiKey(model: ModelConfig): string {
  if (!model.apiKeyEnv) return ''
  return (import.meta.env[model.apiKeyEnv] as string) ?? ''
}

function getBaseUrl(model: ModelConfig): string {
  // In dev, route remote providers through Vite proxy to avoid browser CORS issues.
  if (import.meta.env.DEV) {
    if (model.provider === 'Anthropic') return '/api/anthropic'
    if (model.provider === 'NVIDIA NIM') return '/api/nvidia'
    if (model.provider === 'xAI') return '/api/xai'
    if (model.provider === 'Groq') return '/api/groq'
  }
  return model.baseUrl
}

async function handshakeOpenAI(model: ModelConfig): Promise<HandshakeResult> {
  const apiKey = getApiKey(model)
  const t0 = performance.now()

  try {
    const res = await fetch(`${getBaseUrl(model)}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
      },
      body: JSON.stringify({
        model: model.id,
        messages: [{ role: 'user', content: HANDSHAKE_PROMPT }],
        max_tokens: 80,
      }),
      signal: AbortSignal.timeout(15000),
    })

    const latencyMs = Math.round(performance.now() - t0)

    if (!res.ok) {
      const text = await res.text()
      return { success: false, latencyMs, error: `HTTP ${res.status}: ${text.slice(0, 200)}` }
    }

    const data = await res.json()
    const content: string = data?.choices?.[0]?.message?.content ?? ''
    const success = content.includes(HANDSHAKE_EXPECTED)

    return {
      success,
      latencyMs,
      error: success ? undefined : `Unexpected response: "${content.slice(0, 100)}"`,
    }
  } catch (err) {
    return {
      success: false,
      latencyMs: Math.round(performance.now() - t0),
      error: err instanceof Error ? err.message : String(err),
    }
  }
}

async function handshakeAnthropic(model: ModelConfig): Promise<HandshakeResult> {
  const apiKey = getApiKey(model)
  const t0 = performance.now()

  try {
    const res = await fetch(`${getBaseUrl(model)}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true',
      },
      body: JSON.stringify({
        model: model.id,
        max_tokens: 80,
        messages: [{ role: 'user', content: HANDSHAKE_PROMPT }],
      }),
      signal: AbortSignal.timeout(15000),
    })

    const latencyMs = Math.round(performance.now() - t0)

    if (!res.ok) {
      const text = await res.text()
      return { success: false, latencyMs, error: `HTTP ${res.status}: ${text.slice(0, 200)}` }
    }

    const data = await res.json()
    const content: string = data?.content?.[0]?.text ?? ''
    const success = content.includes(HANDSHAKE_EXPECTED)

    return {
      success,
      latencyMs,
      error: success ? undefined : `Unexpected response: "${content.slice(0, 100)}"`,
    }
  } catch (err) {
    return {
      success: false,
      latencyMs: Math.round(performance.now() - t0),
      error: err instanceof Error ? err.message : String(err),
    }
  }
}

export async function handshake(model: ModelConfig): Promise<HandshakeResult> {
  if (model.provider === 'Anthropic') {
    return handshakeAnthropic(model)
  }
  return handshakeOpenAI(model)
}

export async function healthCheck(model: ModelConfig): Promise<HealthCheckResult> {
  const t0 = performance.now()

  try {
    // For OpenAI-compatible: hit /models endpoint as a lightweight probe
    const apiKey = getApiKey(model)
    const endpoint = `${getBaseUrl(model)}/models`

    const res = await fetch(endpoint, {
      method: 'GET',
      headers: {
        ...(model.provider === 'Anthropic'
          ? {
              'x-api-key': apiKey,
              'anthropic-version': '2023-06-01',
              'anthropic-dangerous-direct-browser-access': 'true',
            }
          : apiKey
          ? { Authorization: `Bearer ${apiKey}` }
          : {}),
      },
      signal: AbortSignal.timeout(8000),
    })

    const latencyMs = Math.round(performance.now() - t0)
    return { reachable: res.ok || res.status === 401 || res.status === 403, latencyMs }
  } catch (err) {
    return {
      reachable: false,
      latencyMs: null,
      error: err instanceof Error ? err.message : String(err),
    }
  }
}
