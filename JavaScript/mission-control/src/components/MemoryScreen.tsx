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

function highlight(text: string, query: string): string {
  if (!query.trim()) return text
  const safe = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return text.replace(new RegExp(`(${safe})`, 'ig'), '<mark>$1</mark>')
}

export function MemoryScreen() {
  const [data, setData] = useState<MemoryIndex | null>(null)
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    fetch('/memory-index.json')
      .then((r) => r.json())
      .then((json: MemoryIndex) => {
        setData(json)
        if (json.documents.length > 0) setSelectedId(json.documents[0].id)
      })
      .catch(() => {
        setData({ generatedAt: new Date().toISOString(), count: 0, documents: [] })
      })
  }, [])

  const docs = data?.documents ?? []

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return docs
    return docs
      .map((doc) => {
        const idx = doc.content.toLowerCase().indexOf(q)
        const score = idx >= 0 ? 2 : 0
        const pathHit = doc.relativePath.toLowerCase().includes(q) ? 1 : 0
        return { doc, score: score + pathHit, idx }
      })
      .filter((x) => x.score > 0)
      .sort((a, b) => b.score - a.score || a.idx - b.idx)
      .map((x) => x.doc)
  }, [docs, query])

  const selected = filtered.find((d) => d.id === selectedId) ?? filtered[0] ?? null

  const preview = useMemo(() => {
    if (!selected) return ''
    if (!query.trim()) return selected.content.slice(0, 5000)
    const low = selected.content.toLowerCase()
    const q = query.toLowerCase()
    const idx = low.indexOf(q)
    if (idx < 0) return selected.content.slice(0, 5000)
    const start = Math.max(0, idx - 350)
    return selected.content.slice(start, start + 1800)
  }, [selected, query])

  return (
    <div className="space-y-4">
      <div className="bg-surface-1 border border-border rounded-lg p-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-gray-200 uppercase tracking-widest">Memory Screen</h2>
            <p className="text-xs text-gray-500 mt-1">
              Search across MEMORY.md + daily memory logs.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500 num">
            <span>{filtered.length} docs</span>
            {data?.generatedAt && <span>indexed {new Date(data.generatedAt).toLocaleString()}</span>}
          </div>
        </div>

        <div className="mt-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search memories, decisions, projects, people..."
            className="w-full bg-surface-2 border border-border rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-accent-blue"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-surface-1 border border-border rounded-lg p-2 max-h-[70vh] overflow-auto">
          {filtered.map((doc) => (
            <button
              key={doc.id}
              onClick={() => setSelectedId(doc.id)}
              className={`w-full text-left rounded p-2 border mb-2 transition-colors ${
                selected?.id === doc.id ? 'border-accent-blue/60 bg-surface-2' : 'border-border/50 bg-surface hover:bg-surface-2'
              }`}
            >
              <p className="text-xs text-gray-200 font-medium truncate">{doc.title}</p>
              <p className="text-[11px] text-gray-500 truncate">{doc.relativePath}</p>
              <p className="text-[11px] text-gray-600 num mt-1">{new Date(doc.updatedAt).toLocaleString()}</p>
            </button>
          ))}
          {filtered.length === 0 && <p className="text-xs text-gray-500 p-2">No matching memories.</p>}
        </div>

        <div className="lg:col-span-2 bg-surface-1 border border-border rounded-lg p-4 max-h-[70vh] overflow-auto">
          {selected ? (
            <>
              <div className="mb-3 border-b border-border/60 pb-2">
                <h3 className="text-sm font-bold text-gray-200">{selected.title}</h3>
                <p className="text-xs text-gray-500">{selected.path}</p>
              </div>
              <article
                className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed"
                dangerouslySetInnerHTML={{ __html: highlight(preview, query) }}
              />
            </>
          ) : (
            <p className="text-xs text-gray-500">No memory selected.</p>
          )}
        </div>
      </div>
    </div>
  )
}
