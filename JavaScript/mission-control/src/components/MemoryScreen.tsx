import { useEffect, useMemo, useState } from 'react'

type MemoryDoc = {
  id: string
  title: string
  path: string
  relativePath: string
  updatedAt: string
  sizeBytes: number
  content: string
}

type MemoryIndex = {
  generatedAt: string
  count: number
  documents: MemoryDoc[]
}

// ─── simple markdown → HTML renderer ─────────────────────────────────────────
// Handles: ## headers, **bold**, `inline code`, ```code blocks```, > blockquote
// Does NOT use any library — just regex replacements, safe enough for local files.
function renderMarkdown(text: string): string {
  // Escape HTML first (content is local so low risk, but be safe)
  const escape = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  const lines = text.split('\n')
  const out: string[] = []
  let inCode = false
  let inBlockquote = false

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i]

    // Fenced code block
    if (line.startsWith('```')) {
      if (!inCode) {
        out.push('<pre class="bg-surface rounded px-3 py-2 text-[11px] text-gray-300 overflow-x-auto my-2">')
        inCode = true
      } else {
        out.push('</pre>')
        inCode = false
      }
      continue
    }
    if (inCode) {
      out.push(escape(line))
      continue
    }

    // Blockquote
    if (line.startsWith('> ')) {
      if (!inBlockquote) {
        out.push('<blockquote class="border-l-2 border-accent-blue/50 pl-3 text-gray-400 my-1">')
        inBlockquote = true
      }
      line = line.slice(2)
    } else if (inBlockquote) {
      out.push('</blockquote>')
      inBlockquote = false
    }

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      out.push('<hr class="border-border/50 my-3" />')
      continue
    }

    // Headers
    const h3 = line.match(/^### (.+)/)
    const h2 = line.match(/^## (.+)/)
    const h1 = line.match(/^# (.+)/)
    if (h1) {
      out.push(`<h1 class="text-sm font-bold text-gray-100 mt-4 mb-1">${escape(h1[1])}</h1>`)
      continue
    }
    if (h2) {
      out.push(`<h2 class="text-xs font-bold text-accent-blue uppercase tracking-wider mt-4 mb-1">${escape(h2[1])}</h2>`)
      continue
    }
    if (h3) {
      out.push(`<h3 class="text-xs font-semibold text-gray-300 mt-3 mb-0.5">${escape(h3[1])}</h3>`)
      continue
    }

    // Bullet list items
    if (/^[\-\*] /.test(line)) {
      const content = inlineMarkdown(escape(line.slice(2)))
      out.push(`<div class="flex gap-2 text-xs text-gray-300 leading-relaxed"><span class="text-gray-600 flex-shrink-0">•</span><span>${content}</span></div>`)
      continue
    }

    // Numbered list
    const numbered = line.match(/^(\d+)\. (.+)/)
    if (numbered) {
      const content = inlineMarkdown(escape(numbered[2]))
      out.push(`<div class="flex gap-2 text-xs text-gray-300 leading-relaxed"><span class="text-gray-600 flex-shrink-0 num">${numbered[1]}.</span><span>${content}</span></div>`)
      continue
    }

    // Empty line → spacing
    if (!line.trim()) {
      out.push('<div class="h-1.5"></div>')
      continue
    }

    // Normal paragraph
    out.push(`<p class="text-xs text-gray-300 leading-relaxed">${inlineMarkdown(escape(line))}</p>`)
  }

  if (inCode) out.push('</pre>')
  if (inBlockquote) out.push('</blockquote>')

  return out.join('\n')
}

function inlineMarkdown(s: string): string {
  return s
    // **bold**
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-100 font-bold">$1</strong>')
    // *italic*
    .replace(/\*(.+?)\*/g, '<em class="text-gray-300 italic">$1</em>')
    // `code`
    .replace(/`([^`]+)`/g, '<code class="bg-surface px-1 rounded text-accent-yellow text-[10px] font-mono">$1</code>')
    // [text](url)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" class="text-accent-blue underline underline-offset-2" target="_blank">$1</a>')
}

// ─── search highlight (raw HTML safe version) ─────────────────────────────────
function highlight(text: string, query: string): string {
  if (!query.trim()) return text
  const safe = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return text.replace(
    new RegExp(`(${safe})`, 'ig'),
    '<mark class="bg-accent-yellow/30 text-accent-yellow rounded px-0.5">$1</mark>'
  )
}

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}

// ─── component ────────────────────────────────────────────────────────────────

export function MemoryScreen() {
  const [data, setData] = useState<MemoryIndex | null>(null)
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [rawMode, setRawMode] = useState(false)

  useEffect(() => {
    fetch('/memory-index.json')
      .then((r) => r.json())
      .then((json: MemoryIndex) => {
        setData(json)
        // auto-select MEMORY.md if present, else first doc
        const memoryMd = json.documents.find((d) =>
          d.relativePath === 'MEMORY.md' || d.title === 'MEMORY.md'
        )
        setSelectedId((memoryMd ?? json.documents[0])?.id ?? null)
      })
      .catch(() => {
        setData({ generatedAt: new Date().toISOString(), count: 0, documents: [] })
      })
  }, [])

  const docs = data?.documents ?? []

  // Sort: MEMORY.md always first, then daily notes, then others
  const sorted = useMemo(() => {
    return [...docs].sort((a, b) => {
      const aIsMain = a.relativePath === 'MEMORY.md'
      const bIsMain = b.relativePath === 'MEMORY.md'
      if (aIsMain && !bIsMain) return -1
      if (bIsMain && !aIsMain) return 1
      // daily notes next
      const aIsDaily = a.relativePath.startsWith('memory/')
      const bIsDaily = b.relativePath.startsWith('memory/')
      if (aIsDaily && !bIsDaily) return -1
      if (bIsDaily && !aIsDaily) return 1
      return b.updatedAt.localeCompare(a.updatedAt)
    })
  }, [docs])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return sorted
    return sorted
      .map((doc) => {
        const idx = doc.content.toLowerCase().indexOf(q)
        const score = idx >= 0 ? 2 : 0
        const pathHit = doc.relativePath.toLowerCase().includes(q) ? 1 : 0
        return { doc, score: score + pathHit, idx }
      })
      .filter((x) => x.score > 0)
      .sort((a, b) => b.score - a.score || a.idx - b.idx)
      .map((x) => x.doc)
  }, [sorted, query])

  const selected = filtered.find((d) => d.id === selectedId) ?? filtered[0] ?? null

  const preview = useMemo(() => {
    if (!selected) return ''
    if (!query.trim()) return selected.content
    const low = selected.content.toLowerCase()
    const q = query.toLowerCase()
    const idx = low.indexOf(q)
    if (idx < 0) return selected.content.slice(0, 6000)
    const start = Math.max(0, idx - 400)
    return selected.content.slice(start, start + 3000)
  }, [selected, query])

  const isMainMemory = selected?.relativePath === 'MEMORY.md'

  const renderedContent = useMemo(() => {
    if (!preview) return ''
    if (rawMode) return ''
    let html = renderMarkdown(preview)
    if (query.trim()) html = highlight(html, query)
    return html
  }, [preview, rawMode, query])

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="bg-surface-1 border border-border rounded-lg p-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-gray-200 uppercase tracking-widest">Memory</h2>
            <p className="text-xs text-gray-500 mt-1">
              MEMORY.md · daily logs · decisions · context
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span className="num">{filtered.length} docs</span>
            {data?.generatedAt && (
              <span>indexed {new Date(data.generatedAt).toLocaleString()}</span>
            )}
          </div>
        </div>

        <div className="mt-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search memories, decisions, projects, people..."
            className="w-full bg-surface-2 border border-border rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-accent-purple"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Doc list */}
        <div className="bg-surface-1 border border-border rounded-lg p-2 max-h-[72vh] overflow-auto">
          {filtered.map((doc) => {
            const isMain = doc.relativePath === 'MEMORY.md'
            const isSelected = selected?.id === doc.id
            return (
              <button
                key={doc.id}
                onClick={() => setSelectedId(doc.id)}
                className={`w-full text-left rounded p-2 border mb-1.5 transition-colors ${
                  isSelected
                    ? isMain
                      ? 'border-accent-purple/60 bg-accent-purple/10'
                      : 'border-accent-blue/60 bg-surface-2'
                    : isMain
                    ? 'border-accent-purple/30 bg-surface hover:bg-surface-2'
                    : 'border-border/50 bg-surface hover:bg-surface-2'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  {isMain && (
                    <span className="text-[9px] uppercase tracking-wider text-accent-purple font-bold bg-accent-purple/20 rounded px-1 py-0.5 flex-shrink-0">
                      MAIN
                    </span>
                  )}
                  <p className="text-xs text-gray-200 font-medium truncate">{doc.title}</p>
                </div>
                <p className="text-[11px] text-gray-500 truncate mt-0.5">{doc.relativePath}</p>
                <div className="flex items-center justify-between mt-1">
                  <p className="text-[11px] text-gray-600 num">
                    {new Date(doc.updatedAt).toLocaleDateString()}
                  </p>
                  <p className="text-[11px] text-gray-600 num">{fmtBytes(doc.sizeBytes)}</p>
                </div>
              </button>
            )
          })}
          {filtered.length === 0 && (
            <p className="text-xs text-gray-500 p-2">No matching memories.</p>
          )}
        </div>

        {/* Content pane */}
        <div className="lg:col-span-2 bg-surface-1 border border-border rounded-lg p-4 max-h-[72vh] overflow-auto">
          {selected ? (
            <>
              {/* Doc header */}
              <div className="mb-3 border-b border-border/60 pb-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    {isMainMemory && (
                      <span className="text-[9px] uppercase tracking-wider text-accent-purple font-bold bg-accent-purple/20 rounded px-1.5 py-0.5 flex-shrink-0">
                        Long-term Memory
                      </span>
                    )}
                    <h3 className="text-sm font-bold text-gray-200 truncate">{selected.title}</h3>
                  </div>
                  <button
                    onClick={() => setRawMode((v) => !v)}
                    className="text-[11px] px-2 py-0.5 rounded border border-border text-gray-500 hover:text-gray-300 flex-shrink-0 transition-colors"
                  >
                    {rawMode ? 'Rendered' : 'Raw'}
                  </button>
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-[11px] text-gray-600">
                  <span>{selected.path}</span>
                  <span className="num">{fmtBytes(selected.sizeBytes)}</span>
                  <span>Updated {new Date(selected.updatedAt).toLocaleString()}</span>
                </div>
              </div>

              {/* Content */}
              {rawMode ? (
                <pre className="text-[11px] text-gray-300 font-mono whitespace-pre-wrap leading-relaxed">
                  {query.trim()
                    ? preview
                    : selected.content}
                </pre>
              ) : (
                <article
                  className="prose-sm space-y-0.5"
                  dangerouslySetInnerHTML={{ __html: renderedContent }}
                />
              )}
            </>
          ) : (
            <p className="text-xs text-gray-500">No memory selected.</p>
          )}
        </div>
      </div>
    </div>
  )
}
