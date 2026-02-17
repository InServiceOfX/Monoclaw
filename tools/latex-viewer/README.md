# LaTeX Live Viewer

A self-contained, browser-based LaTeX + Markdown live-rendering tool.  
No build step, no server, no dependencies to install — just open the file.

---

## How to open

```bash
# From the repo root:
open tools/latex-viewer/index.html          # macOS
xdg-open tools/latex-viewer/index.html     # Linux
start tools/latex-viewer/index.html        # Windows
```

Or simply double-click `index.html` in your file manager, or drag it into any browser tab.

---

## Features

| Feature | Details |
|---|---|
| **Live rendering** | Auto-renders ~300 ms after you stop typing (debounced) |
| **Math** | KaTeX v0.16.9 — fast, accurate LaTeX rendering |
| **Inline math** | Wrap with `$...$` or `\(...\)` |
| **Display math** | Wrap with `$$...$$` or `\[...\]` |
| **Markdown** | marked.js — headings, bold, italic, code blocks, tables, blockquotes |
| **Dark theme** | Terminal / physics-paper aesthetic |
| **Copy LaTeX** | Copies the full editor contents to clipboard |
| **Clear** | Clears the editor (with confirmation) |
| **Tab key** | Inserts 2 spaces instead of switching focus |

---

## Supported physics notation

All standard KaTeX commands work.  Built-in macros include:

| Macro | Expands to |
|---|---|
| `\ket{ψ}` | `\left\|ψ\right\rangle` |
| `\bra{ψ}` | `\left\langle ψ\right\|` |
| `\braket{φ\|ψ}` | full inner-product brackets |
| `\mel{m\|A\|n}` | matrix element |
| `\ev{A}` / `\expval{A}` | expectation value brackets |
| `\comm{A}{B}` | commutator `[A, B]` |
| `\acomm{A}{B}` | anti-commutator `{A, B}` |
| `\pdv{f}{x}` | partial derivative fraction |
| `\dv{f}{x}` | ordinary derivative fraction |
| `\abs{x}` | absolute value bars |
| `\norm{v}` | norm double bars |
| `\order{n}` | big-O `𝒪(n)` |
| `\Tr` / `\tr` | trace operator |
| `\dd` | upright `d` (for differentials) |

Plus every command in the [KaTeX support table](https://katex.org/docs/support_table):  
`\partial`, `\nabla`, `\psi`, `\phi`, `\Psi`, `\Phi`, `\mathcal{}`,  
`\hbar`, `\varepsilon`, `\otimes`, `\oplus`, `\dagger`, `\infty`, etc.

---

## Stack

- **[KaTeX](https://katex.org/) v0.16.9** — math rendering (loaded from jsDelivr CDN)
- **[marked.js](https://marked.js.org/) v12** — Markdown parsing (loaded from jsDelivr CDN)
- Pure HTML/CSS/JS — zero build tooling

---

## Offline use

The tool requires CDN access for KaTeX and marked.  
To use offline, download the CDN assets and update the `<link>` / `<script>` `src` attributes to local paths.

```
https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css
https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js
https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js
https://cdn.jsdelivr.net/npm/marked@12.0.0/marked.min.js
```
