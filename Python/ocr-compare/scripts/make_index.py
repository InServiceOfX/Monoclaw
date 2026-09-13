#!/usr/bin/env python3
"""Write the greppable INDEX.md for a parsed book slug.

One table row per table-of-contents entry: section number, title, the PRINTED
page a citation uses, and the PDF page to actually open. This is the file an
agent greps first, so it states the page-number rule at the top and never makes
the reader infer it.

Usage:
    make_index.py SLUG_DIR [--artifacts artifacts]
Requires SLUG_DIR/toc.json and SLUG_DIR/page_map.json (from build_page_map.py).
"""

import argparse
import json
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug_dir")
    parser.add_argument("--spec", default="book_spec.json")
    parser.add_argument("--artifacts", default="artifacts")
    args = parser.parse_args()

    toc = json.load(open(os.path.join(args.slug_dir, "toc.json")))
    page_map = json.load(open(os.path.join(args.slug_dir, "page_map.json")))
    spec_path = os.path.join(args.slug_dir, args.spec)
    spec = json.load(open(spec_path)) if os.path.exists(spec_path) else {}

    counts = {}
    for name in ("equations", "tables", "figures"):
        path = os.path.join(args.slug_dir, args.artifacts, f"{name}.json")
        if os.path.exists(path):
            counts[name] = len(json.load(open(path)))

    lines = []
    title = spec.get("title", os.path.basename(args.slug_dir.rstrip("/")))
    authors = ", ".join(spec.get("authors", [])) or ""
    lines.append(f"# {authors + ', ' if authors else ''}{title}"
                 f"{', ' + spec['edition'] if spec.get('edition') else ''}\n")
    lines.append(f"{spec.get('publisher', '')} {spec.get('year', '')}. "
                 f"{page_map['pdf_pages']} PDF pages. "
                 f"{spec.get('note', '')}\n")

    lines.append("## How to use this file\n")
    lines.append("Grep for a topic and you get the section number, the "
                 "**printed** page as cited in the book, and the **PDF** page "
                 "to open.\n")
    lines.append("```bash\ngrep -i 'boundary layer' INDEX.md\n"
                 "grep -E '^\\| 4\\.' INDEX.md    # everything in chapter 4\n```\n")

    lines.append("### The page-number rule\n")
    for rule in page_map["folio_rules"]["ranges"]:
        if rule["style"] == "roman":
            lines.append(f"- PDF pages {rule['pdf_from']}–{rule['pdf_to']}: front "
                         f"matter, roman folio equal to the PDF page.")
        else:
            sign = "+" if -rule["offset"] >= 0 else "-"
            lines.append(f"- PDF pages {rule['pdf_from']}–{rule['pdf_to']}: "
                         f"**PDF page = printed page {sign} {abs(rule['offset'])}**.")
    lines.append(f"\n`page_map.json` holds the exact mapping in both directions.\n")

    if counts:
        lines.append("### What else is in this directory\n")
        lines.append(f"- `book.md` — the whole book, one anchor per PDF page.")
        lines.append(f"- `pages/page-NNNN.md` — one file per PDF page.")
        lines.append(f"- `chapters/` — split by PDF page range; see its `INDEX.md`.")
        if "equations" in counts:
            lines.append(f"- `{args.artifacts}/equations.json|md` — "
                         f"{counts['equations']:,} display equations in LaTeX, "
                         f"carrying the book's own numbers.")
        if "tables" in counts:
            lines.append(f"- `{args.artifacts}/tables.json|md` — "
                         f"{counts['tables']:,} tables as Markdown and HTML.")
        if "figures" in counts:
            lines.append(f"- `{args.artifacts}/figures.json|md` — "
                         f"{counts['figures']:,} figures with captions; "
                         f"images in `images/`.")
        lines.append("")

    lines.append("## Contents\n")
    open_table = False
    for entry in toc:
        kind = entry.get("kind", "section")
        number, name = entry.get("number") or "", entry["title"]
        printed = entry["printed_page"] if entry["printed_page"] is not None else "?"
        pdf_page = entry["pdf_page"] if entry["pdf_page"] is not None else "?"

        if kind == "part":
            lines.append(f"\n### Part {number}. {name} "
                         f"(printed {printed}, pdf {pdf_page})\n")
            open_table = False
            continue

        if kind in ("chapter", "appendix", "backmatter"):
            heading = {"chapter": f"{number}. {name}",
                       "appendix": f"Appendix {number}. {name}"}.get(kind, name)
            label = {"chapter": number,
                     "appendix": f"App. {number}"}.get(kind, "—")
            lines.append(f"\n#### {heading}\n")
            lines.append("| § | Title | Printed | PDF |")
            lines.append("|---|-------|--------:|----:|")
            lines.append(f"| {label} | {name} | {printed} | {pdf_page} |")
            open_table = True
            continue

        if not open_table:      # a stray section with no chapter above it
            lines.append("| § | Title | Printed | PDF |")
            lines.append("|---|-------|--------:|----:|")
            open_table = True
        lines.append(f"| {number or '—'} | {name} | {printed} | {pdf_page} |")

    path = os.path.join(args.slug_dir, "INDEX.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"-> {path}")


if __name__ == "__main__":
    main()
