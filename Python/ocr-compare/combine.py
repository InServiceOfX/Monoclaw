#!/usr/bin/env python3
"""
Reconcile Nougat + Marker OCR outputs of the same PDF into one source of truth.

Strategy (based on their complementary failure modes):
  - Marker = structural backbone: complete page coverage, all prose, never drops pages.
  - Nougat = equation authority: cleaner LaTeX + better indices on arXiv-style math,
    BUT it drops pages and repeats equations -> we detect & quarantine those.
  - We align equations by their \\tag{N} number, classify each as
    AGREE / CONFLICT / MARKER-ONLY (nougat dropped) / NOUGAT-ONLY, and emit:
      * reconciliation_report.md   (human/agent-readable findings)
      * equations.json             (machine-readable, for AI agents)
      * merged.md                  (Marker backbone + inline conflict flags)

Pure stdlib. Usage:
    python3 combine.py nougat_out/sample.mmd marker_out/sample/sample.md outdir/
"""
import sys, re, json, os
from collections import defaultdict, Counter

# Equation numbers come in several flavors:
#   - arXiv preprints: flat integers, e.g. \tag{12}              -> "12"
#   - textbooks (e.g. Srednicki QFT): chapter.eq, \tag{2.1}      -> "2.1"
#   - textbooks (e.g. Sidi Spacecraft): chapter.section.eq, \tag{2.1.2} -> "2.1.2"
# This capture group accepts all three (up to 3 dotted parts); _tagkey sorts them.
_TAG = r"([0-9]+(?:\.[0-9]+){0,2})"

def _tagkey(t):
    """Sort key so '1.2' < '1.10' < '2.1' and bare ints still order naturally."""
    return tuple(int(p) for p in str(t).split("."))

# ---------- equation extraction ----------

# Presentation-only macros: spelling differs between Nougat and Marker for the
# SAME printed glyph, so they must not count as conflicts. Deleted whole-token
# (the negative lookahead stops \big eating \bigcup, \it eating \item, etc.).
_DROP_MACROS = (
    "biggl|biggr|Biggl|Biggr|bigl|bigr|Bigl|Bigr|bigg|Bigg|big|Big|left|right|"
    "mathcal|mathrm|mathbf|mathsf|mathbb|mathit|mathfrak|boldsymbol|operatorname|"
    "displaystyle|scriptstyle|textstyle|limits|nolimits|"
    "textrm|textbf|textit|texttt|text|cal|rm|bf|sf|it|tt|"
    "quad|qquad|notag|nonumber|stackrel|overset|underset|"
    # fraction spelling: Nougat emits plain-TeX {a\over b}, Marker emits \frac{a}{b};
    # deleting the macro (braces already gone) reduces both to "a b".
    "frac|over|atop|"
    # font sizes
    "mbox|tiny|small|footnotesize|scriptsize|normalsize|large|Large|LARGE|huge|Huge"
)

def _norm(latex: str) -> str:
    """Canonicalize LaTeX so only *semantic* differences (symbols, indices,
    operators) count as conflicts — font/sizing/spacing/punctuation do not."""
    s = latex
    s = re.sub(r"\\tag\{[^}]*\}", "", s)                 # \tag{N} / \tag{N.M}
    s = re.sub(r"\(\d+(?:\.\d+){0,2}\)\s*$", "", s)      # trailing (N) / (N.M) / (N.M.K)
    s = re.sub(r"\\(?:phantom|hspace|vspace|label|qquad)\{[^}]*\}", "", s)
    s = re.sub(r"\\[dtc]frac", r"\\frac", s)             # tfrac/dfrac/cfrac -> frac
    s = re.sub(r"\\(?:cdots|ldots|dotsb|dotsc|dotsm|dotsi)", r"\\dots", s)  # all ellipses
    # matrix scaffolding: \begin{pmatrix}/\begin{array}{cc}/\pmatrix all -> gone,
    # so a column vector reads the same whichever engine emitted it.
    s = re.sub(r"\\begin\{[a-zA-Z*]+\}(?:\{[^}]*\})?", "", s)
    s = re.sub(r"\\end\{[a-zA-Z*]+\}", "", s)
    s = re.sub(r"\\(?:cr|\\)(?![a-zA-Z])", "", s)        # row separators \cr and \\
    s = s.replace("&", "")                               # column alignment
    s = re.sub(r"\\(?:" + _DROP_MACROS + r")(?![a-zA-Z])", "", s)
    s = re.sub(r"\\(?:longrightarrow|Longrightarrow|rightarrow|Rightarrow|to|mapsto)(?![a-zA-Z])",
               r"\\to", s)                               # all right-arrows -> \to
    s = re.sub(r"\\(?:geq|leq|neq)\b", lambda m: "\\" + m.group(0)[1:3], s)  # \geq->\ge \leq->\le \neq->\ne
    s = s.replace("\\prime", "'")                        # \prime == '
    s = s.replace("$", "")                               # stray inline-math $ Nougat emits in display
    s = re.sub(r"\\[,;:!>< ]", "", s)                    # thin/med/neg spaces (\, \; \! ...)
    s = s.replace("{", "").replace("}", "")              # ignore all grouping braces
    s = s.replace("^'", "'")                             # superscript-prime x^{\prime} == x'
    s = re.sub(r"_+", "_", s)                             # {}_ empty-group spacers: 1__S -> 1_S
    s = re.sub(r"\^+", "^", s)
    s = re.sub(r"\s+", "", s)                             # all whitespace
    s = re.sub(r"\\+$", "", s)                            # trailing line-break backslashes
    s = re.sub(r"[.,;]+$", "", s)                         # trailing punctuation (., ;)
    return s

def extract_nougat(text):
    """Nougat: display math in \\[ ... \\], eq number as \\tag{N} or \\tag{N.M}."""
    eqs = []
    for m in re.finditer(r"\\\[(.*?)\\\]", text, re.DOTALL):
        body = m.group(1)
        # a single \[...\] may hold several \tag-separated equations
        for t in re.finditer(r"\\tag\{" + _TAG + r"\}", body):
            eqs.append((t.group(1), body.strip()))
        if not re.search(r"\\tag\{" + _TAG + r"\}", body):
            eqs.append((None, body.strip()))
    return eqs

def extract_marker(text):
    """Marker: display math in $$ ... $$. The equation number may be a \\tag{N[.M]}
    or a bare (N[.M]) INSIDE the block, or — commonly for textbooks — on the very
    next line just AFTER the closing $$. We check all three."""
    eqs = []
    after_label = re.compile(r"\A\s*\(" + _TAG + r"\)")   # label on the line after $$...$$
    for m in re.finditer(r"\$\$(.*?)\$\$", text, re.DOTALL):
        body = m.group(1).strip()
        tagm = (re.search(r"\\tag\{" + _TAG + r"\}", body)
                or re.search(r"\(" + _TAG + r"\)\s*$", body))
        if tagm:
            eqs.append((tagm.group(1), body))
            continue
        nxt = after_label.match(text[m.end():m.end() + 24])
        eqs.append((nxt.group(1) if nxt else None, body))
    return eqs

# ---------- reconciliation ----------

def reconcile(nougat_eqs, marker_eqs):
    n_by_tag = defaultdict(list)
    for tag, body in nougat_eqs:
        if tag: n_by_tag[tag].append(body)
    m_by_tag = defaultdict(list)
    for tag, body in marker_eqs:
        if tag: m_by_tag[tag].append(body)

    # Nougat repetition artifacts (same tag emitted multiple times)
    n_repeats = {t: c for t, c in Counter(
        t for t, _ in nougat_eqs if t).items() if c > 1}

    all_tags = sorted(set(n_by_tag) | set(m_by_tag), key=_tagkey)
    rows = []
    for tag in all_tags:
        n = n_by_tag.get(tag, [None])[0]
        m = m_by_tag.get(tag, [None])[0]
        if n and m:
            status = "agree" if _norm(n) == _norm(m) else "conflict"
        elif m and not n:
            status = "marker_only"   # nougat dropped/skipped this region
        elif n and not m:
            status = "nougat_only"
        else:
            status = "empty"
        rows.append({"tag": tag, "status": status, "nougat": n, "marker": m,
                     "nougat_repeated": n_repeats.get(tag, 0)})

    # Missing equation numbers in Nougat's sequence => likely dropped page(s).
    # For textbook tags we look for gaps WITHIN each chapter (the part before the
    # dot); flat-integer tags are treated as one chapter. Returns formatted
    # strings like "2.5-2.7" / "41".
    gaps = _gaps(n_by_tag.keys())
    return rows, n_repeats, gaps


def _gaps(tags):
    """Missing integers within the observed range, grouped per chapter prefix."""
    by_ch = defaultdict(set)
    for t in tags:
        parts = str(t).split(".")
        if len(parts) == 2:
            by_ch[parts[0]].add(int(parts[1]))
        else:
            by_ch[None].add(int(parts[0]))
    out = []
    for ch in sorted(by_ch, key=lambda c: (c is not None, c if c is None else int(c))):
        nums = sorted(by_ch[ch])
        missing = sorted(set(range(nums[0], nums[-1] + 1)) - set(nums))
        runs = []
        for v in missing:
            if runs and v == runs[-1][1] + 1:
                runs[-1][1] = v
            else:
                runs.append([v, v])
        pre = "" if ch is None else f"{ch}."
        for a, b in runs:
            out.append(f"{pre}{a}" if a == b else f"{pre}{a}-{pre}{b}")
    return out

# ---------- outputs ----------

def write_report(rows, n_repeats, gaps, marker_eqs, nougat_eqs, out):
    agree = [r for r in rows if r["status"] == "agree"]
    conflict = [r for r in rows if r["status"] == "conflict"]
    marker_only = [r for r in rows if r["status"] == "marker_only"]
    nougat_only = [r for r in rows if r["status"] == "nougat_only"]
    L = []
    L.append("# OCR Reconciliation Report\n")
    L.append(f"- Nougat equations (tagged): {sum(1 for t,_ in nougat_eqs if t)}")
    L.append(f"- Marker equations (tagged): {sum(1 for t,_ in marker_eqs if t)}")
    L.append(f"- **Agree (both match): {len(agree)}**")
    L.append(f"- **Conflict (need review): {len(conflict)}**")
    L.append(f"- Marker-only (Nougat dropped): {len(marker_only)}")
    L.append(f"- Nougat-only (Marker missed numbering): {len(nougat_only)}")
    if gaps:
        L.append(f"- ⚠️ **Nougat tag-sequence gaps (likely dropped pages): {', '.join(gaps)}**")
    if n_repeats:
        r = ", ".join(f"({t})×{c}" for t,c in sorted(n_repeats.items(), key=lambda x:_tagkey(x[0])))
        L.append(f"- ⚠️ **Nougat repeated equations: {r}**")
    L.append("\n## Conflicts to resolve (check against the PDF)\n")
    for r in conflict:
        L.append(f"### eq ({r['tag']})")
        L.append(f"- **nougat:** `{r['nougat']}`")
        L.append(f"- **marker:** `{r['marker']}`\n")
    L.append("\n## Marker-only equations (Nougat lost these)\n")
    for r in marker_only:
        L.append(f"- ({r['tag']}) `{r['marker']}`")
    with open(out, "w") as f:
        f.write("\n".join(L))

def write_json(rows, n_repeats, gaps, out):
    obj = {
        "summary": {
            "agree": sum(1 for r in rows if r["status"]=="agree"),
            "conflict": sum(1 for r in rows if r["status"]=="conflict"),
            "marker_only": sum(1 for r in rows if r["status"]=="marker_only"),
            "nougat_only": sum(1 for r in rows if r["status"]=="nougat_only"),
            "nougat_dropped_ranges": gaps,
            "nougat_repeated": n_repeats,
        },
        "equations": rows,
    }
    with open(out, "w") as f:
        json.dump(obj, f, indent=2)

def write_merged(marker_text, rows, gaps, n_repeats, out):
    """Marker backbone + inline review flags where Nougat disagrees / Nougat lost content."""
    by_tag = {r["tag"]: r for r in rows}
    header = ["<!-- MERGED SOURCE OF TRUTH (Marker backbone + Nougat equation overlay) -->",
              "<!-- Generated by combine.py. ✓=both agree, ⚠=conflict (verify vs PDF). -->"]
    if gaps:
        header.append(f"<!-- NOTE: Nougat dropped eq range(s) {', '.join(gaps)}; those equations come from Marker only. -->")
    if n_repeats:
        header.append(f"<!-- NOTE: Nougat repeated eqs {dict(n_repeats)} (deduped, ignored here). -->")

    def annotate(m):
        body = m.group(1)
        tagm = re.search(r"\\tag\{" + _TAG + r"\}", body) or re.search(r"\(" + _TAG + r"\)\s*$", body)
        if not tagm:
            return m.group(0)
        row = by_tag.get(tagm.group(1))
        if not row:
            return m.group(0)
        if row["status"] == "agree":
            flag = f"\n<!-- eq ({row['tag']}) ✓ nougat+marker agree -->"
        elif row["status"] == "conflict":
            flag = (f"\n<!-- eq ({row['tag']}) ⚠ CONFLICT — verify vs PDF."
                    f"\n     nougat: {row['nougat']}"
                    f"\n     marker: {row['marker']} -->")
        elif row["status"] == "marker_only":
            flag = f"\n<!-- eq ({row['tag']}) ⚠ MARKER-ONLY (Nougat dropped this) -->"
        else:
            flag = ""
        return m.group(0) + flag

    merged = re.sub(r"\$\$(.*?)\$\$", annotate, marker_text, flags=re.DOTALL)
    with open(out, "w") as f:
        f.write("\n".join(header) + "\n\n" + merged)


def main():
    nougat_path, marker_path, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    nougat_text = open(nougat_path).read()
    marker_text = open(marker_path).read()
    nougat_eqs = extract_nougat(nougat_text)
    marker_eqs = extract_marker(marker_text)
    rows, n_repeats, gaps = reconcile(nougat_eqs, marker_eqs)
    write_report(rows, n_repeats, gaps, marker_eqs, nougat_eqs, os.path.join(outdir, "reconciliation_report.md"))
    write_json(rows, n_repeats, gaps, os.path.join(outdir, "equations.json"))
    write_merged(marker_text, rows, gaps, n_repeats, os.path.join(outdir, "merged.md"))
    print(f"Wrote reconciliation_report.md, equations.json, merged.md to {outdir}/")
    print(f"  agree={sum(1 for r in rows if r['status']=='agree')}  "
          f"conflict={sum(1 for r in rows if r['status']=='conflict')}  "
          f"marker_only={sum(1 for r in rows if r['status']=='marker_only')}  "
          f"nougat_only={sum(1 for r in rows if r['status']=='nougat_only')}")
if __name__ == "__main__":
    main()
