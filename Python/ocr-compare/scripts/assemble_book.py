#!/usr/bin/env python3
"""Assemble marker_book.py chunk output into per-page files and one book.md.

marker_book.py writes overlapping-free chunks of paginated markdown. This turns
them into the two shapes a reader actually wants:

    pages/page-0120.md   one file per PDF page, named by 1-BASED PDF page
    book.md              the whole book, with an HTML anchor before each page

and an index (page_index.json) recording, per page, the character count and the
block-type census, so gaps and OCR misses are obvious without opening anything.

Page numbering, stated once because it is the easy thing to get wrong:
  * Marker's `{K}` separator carries a 0-BASED PDF page index.
  * Filenames and anchors use 1-BASED PDF pages (what a PDF viewer shows).
  * The book's own PRINTED folio is a third number, resolved separately by
    build_page_map.py and injected here when --page-map is supplied.

Usage:
    assemble_book.py MARKERDIR OUTDIR [--page-map page_map.json]
"""

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter

from textnorm import count_homoglyphs, normalize

PAGE_MARKER = re.compile(r"\{(\d+)\}-{10,}\s*")
IMAGE_REF = re.compile(r"!\[\]\(([^)]+)\)")


def load_chunk_pages(marker_dir):
    """chunk markdown -> {0-based pdf page: markdown text}, plus repair count."""
    pages = {}
    duplicates = []
    repaired = 0
    for path in sorted(glob.glob(os.path.join(marker_dir, "chunks", "md", "*.md"))):
        text = open(path).read()
        hits = list(PAGE_MARKER.finditer(text))
        if not hits:
            continue
        for index, match in enumerate(hits):
            page_id = int(match.group(1))
            start = match.end()
            end = hits[index + 1].start() if index + 1 < len(hits) else len(text)
            raw = text[start:end].strip()
            repaired += count_homoglyphs(raw)
            body = normalize(raw)
            if page_id in pages and pages[page_id] != body:
                duplicates.append(page_id)
            pages[page_id] = body
    return pages, duplicates, repaired


def load_block_census(marker_dir):
    """chunk json -> {0-based pdf page: Counter(block_type)}."""
    census = {}
    for path in sorted(glob.glob(os.path.join(marker_dir, "chunks", "json", "*.json"))):
        data = json.load(open(path))
        for page in data.get("children", []):
            match = re.search(r"/page/(\d+)/", page["id"])
            if not match:
                continue
            counter = Counter()

            def walk(block):
                counter[block["block_type"]] += 1
                for child in block.get("children") or []:
                    walk(child)

            walk(page)
            del counter["Page"]
            census[int(match.group(1))] = counter
    return census


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("marker_dir")
    parser.add_argument("out_dir")
    parser.add_argument("--page-map", default=None,
                        help="page_map.json giving printed folios per 1-based PDF page")
    parser.add_argument("--image-prefix", default="images/",
                        help="path prefix rewritten into image refs in book.md")
    args = parser.parse_args()

    pages, duplicates, repaired = load_chunk_pages(args.marker_dir)
    if not pages:
        sys.exit(f"no paginated markdown found under {args.marker_dir}/chunks/md")
    census = load_block_census(args.marker_dir)

    printed = {}
    if args.page_map:
        raw = json.load(open(args.page_map))
        printed = {int(k): v for k, v in raw.get("printed_by_pdf_page", {}).items()}

    pages_dir = os.path.join(args.out_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)

    lowest, highest = min(pages), max(pages)
    missing = [p for p in range(lowest, highest + 1) if p not in pages]

    index = []
    body_parts = []
    for page_id in range(lowest, highest + 1):
        pdf_page = page_id + 1
        text = pages.get(page_id, "")
        folio = printed.get(pdf_page)

        header = f"pdf page {pdf_page}"
        if folio is not None:
            header += f" | printed page {folio}"
        with open(os.path.join(pages_dir, f"page-{pdf_page:04d}.md"), "w") as f:
            f.write(f"<!-- {header} -->\n\n{text}\n")

        body_parts.append(f'\n\n<a id="pdf-page-{pdf_page}"></a>\n<!-- {header} -->\n\n{text}')
        index.append({
            "pdf_page": pdf_page,
            "marker_page_id": page_id,
            "printed_page": folio,
            "chars": len(text),
            "blocks": dict(census.get(page_id, {})),
        })

    book = "".join(body_parts).strip() + "\n"
    book = IMAGE_REF.sub(
        lambda m: f"![]({args.image_prefix}{os.path.basename(m.group(1))})", book)
    with open(os.path.join(args.out_dir, "book.md"), "w") as f:
        f.write(book)
    with open(os.path.join(args.out_dir, "page_index.json"), "w") as f:
        json.dump({
            "pdf_pages": highest - lowest + 1,
            "missing_pdf_pages": [p + 1 for p in missing],
            "duplicate_pdf_pages": sorted({p + 1 for p in duplicates}),
            "pages": index,
        }, f, indent=2)

    total_chars = sum(entry["chars"] for entry in index)
    thin = [e["pdf_page"] for e in index if e["chars"] < 200]
    print(f"pages {lowest + 1}-{highest + 1} ({len(index)}), {total_chars} chars")
    print(f"missing: {[p + 1 for p in missing] or 'none'}")
    print(f"duplicate-id pages: {sorted({p + 1 for p in duplicates}) or 'none'}")
    print(f"thin pages (<200 chars, likely plates/blanks): {len(thin)}")
    print(f"cyrillic homoglyphs repaired: {repaired}")
    print(f"-> {args.out_dir}/book.md, pages/, page_index.json")


if __name__ == "__main__":
    main()
