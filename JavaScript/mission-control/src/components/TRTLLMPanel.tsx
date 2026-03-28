import { useCallback, useEffect, useRef, useState } from 'react'
import config from '../config/mission-control.json'

// ─── config ──────────────────────────────────────────────────────────────────

const localLLM = (config as unknown as {
  localLLM?: {
    trtllmScriptDir?: string
    port?: number
    profiles?: { id: string; label: string; description: string }[]
  }
}).localLLM ?? {}

const SCRIPT_DIR = localLLM.trtllmScriptDir ?? '(not configured — run node scripts/sync-openclaw-config.js)'
const SERVER_PORT = localLLM.port ?? 30000

interface Profile {
  id: string
  label: string
  description: string
  model: string
}

const PROFILES: Profile[] = (localLLM.profiles ?? []).map((p) => ({
  id: p.id,
  label: p.label,
  description: p.description,
  model: p.id,
}))

type Mode = 'thinking' | 'no-think' | 'instruct' | 'coding'

const MODES: { id: Mode; label: string; note: string }[] = [
  { id: 'thinking', label: 'Thinking', note: 'Extended reasoning (default)' },
  { id: 'no-think', label: 'Instruct', note: 'Fast, no reasoning chain' },
  { id: 'coding',   label: 'Coding',   note: 'Thinking w/ coding prompt' },
]

type ServerStatus = 'unknown' | 'checking' | 'running' | 'stopped'

// ─── helpers ─────────────────────────────────────────────────────────────────

function makeServeCmd(profile: Profile, mode: Mode): string {
  const modeFlag = mode === 'thinking' ? '' : ` --${mode}`
  return `cd '${SCRIPT_DIR}'\n./trtllm_launch.sh ${profile.id}${modeFlag}`
}

function makeChatCmd(profile: Profile): string {
  return `cd '${SCRIPT_DIR}'\nTRTLLM_PROFILE=${profile.id} ./chat.sh`
}

function makeStopCmd(): string {
  return 'docker stop trtllm-serve'
}

// ─── sub-components ───────────────────────────────────────────────────────────

function CopyBox({ label, code, highlight = false }: { label: string; code: string; highlight?: boolean }) {
  const [copied, setCopied] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div className={`rounded-lg border p-3 space-y-2 ${
      highlight
        ? 'border-accent-green/40 bg-accent-green/5'
        : 'border-border bg-surface-2'
    }`}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-widest text-gray-500 font-bold">{label}</span>
        <button
          onClick={copy}
          className={`text-[11px] px-2 py-0.5 rounded border transition-colors ${
            copied
              ? 'border-accent-green/60 text-accent-green'
              : 'border-border text-gray-400 hover:border-accent-blue/50 hover:text-accent-blue'
          }`}
        >
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <pre className="text-[11px] text-gray-300 font-mono whitespace-pre-wrap leading-relaxed">{code}</pre>
    </div>
  )
}

function StatusBadge({ status }: { status: ServerStatus }) {
  const cfg: Record<ServerStatus, { dot: string; label: string; text: string }> = {
    unknown:  { dot: 'bg-gray-600',                      label: 'Unknown',  text: 'text-gray-500' },
    checking: { dot: 'bg-accent-yellow animate-pulse',    label: 'Checking', text: 'text-accent-yellow' },
    running:  { dot: 'bg-accent-green',                   label: 'Running ✅', text: 'text-accent-green' },
    stopped:  { dot: 'bg-accent-red',                     label: 'Stopped',  text: 'text-accent-red' },
  }
  const c = cfg[status]
  return (
    <div className="flex items-center gap-1.5">
      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${c.dot}`} />
      <span className={`text-xs font-medium ${c.text}`}>{c.label}</span>
    </div>
  )
}

// ─── main panel ──────────────────────────────────────────────────────────────

export function TRTLLMPanel() {
  const [profile, setProfile] = useState<Profile>(PROFILES[0])
  const [mode, setMode] = useState<Mode>('thinking')
  const [status, setStatus] = useState<ServerStatus>('unknown')
  const [lastChecked, setLastChecked] = useState<Date | null>(null)
  const [modelsInfo, setModelsInfo] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const checkStatus = useCallback(async () => {
    setStatus('checking')
    try {
      const r = await fetch(`http://localhost:${SERVER_PORT}/v1/models`, {
        signal: AbortSignal.timeout(3000),
      })
      if (r.ok) {
        const data = await r.json()
        const ids = (data?.data ?? []).map((m: { id: string }) => m.id).join(', ')
        setModelsInfo(ids || '(no models listed)')
        setStatus('running')
      } else {
        setStatus('stopped')
        setModelsInfo(null)
      }
    } catch {
      setStatus('stopped')
      setModelsInfo(null)
    }
    setLastChecked(new Date())
  }, [])

  // Check on mount + every 15s
  useEffect(() => {
    checkStatus()
    intervalRef.current = setInterval(checkStatus, 15000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [checkStatus])

  const serveCmd = makeServeCmd(profile, mode)
  const chatCmd  = makeChatCmd(profile)
  const stopCmd  = makeStopCmd()

  return (
    <div className="bg-surface-1 border border-border rounded-lg p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-bold uppercase tracking-widest text-gray-400">
            TensorRT-LLM Local
          </h2>
          <p className="text-[11px] text-gray-600 mt-0.5">RTX 3060 · GPU 1 · port {SERVER_PORT}</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={status} />
          <button
            onClick={checkStatus}
            className="text-[11px] text-accent-blue hover:text-accent-blue/80 border border-accent-blue/30 rounded px-2 py-0.5 transition-colors"
          >
            Ping
          </button>
        </div>
      </div>

      {/* Running model info */}
      {status === 'running' && modelsInfo && (
        <div className="bg-accent-green/5 border border-accent-green/30 rounded px-3 py-2">
          <p className="text-[11px] text-accent-green">
            Serving: <span className="font-mono">{modelsInfo}</span>
          </p>
          {lastChecked && (
            <p className="text-[11px] text-gray-600 mt-0.5">
              Checked {lastChecked.toLocaleTimeString()}
            </p>
          )}
        </div>
      )}

      {/* Profile selector */}
      <div className="space-y-1.5">
        <p className="text-[11px] uppercase tracking-widest text-gray-500 font-bold">Profile</p>
        <div className="grid grid-cols-1 gap-1.5">
          {PROFILES.map((p) => (
            <button
              key={p.id}
              onClick={() => setProfile(p)}
              className={`text-left rounded px-3 py-2 border transition-colors ${
                profile.id === p.id
                  ? 'border-accent-blue/60 bg-accent-blue/10'
                  : 'border-border bg-surface-2 hover:border-border/80'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className={`text-xs font-bold ${profile.id === p.id ? 'text-accent-blue' : 'text-gray-300'}`}>
                  {p.label}
                </span>
                {profile.id === p.id && (
                  <span className="text-[10px] text-accent-blue/70 uppercase tracking-wide">selected</span>
                )}
              </div>
              <p className="text-[11px] text-gray-500 mt-0.5">{p.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Mode selector */}
      <div className="space-y-1.5">
        <p className="text-[11px] uppercase tracking-widest text-gray-500 font-bold">Mode</p>
        <div className="flex gap-1.5 flex-wrap">
          {MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              title={m.note}
              className={`px-2.5 py-1 rounded text-xs border transition-colors ${
                mode === m.id
                  ? 'border-accent-purple/60 bg-accent-purple/10 text-accent-purple'
                  : 'border-border text-gray-400 hover:text-gray-200'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <p className="text-[11px] text-gray-600">
          {MODES.find((m) => m.id === mode)?.note}
        </p>
      </div>

      {/* Commands */}
      <div className="space-y-2.5">
        <CopyBox
          label="1 · Start server"
          code={serveCmd}
          highlight={status === 'stopped' || status === 'unknown'}
        />
        <CopyBox
          label="2 · Chat (after server is ✅ ready)"
          code={chatCmd}
          highlight={status === 'running'}
        />
        <CopyBox
          label="Stop server"
          code={stopCmd}
        />
      </div>

      {/* Workflow note */}
      <div className="border-t border-border/50 pt-3">
        <p className="text-[11px] text-gray-600 leading-relaxed">
          <span className="text-gray-500 font-bold">Workflow: </span>
          Run <span className="font-mono text-gray-400">trtllm_launch.sh</span> in a terminal,
          wait for <span className="text-accent-green">✅ Server ready</span>, then run{' '}
          <span className="font-mono text-gray-400">chat.sh</span> in a second terminal.
          The server stays up until <span className="font-mono text-gray-400">docker stop trtllm-serve</span>.
        </p>
        <p className="text-[11px] text-gray-600 mt-1.5 leading-relaxed">
          <span className="text-gray-500 font-bold">Direct API: </span>
          <span className="font-mono text-gray-400">http://localhost:{SERVER_PORT}/v1/chat/completions</span> (OpenAI-compatible)
        </p>
      </div>
    </div>
  )
}
