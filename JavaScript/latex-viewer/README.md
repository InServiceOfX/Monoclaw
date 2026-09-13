# LaTeX Live Viewer

A self-contained, browser-based LaTeX + Markdown live-rendering tool.  
No build step, no server, no dependencies to install — just open the file.

---

## How to open

```bash
# From the repo root:
open JavaScript/latex-viewer/index.html          # macOS
xdg-open JavaScript/latex-viewer/index.html     # Linux
start JavaScript/latex-viewer/index.html        # Windows
```

Or simply double-click `index.html` in your file manager, or drag it into any browser tab.

---

## Features

| Feature | Details |
|---|---|
| **Live rendering** | Auto-renders ~300 ms after you stop typing (debounced) |
| **Autosave** | Editor contents and split position persist in the browser's `localStorage`; reopening the page restores your last document |
| **Math** | KaTeX 0.18 — fast, accurate LaTeX rendering |
| **Inline math** | Wrap with `$...$` or `\(...\)` — pandoc rule: no space just inside the `$`, so `$5 or $10` stays text; `\$` is a literal dollar |
| **Display math** | Wrap with `$$...$$` or `\[...\]`; may span lines and blank lines |
| **Markdown** | marked.js — headings, bold, italic, code blocks, tables, blockquotes |
| **Code is code** | `$` inside fenced blocks and inline code is never treated as math |
| **Open / drop** | `Open…` button or drag a `.md` / `.tex` / `.txt` file onto the editor |
| **Save** | `Save .md` button or **Ctrl+S** downloads the editor contents (named after the first `#` heading) |
| **Print / PDF** | **Ctrl+P** prints the rendered preview only, in paper colours |
| **Resizable split** | Drag the divider between the panels |
| **Scroll sync** | Scrolling the editor scrolls the preview proportionally (one way, so the preview can still be scrolled independently) |
| **Dark theme** | Terminal / physics-paper aesthetic |
| **Copy LaTeX** | Copies the full editor contents to clipboard |
| **Example / Clear** | Reload the demo document, or clear the editor (with confirmation) |
| **Tab key** | Inserts 2 spaces (undo-safe) instead of switching focus |

---

## Supported physics notation

All standard KaTeX commands work.  Built-in macros include:

| Macro | Expands to |
|---|---|
| `\ket{ψ}` / `\bra{ψ}` | `\left\|ψ\right\rangle` / `\left\langle ψ\right\|` |
| `\braket{φ\|ψ}` | inner product `⟨φ|ψ⟩` |
| `\mel{m\|A\|n}` | matrix element `⟨m|A|n⟩` |
| `\ev{A}` / `\expval{A}` | expectation value `⟨A⟩` |
| `\comm{A}{B}` / `\acomm{A}{B}` | commutator `[A, B]` / anti-commutator `{A, B}` |
| `\pdv{f}{x}` / `\dv{f}{x}` | partial / ordinary derivative fraction |
| `\dd` | upright `d` (for differentials) |
| `\abs{x}` / `\norm{v}` | absolute value bars / norm double bars |
| `\order{n}` | big-O `𝒪(n)` |
| `\Tr` / `\tr` / `\rank` / `\diag` | upright operators |
| `\vb{v}` / `\vu{n}` | bold vector / bold unit vector `n̂` |
| `\grad` / `\curl` / `\divergence` / `\laplacian` | `∇` / `∇×` / `∇·` / `∇²` |
| `\cross` | `×` |
| `A\T` | transpose `Aᵀ` |
| `\R` `\C` `\N` `\Z` `\Q` | blackboard-bold number sets |
| `\SO{3}` / `\SU{2}` / `\SE{3}` | `SO(3)` / `SU(2)` / `SE(3)` |

Plus every command in the [KaTeX support table](https://katex.org/docs/support_table):  
`\partial`, `\nabla`, `\psi`, `\phi`, `\Psi`, `\Phi`, `\mathcal{}`,  
`\hbar`, `\varepsilon`, `\otimes`, `\oplus`, `\dagger`, `\infty`, etc.

---

## How math survives Markdown

Math spans are swapped for placeholders *before* marked.js runs (so `_` and `*`
inside equations are never turned into emphasis), then each span is rendered
with `katex.renderToString` and spliced back into the HTML.  KaTeX's
`auto-render` extension is deliberately not used: it rescans the page with its
own `$` rule and would render currency-like text.

---

## Stack

- **[KaTeX](https://katex.org/) 0.18.7** — math rendering (loaded from jsDelivr CDN)
- **[marked.js](https://marked.js.org/) 18** — Markdown parsing (loaded from jsDelivr CDN)
- Pure HTML/CSS/JS — zero build tooling

---

## Offline use

The tool requires CDN access for KaTeX and marked; if they fail to load the
page says so instead of rendering nothing (your text is still autosaved).  
To use offline, download the CDN assets and update the `<link>` / `<script>` `src` attributes to local paths.

```
https://cdn.jsdelivr.net/npm/katex@0.18.7/dist/katex.min.css
https://cdn.jsdelivr.net/npm/katex@0.18.7/dist/katex.min.js
https://cdn.jsdelivr.net/npm/marked@18.0.13/lib/marked.umd.min.js
```
