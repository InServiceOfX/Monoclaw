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

# ---------- equation extraction ----------

def _norm(latex: str) -> str:
    """Canonicalize LaTeX so cosmetic differences don't count as conflicts."""
    s = latex
    s = re.sub(r"\\tag\{[^}]*\}", "", s)            # drop the eq number
    s = re.sub(r"\((\d+)\)\s*$", "", s)             # drop trailing (N) number
    s = re.sub(r"\\(left|right|[Bb]igg?[lr]?|[Bb]ig[lr]?)", "", s)  # delimiter sizing
    s = re.sub(r"\\[,;:!> ]", "", s)                # thin/med spaces
    s = re.sub(r"\\quad|\\qquad|\\notag|\\nonumber|\\phantom\{[^}]*\}", "", s)
    s = s.replace("\\!", "")
    s = s.replace("\\rm", "").replace("\\mathrm", "").replace("\\operatorname", "")
    s = s.replace("\\text", "").replace("\\,", "")
    s = re.sub(r"\\(stackrel|overset)", "", s)      # both used for the eps->0 limit
    s = s.replace("{", "").replace("}", "")         # ignore all grouping braces
    s = re.sub(r"\s+", "", s)                        # all whitespace
    return s

def extract_nougat(text):
    """Nougat: display math in \\[ ... \\], eq number as \\tag{N}."""
    eqs = []
    for m in re.finditer(r"\\\[(.*?)\\\]", text, re.DOTALL):
        body = m.group(1)
        # a single \[...\] may hold several \tag-separated equations
        for t in re.finditer(r"\\tag\{(\d+)\}", body):
            eqs.append((t.group(1), body.strip()))
        if not re.search(r"\\tag\{\d+\}", body):
            eqs.append((None, body.strip()))
    return eqs

def extract_marker(text):
    """Marker: display math in $$ ... $$, number as \\tag{N} or trailing (N)."""
    eqs = []
    for m in re.finditer(r"\$\$(.*?)\$\$", text, re.DOTALL):
        body = m.group(1).strip()
        tagm = re.search(r"\\tag\{(\d+)\}", body)
        if tagm:
            eqs.append((tagm.group(1), body))
        else:
            trail = re.search(r"\((\d+)\)\s*$", body)
            eqs.append((trail.group(1) if trail else None, body))
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

    all_tags = sorted(set(n_by_tag) | set(m_by_tag), key=lambda x: int(x))
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

    # contiguous gaps in Nougat's tag sequence => likely dropped page(s)
    n_tags = sorted((int(t) for t in n_by_tag), )
    gaps = []
    if n_tags:
        full = set(range(n_tags[0], n_tags[-1] + 1))
        missing = sorted(full - set(n_tags))
        # group consecutive
        for i, v in enumerate(missing):
            if i == 0 or v != missing[i-1] + 1:
                gaps.append([v, v])
            else:
                gaps[-1][1] = v
    return rows, n_repeats, gaps

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
        g = ", ".join(f"{a}-{b}" if a!=b else str(a) for a,b in gaps)
        L.append(f"- ⚠️ **Nougat tag-sequence gaps (likely dropped pages): {g}**")
    if n_repeats:
        r = ", ".join(f"({t})×{c}" for t,c in sorted(n_repeats.items(), key=lambda x:int(x[0])))
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
        g = ", ".join(f"{a}-{b}" if a!=b else str(a) for a,b in gaps)
        header.append(f"<!-- NOTE: Nougat dropped eq range(s) {g}; those equations come from Marker only. -->")
    if n_repeats:
        header.append(f"<!-- NOTE: Nougat repeated eqs {dict(n_repeats)} (deduped, ignored here). -->")

    def annotate(m):
        body = m.group(1)
        tagm = re.search(r"\\tag\{(\d+)\}", body) or re.search(r"\((\d+)\)\s*$", body)
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
