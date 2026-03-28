#!/usr/bin/env node
/**
 * build-memory-index.js
 * Reads memory files from the local OpenClaw workspace and writes
 * public/memory-index.json for the Memory tab.
 * 
 * Usage: node scripts/build-memory-index.js
 *        node scripts/build-memory-index.js --workspace /path/to/.openclaw/workspace
 */
const fs = require('fs')
const path = require('path')
const os = require('os')

// --- Args ---
const args = process.argv.slice(2)
function getArg(flag) {
  const i = args.indexOf(flag)
  return i >= 0 ? args[i + 1] : null
}

// Try to read workspace from mission-control.json
let defaultWorkspace = path.join(os.homedir(), '.openclaw', 'workspace')
const configPath = path.join(__dirname, '..', 'src', 'config', 'mission-control.json')
if (fs.existsSync(configPath)) {
  try {
    const cfg = JSON.parse(fs.readFileSync(configPath, 'utf8'))
    if (cfg?.openclaw?.workspaceDir) {
      defaultWorkspace = cfg.openclaw.workspaceDir.replace(/^~/, os.homedir())
    }
  } catch {}
}

const workspaceDir = (getArg('--workspace') ?? defaultWorkspace).replace(/^~/, os.homedir())
const outputPath = path.join(__dirname, '..', 'public', 'memory-index.json')

console.log(`📂 Workspace: ${workspaceDir}`)

// --- Collect memory files ---
const memoryFiles = []

// MEMORY.md (main long-term memory)
const mainMemoryPath = path.join(workspaceDir, 'MEMORY.md')
if (fs.existsSync(mainMemoryPath)) {
  memoryFiles.push({ filePath: mainMemoryPath, relativePath: 'MEMORY.md' })
}

// memory/ directory (daily notes + other files)
const memoryDir = path.join(workspaceDir, 'memory')
if (fs.existsSync(memoryDir)) {
  const files = fs.readdirSync(memoryDir)
    .filter(f => f.endsWith('.md') || f.endsWith('.json'))
    .sort()
    .reverse()  // newest first
  for (const f of files) {
    memoryFiles.push({ filePath: path.join(memoryDir, f), relativePath: path.join('memory', f) })
  }
}

if (memoryFiles.length === 0) {
  console.warn(`⚠️  No memory files found in: ${workspaceDir}`)
  console.warn('   Create MEMORY.md or a memory/ directory in your workspace.')
}

// --- Build index ---
const documents = memoryFiles.map(({ filePath, relativePath }, i) => {
  const stat = fs.statSync(filePath)
  const content = fs.readFileSync(filePath, 'utf8')
  const title = relativePath.split('/').pop() ?? relativePath
  return {
    id: `doc-${i}`,
    title,
    path: filePath,
    relativePath,
    updatedAt: stat.mtime.toISOString(),
    sizeBytes: stat.size,
    content,
  }
})

const index = {
  generatedAt: new Date().toISOString(),
  count: documents.length,
  documents,
}

// --- Write ---
fs.mkdirSync(path.dirname(outputPath), { recursive: true })
fs.writeFileSync(outputPath, JSON.stringify(index, null, 2) + '\n')

console.log(`✅ Written: ${outputPath}`)
console.log(`   Documents: ${documents.length}`)
console.log(`   Files:`)
for (const doc of documents) {
  console.log(`     ${doc.relativePath} (${doc.sizeBytes} bytes)`)
}
