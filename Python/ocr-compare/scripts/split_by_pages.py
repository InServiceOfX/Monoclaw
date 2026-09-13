#!/usr/bin/env python3
"""Split a page-accurate book into chapters by PDF page range.

The sibling `split_by_toc.py` finds chapter boundaries by matching heading text
in a flat markdown blob, which is the only option when the output has no page
structure. When `assemble_book.py` has produced `pages/page-NNNN.md`, the
boundaries are already known exactly from `toc.json`: a chapter runs from its
own first PDF page to the page before the next chapter's. That is exact rather
than heuristic, and it cannot silently swallow a chapter whose heading OCR'd
imperfectly.

Front matter (everything before the first chapter) and back matter are kept as
their own parts, so every page of the book lands in exactly one file.

Usage:
    split_by_pages.py SLUG_DIR [--pages-dir pages] [--out chapters]
Requires SLUG_DIR/toc.json (from build_page_map.py).
"""

import argparse
import json
import os
import re
import sys


def slugify(text, limit=60):
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)[:limit].rstrip("-") or "section"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug_dir")
    parser.add_argument("--pages-dir", default="pages")
    parser.add_argument("--out", default="chapters")
    args = parser.parse_args()

    toc = json.load(open(os.path.join(args.slug_dir, "toc.json")))
    pages_dir = os.path.join(args.slug_dir, args.pages_dir)
    out_dir = os.path.join(args.slug_dir, args.out)
    os.makedirs(out_dir, exist_ok=True)
    for name in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, name))

    page_files = sorted(f for f in os.listdir(pages_dir) if f.endswith(".md"))
    if not page_files:
        sys.exit(f"no page files in {pages_dir}")
    numbers = [int(re.search(r"(\d+)", f).group(1)) for f in page_files]
    first_page, last_page = min(numbers), max(numbers)

    def read_pages(start, end):
        chunks = []
        for page in range(start, end + 1):
            path = os.path.join(pages_dir, f"page-{page:04d}.md")
            if os.path.exists(path):
                chunks.append(open(path).read().rstrip())
        return "\n\n".join(chunks) + "\n"

    # Only the top-level divisions start a file; parts label the chapter after
    # them rather than becoming a part of their own.
    starts = [e for e in toc
              if e.get("kind") in ("chapter", "appendix", "backmatter") and e.get("pdf_page")]
    starts.sort(key=lambda e: e["pdf_page"])

    parts = []
    if starts and starts[0]["pdf_page"] > first_page:
        parts.append(("000-front-matter", "Front matter",
                      first_page, starts[0]["pdf_page"] - 1))
    for index, entry in enumerate(starts):
        end = (starts[index + 1]["pdf_page"] - 1
               if index + 1 < len(starts) else last_page)
        if entry["kind"] == "chapter":
            label = f"Chapter {entry['number']}. {entry['title']}"
            name = f"{index + 1:03d}-{slugify(entry['number'] + '-' + entry['title'])}"
        elif entry["kind"] == "appendix":
            label = f"Appendix {entry['number']}. {entry['title']}"
            name = f"{index + 1:03d}-appendix-{slugify(entry['number'] + '-' + entry['title'])}"
        else:
            label = entry["title"]
            name = f"{index + 1:03d}-{slugify(entry['title'])}"
        parts.append((name, label, entry["pdf_page"], end))

    index_rows = []
    for name, label, start, end in parts:
        text = read_pages(start, end)
        header = (f"# {label}\n\n"
                  f"*PDF pages {start}–{end}*\n\n---\n\n")
        with open(os.path.join(out_dir, name + ".md"), "w") as f:
            f.write(header + text)
        index_rows.append({
            "file": name + ".md", "title": label,
            "pdf_from": start, "pdf_to": end,
            "pages": end - start + 1, "words": len(text.split()),
        })

    with open(os.path.join(out_dir, "INDEX.md"), "w") as f:
        f.write(f"# Chapter index\n\nSplit by PDF page range from `toc.json` "
                f"({len(parts)} parts, pages {first_page}–{last_page}).\n\n")
        f.write("| File | Part | PDF pages | Words |\n|---|---|---|---:|\n")
        for row in index_rows:
            f.write(f"| `{row['file']}` | {row['title'][:80]} | "
                    f"{row['pdf_from']}–{row['pdf_to']} | {row['words']:,} |\n")
    json.dump(index_rows, open(os.path.join(out_dir, "index.json"), "w"), indent=2)

    covered = sum(row["pages"] for row in index_rows)
    print(f"{len(parts)} parts, {covered} of {last_page - first_page + 1} pages covered")
    for row in index_rows:
        print(f"  {row['words']:>7,}  p{row['pdf_from']}-{row['pdf_to']}  {row['title'][:60]}")


if __name__ == "__main__":
    main()
