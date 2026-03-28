#!/usr/bin/env node
/**
 * sync-openclaw-config.js
 * Reads ~/.openclaw/openclaw.json and generates src/config/mission-control.json
 * for this Mission Control instance.
 * 
 * Usage: node scripts/sync-openclaw-config.js
 *        node scripts/sync-openclaw-config.js --openclaw-config /path/to/openclaw.json
 *        node scripts/sync-openclaw-config.js --trtllm-dir /path/to/TensorRTLLMFixed
 */
const fs = require('fs')
const path = require('path')
const os = require('os')

// --- Parse args ---
const args = process.argv.slice(2)
function getArg(flag) {
  const i = args.indexOf(flag)
  return i >= 0 ? args[i + 1] : null
}

const openclawConfigPath = getArg('--openclaw-config')
  ?? path.join(os.homedir(), '.openclaw', 'openclaw.json')
const trtllmDir = getArg('--trtllm-dir') ?? null
const outputPath = path.join(__dirname, '..', 'src', 'config', 'mission-control.json')

// --- Known provider defaults ---
const PROVIDER_DEFAULTS = {
  anthropic: {
    displayProvider: 'Anthropic',
    baseUrl: 'https://api.anthropic.com/v1',
    apiKeyEnv: 'VITE_ANTHROPIC_API_KEY',
  },
  xai: {
    displayProvider: 'xAI',
    baseUrl: 'https://api.x.ai/v1',
    apiKeyEnv: 'VITE_XAI_API_KEY',
  },
  groq: {
    displayProvider: 'Groq',
    baseUrl: 'https://api.groq.com/openai/v1',
    apiKeyEnv: 'VITE_GROQ_API_KEY',
  },
  'nvidia-nim': {
    displayProvider: 'NVIDIA NIM',
    baseUrl: 'https://integrate.api.nvidia.com/v1',
    apiKeyEnv: 'VITE_NVIDIA_NIM_API_KEY',
  },
  sglang: {
    displayProvider: 'Local (SGLang)',
    baseUrl: 'http://localhost:30000/v1',
    apiKeyEnv: '',
  },
  openai: {
    displayProvider: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    apiKeyEnv: 'VITE_OPENAI_API_KEY',
  },
  'openai-codex': {
    displayProvider: 'OpenAI Codex',
    baseUrl: 'https://api.openai.com/v1',
    apiKeyEnv: 'VITE_OPENAI_API_KEY',
  },
}

const MODEL_COST_DEFAULTS = {
  'claude-sonnet-4-6': { contextWindow: 200000, maxTokens: 8192, costPer1kInput: 0.003, costPer1kOutput: 0.015 },
  'claude-opus-4-6':   { contextWindow: 200000, maxTokens: 32000, costPer1kInput: 0.015, costPer1kOutput: 0.075 },
  'claude-haiku-4-5':  { contextWindow: 200000, maxTokens: 8192, costPer1kInput: 0.00025, costPer1kOutput: 0.00125 },
  'grok-4-1-fast':     { contextWindow: 2000000, maxTokens: 65536, costPer1kInput: 0, costPer1kOutput: 0 },
}

// --- Load openclaw.json ---
if (!fs.existsSync(openclawConfigPath)) {
  console.error(`❌ openclaw.json not found at: ${openclawConfigPath}`)
  console.error('   Use: node scripts/sync-openclaw-config.js --openclaw-config /path/to/openclaw.json')
  process.exit(1)
}

let openclawCfg
try {
  openclawCfg = JSON.parse(fs.readFileSync(openclawConfigPath, 'utf8'))
} catch (e) {
  console.error(`❌ Failed to parse openclaw.json: ${e.message}`)
  process.exit(1)
}

// --- Extract workspace dir ---
const workspaceDir = openclawCfg?.agents?.defaults?.workspace?.dir
  ?? path.join(os.homedir(), '.openclaw', 'workspace')

// --- Extract models ---
const primaryModel = openclawCfg?.agents?.defaults?.model?.primary ?? ''
const fallbackModels = openclawCfg?.agents?.defaults?.model?.fallbacks ?? []
const modelAliases = openclawCfg?.agents?.defaults?.models ?? {}
const providers = openclawCfg?.models?.providers ?? {}

const allModelIds = [...new Set([primaryModel, ...fallbackModels].filter(Boolean))]

const models = allModelIds.slice(0, 10).map(fullId => {
  const parts = fullId.split('/')
  const providerKey = parts[0]
  const modelId = parts.slice(1).join('/')

  const providerCfg = providers[providerKey] ?? {}
  const providerDefaults = PROVIDER_DEFAULTS[providerKey] ?? {}
  const modelList = providerCfg.models ?? []
  const modelCfg = modelList.find(m => m.id === modelId) ?? {}

  // Get cost from openclaw config
  const cost = modelCfg.cost ?? {}

  // Model name: alias > openclaw name > model ID
  const aliasEntry = modelAliases[fullId]
  const alias = typeof aliasEntry === 'object' ? aliasEntry.alias : aliasEntry
  const displayName = alias ?? modelCfg.name ?? modelId

  // Cost/context: openclaw config > known defaults for model ID stem
  const knownDefaults = MODEL_COST_DEFAULTS[modelId.split('/').pop()] ?? {}

  return {
    id: fullId,
    displayName,
    provider: providerDefaults.displayProvider ?? providerKey,
    baseUrl: providerCfg.baseUrl ?? providerDefaults.baseUrl ?? '',
    apiKeyEnv: providerDefaults.apiKeyEnv ?? '',
    contextWindow: modelCfg.contextWindow ?? knownDefaults.contextWindow ?? 0,
    maxTokens: modelCfg.maxTokens ?? knownDefaults.maxTokens ?? 0,
    costPer1kInput: cost.input ?? knownDefaults.costPer1kInput ?? 0,
    costPer1kOutput: cost.output ?? knownDefaults.costPer1kOutput ?? 0,
  }
}).filter(m => m.id)

// --- Detect TRT-LLM dir ---
let trtllmScriptDir = trtllmDir
if (!trtllmScriptDir) {
  // Try common paths relative to workspace
  const candidates = [
    path.join(workspaceDir, 'repos', 'Monoclaw', 'Deployments', 'Scripts', 'TensorRTLLMFixed'),
    path.join(os.homedir(), 'Deployments', 'Scripts', 'TensorRTLLMFixed'),
  ]
  trtllmScriptDir = candidates.find(p => fs.existsSync(p)) ?? null
}

// --- Detect TRT-LLM profiles ---
let trtllmProfiles = []
if (trtllmScriptDir && fs.existsSync(path.join(trtllmScriptDir, 'profiles'))) {
  const profileFiles = fs.readdirSync(path.join(trtllmScriptDir, 'profiles'))
    .filter(f => f.endsWith('.yml') && !f.endsWith('.example.yml') && !f.includes('example'))
  trtllmProfiles = profileFiles.map(f => ({
    id: f.replace(/\.yml$/, ''),
    label: f.replace(/\.yml$/, '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    description: '',
  }))
}

// --- Build output config ---
const outputConfig = {
  _comment: `Instance config auto-generated by sync-openclaw-config.js on ${new Date().toISOString()}. Do not commit.`,
  openclaw: {
    workspaceDir,
  },
  models,
  localLLM: {
    trtllmScriptDir: trtllmScriptDir ?? '(not found — use --trtllm-dir)',
    port: 30000,
    profiles: trtllmProfiles.length > 0 ? trtllmProfiles : [
      { id: 'qwen3-1.7b', label: 'Qwen3-1.7B', description: '1.7B params' },
    ],
  },
}

// --- Write ---
fs.mkdirSync(path.dirname(outputPath), { recursive: true })
fs.writeFileSync(outputPath, JSON.stringify(outputConfig, null, 2) + '\n')

console.log(`✅ Written: ${outputPath}`)
console.log(`   Models: ${models.length}`)
console.log(`   Workspace: ${workspaceDir}`)
console.log(`   TRT-LLM: ${trtllmScriptDir ?? '(not detected)'}`)
console.log(`   TRT-LLM profiles: ${trtllmProfiles.map(p => p.id).join(', ') || '(none detected)'}`)
console.log()
console.log('Next steps:')
console.log('  npm run memory:build   # index your memory files')
console.log('  cp .env.example .env   # add your API keys')
console.log('  npm run dev            # start the dashboard')
