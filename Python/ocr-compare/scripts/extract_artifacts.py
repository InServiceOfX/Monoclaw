#!/usr/bin/env python3
"""Inventory the equations, tables and figures in marker_book.py JSON output.

The point is to make a scanned textbook *queryable*. Marker's block tree already
labels every region; this walks it and emits one record per artifact, carrying
the page it sits on, the book's own number for it (Eq. 4.7a, Fig. 4.10,
Table 5.2 -- parsed from LaTeX \\tag{} and from caption text), and the content
in a form you can use directly:

    equations.json / .md / .tex     LaTeX, with the book's equation tag
    tables.json / .md, tables/*.csv Markdown, HTML and CSV per table
    figures.json / figures.md       Caption + the extracted image filename
    artifacts_summary.md            counts, and what looks suspect

Figures and tables come out of Marker as *groups* (FigureGroup wraps a Figure
and its Caption), so captions are matched by group membership first and by
nearest-caption-on-the-page only as a fallback.

Usage:
    extract_artifacts.py MARKERDIR OUTDIR [--page-map page_map.json]
"""

import argparse
import csv
import glob
import html as html_module
import json
import os
import re

from textnorm import normalize

TAG = re.compile(r"\\tag\{([^}]*)\}")
# Marker tags most numbered equations, but on some pages the book's number
# survives only as trailing plain text -- "... = 0. (4.6)". Anchored to the end
# and shaped chapter.number so it cannot eat a genuine trailing parenthetical.
TRAILING_NUMBER = re.compile(
    r"(?:\\qquad|\\quad|\\,|\\;|\s)*\(\s*([0-9]{1,2}\.[0-9]{1,3}[a-z]?)\s*\)\s*$")
FIGURE_LABEL = re.compile(r"\b(?:FIGURE|Figure|FIG\.?)\s*([0-9]+[.\-][0-9]+[a-z]?)", re.I)
TABLE_LABEL = re.compile(r"\bTABLE\s*([0-9]+[.\-][0-9]+[a-z]?)", re.I)


def strip_html(raw):
    text = re.sub(r"<br\s*/?>", " ", raw or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_module.unescape(text)
    return normalize(re.sub(r"\s+", " ", text).strip())


def html_table_to_grid(raw):
    """Minimal HTML table -> list of rows. Marker emits clean <table><tr><td>."""
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", raw or "", re.S | re.I)
    grid = []
    for row in rows:
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S | re.I)
        grid.append([strip_html(c) for c in cells])
    if not grid:
        return []
    width = max(len(r) for r in grid)
    return [r + [""] * (width - len(r)) for r in grid]


def grid_to_markdown(grid):
    if not grid:
        return ""
    escaped = [[c.replace("|", r"\|") for c in row] for row in grid]
    lines = ["| " + " | ".join(escaped[0]) + " |",
             "| " + " | ".join(["---"] * len(escaped[0])) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in escaped[1:]]
    return "\n".join(lines)


def iter_pages(marker_dir):
    for path in sorted(glob.glob(os.path.join(marker_dir, "chunks", "json", "*.json"))):
        for page in json.load(open(path)).get("children", []):
            match = re.search(r"/page/(\d+)/", page["id"])
            if match:
                yield int(match.group(1)), page


def flatten(block, out):
    out.append(block)
    for child in block.get("children") or []:
        flatten(child, out)


def caption_in_group(group):
    for child in group.get("children") or []:
        if child["block_type"] == "Caption":
            return strip_html(child["html"])
    return ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("marker_dir")
    parser.add_argument("out_dir")
    parser.add_argument("--page-map", default=None)
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    printed = {}
    if args.page_map:
        raw = json.load(open(args.page_map))
        printed = {int(k): v for k, v in raw.get("printed_by_pdf_page", {}).items()}

    equations, tables, figures = [], [], []

    for page_id, page in iter_pages(args.marker_dir):
        pdf_page = page_id + 1
        folio = printed.get(pdf_page)
        blocks = []
        flatten(page, blocks)

        # Captions on this page, in reading order, for the fallback match.
        page_captions = [strip_html(b["html"]) for b in blocks
                         if b["block_type"] == "Caption"]
        claimed = set()

        for block in blocks:
            kind = block["block_type"]
            common = {"pdf_page": pdf_page, "printed_page": folio, "id": block["id"]}

            if kind == "Equation":
                latex = strip_html(block["html"])
                tag = TAG.search(latex)
                latex = TAG.sub("", latex).strip()
                number = tag.group(1).strip() if tag else None
                if number is None:
                    trailing = TRAILING_NUMBER.search(latex)
                    if trailing:
                        number = trailing.group(1)
                        latex = latex[:trailing.start()].strip()
                equations.append({**common, "number": number, "latex": latex})

            elif kind == "Table":
                caption = ""
                for group in blocks:
                    if group["block_type"] == "TableGroup" and \
                            any(c["id"] == block["id"] for c in group.get("children") or []):
                        caption = caption_in_group(group)
                        break
                if not caption:
                    for candidate in page_captions:
                        if candidate not in claimed and TABLE_LABEL.search(candidate):
                            caption, _ = candidate, claimed.add(candidate)
                            break
                label = TABLE_LABEL.search(caption)
                grid = html_table_to_grid(block["html"])
                tables.append({
                    **common,
                    "number": label.group(1) if label else None,
                    "caption": caption,
                    "rows": grid,
                    "markdown": grid_to_markdown(grid),
                    "html": block["html"],
                })

            elif kind in ("Figure", "Picture"):
                caption = ""
                for group in blocks:
                    if group["block_type"] in ("FigureGroup", "PictureGroup") and \
                            any(c["id"] == block["id"] for c in group.get("children") or []):
                        caption = caption_in_group(group)
                        break
                if not caption:
                    for candidate in page_captions:
                        if candidate not in claimed and FIGURE_LABEL.search(candidate):
                            caption, _ = candidate, claimed.add(candidate)
                            break
                label = FIGURE_LABEL.search(caption)
                names = block.get("image_names") or []
                figures.append({
                    **common,
                    "kind": kind,
                    "number": label.group(1) if label else None,
                    "caption": caption,
                    # Marker names crops after the block path: /page/119/Figure/11
                    "image": f"_page_{page_id}_{kind}_{block['id'].rsplit('/', 1)[-1]}.jpeg"
                    if not names else
                    "_page_" + names[0].strip("/").replace("page/", "").replace("/", "_") + ".jpeg",
                })

    def dump(name, rows):
        with open(os.path.join(args.out_dir, f"{name}.json"), "w") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)

    with open(os.path.join(args.out_dir, "equations.md"), "w") as f:
        f.write("# Equations\n\nEvery display equation Marker found, in book order. "
                "`number` is the book's own equation tag where it printed one.\n\n")
        for eq in equations:
            head = f"Eq. ({eq['number']})" if eq["number"] else "(untagged)"
            page = f"printed p. {eq['printed_page']}" if eq["printed_page"] else \
                   f"pdf p. {eq['pdf_page']}"
            f.write(f"### {head} — {page}\n\n$$\n{eq['latex']}\n$$\n\n")

    # One CSV per table, so a data table can be loaded without parsing markdown.
    csv_dir = os.path.join(args.out_dir, "tables")
    os.makedirs(csv_dir, exist_ok=True)
    for name in os.listdir(csv_dir):
        os.remove(os.path.join(csv_dir, name))
    for position, table in enumerate(tables, 1):
        if not table["rows"]:
            continue
        stem = (f"table-{table['number'].replace('.', '_')}"
                if table["number"] else f"table-p{table['pdf_page']:04d}")
        path = os.path.join(csv_dir, f"{position:03d}-{stem}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(table["rows"])
        table["csv"] = os.path.relpath(path, args.out_dir)

    with open(os.path.join(args.out_dir, "equations.tex"), "w") as f:
        f.write("% Every display equation, in book order, with the book's own\n"
                "% number restored as \\tag where it printed one.\n")
        for eq in equations:
            page = (f"printed p. {eq['printed_page']}" if eq["printed_page"]
                    else f"pdf p. {eq['pdf_page']}")
            f.write(f"\n% {page}\n\\begin{{equation}}\n{eq['latex']}\n")
            if eq["number"]:
                f.write(f"\\tag{{{eq['number']}}}\n")
            f.write("\\end{equation}\n")

    with open(os.path.join(args.out_dir, "tables.md"), "w") as f:
        f.write("# Tables\n\n")
        for table in tables:
            head = f"Table {table['number']}" if table["number"] else "Table (unnumbered)"
            page = f"printed p. {table['printed_page']}" if table["printed_page"] else \
                   f"pdf p. {table['pdf_page']}"
            f.write(f"### {head} — {page}\n\n")
            if table["caption"]:
                f.write(f"*{table['caption']}*\n\n")
            f.write((table["markdown"] or "_(table structure not recovered)_") + "\n\n")
            if table.get("csv"):
                f.write(f"`{table['csv']}`\n\n")

    with open(os.path.join(args.out_dir, "figures.md"), "w") as f:
        f.write("# Figures\n\n")
        for figure in figures:
            head = f"Figure {figure['number']}" if figure["number"] else \
                   f"{figure['kind']} (unnumbered)"
            page = f"printed p. {figure['printed_page']}" if figure["printed_page"] else \
                   f"pdf p. {figure['pdf_page']}"
            f.write(f"### {head} — {page}\n\n![{head}](../images/{figure['image']})\n\n")
            if figure["caption"]:
                f.write(f"*{figure['caption']}*\n\n")

    # Dumped last so each table record carries the CSV path written above.
    dump("equations", equations)
    dump("tables", tables)
    dump("figures", figures)

    tagged = sum(1 for e in equations if e["number"])
    with open(os.path.join(args.out_dir, "artifacts_summary.md"), "w") as f:
        f.write("# Artifact inventory\n\n")
        f.write(f"- **Equations**: {len(equations)} ({tagged} carry the book's own number)\n")
        f.write(f"- **Tables**: {len(tables)} "
                f"({sum(1 for t in tables if t['number'])} numbered, "
                f"{sum(1 for t in tables if t['markdown'])} with recovered structure)\n")
        f.write(f"- **Figures**: {len(figures)} "
                f"({sum(1 for x in figures if x['number'])} numbered)\n")

    print(f"equations={len(equations)} (tagged {tagged}) "
          f"tables={len(tables)} figures={len(figures)} -> {args.out_dir}")


if __name__ == "__main__":
    main()
