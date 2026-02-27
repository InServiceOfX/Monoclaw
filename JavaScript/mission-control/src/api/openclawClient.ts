import { MODELS, type ModelConfig } from '../config/models'

export interface OpenClawSessionModelResult {
  modelRef: string
}

function getOpenClawBaseUrl(): string {
  const raw = (import.meta.env.VITE_OPENCLAW_BASE_URL as string) || 'http://localhost:18789'
  return raw.replace(/\/$/, '')
}

function getOpenClawToken(): string {
  return (import.meta.env.VITE_OPENCLAW_TOKEN as string) || ''
}

// NOTE: This endpoint shape is a lightweight bridge contract for Mission Control.
// If your OpenClaw gateway plugin uses different routes, adjust here only.
async function openclawRequest(path: string, init?: RequestInit): Promise<Response> {
  const token = getOpenClawToken()
  return fetch(`${getOpenClawBaseUrl()}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  })
}

export async function getOpenClawSessionModel(): Promise<OpenClawSessionModelResult> {
  const res = await openclawRequest('/api/mission-control/session-model')
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`OpenClaw model read failed (HTTP ${res.status}): ${text.slice(0, 180)}`)
  }
  return res.json()
}

export async function setOpenClawSessionModel(model: ModelConfig): Promise<void> {
  const res = await openclawRequest('/api/mission-control/session-model', {
    method: 'POST',
    body: JSON.stringify({ modelRef: `${model.provider}/${model.id}` }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`OpenClaw model switch failed (HTTP ${res.status}): ${text.slice(0, 180)}`)
  }
}

export function resolveModelFromRef(modelRef: string): ModelConfig | null {
  // supports either full ref ("Provider/model") or raw model id
  return (
    MODELS.find((m) => `${m.provider}/${m.id}`.toLowerCase() === modelRef.toLowerCase()) ||
    MODELS.find((m) => m.id.toLowerCase() === modelRef.toLowerCase()) ||
    null
  )
}
