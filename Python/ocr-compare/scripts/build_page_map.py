#!/usr/bin/env python3
"""Turn a verified book_spec.json into a page map and a PDF-anchored TOC.

A scanned book has three page numberings (0-based marker id, 1-based PDF page,
and the folio actually printed on the paper). Readers cite the printed folio;
every tool here addresses the PDF page. This resolves between them from the
`folio_rules` in the spec, then anchors every TOC entry to a PDF page.

It also VERIFIES rather than trusts: each chapter's title is searched for near
its predicted PDF page in the OCR text, and any chapter whose heading is not
found where the offset says it should be is reported. That is what catches a
folio rule that is wrong, or off by a page, somewhere in the middle of a book.

Usage:
    build_page_map.py BOOK_SPEC.json OUT_DIR [--pages-dir DIR] [--window 2]
"""

import argparse
import json
import os
import re
import sys

ROMAN = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
         (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]


def to_roman(value):
    out = []
    for size, glyph in ROMAN:
        while value >= size:
            out.append(glyph)
            value -= size
    return "".join(out)


def printed_for(pdf_page, rules):
    for rule in rules["ranges"]:
        if rule["pdf_from"] <= pdf_page <= rule["pdf_to"]:
            number = pdf_page + rule["offset"]
            if number < 1:
                return None
            return to_roman(number) if rule["style"] == "roman" else number
    return None


def pdf_for_printed(printed, rules):
    for rule in rules["ranges"]:
        if rule["style"] != "arabic":
            continue
        candidate = printed - rule["offset"]
        if rule["pdf_from"] <= candidate <= rule["pdf_to"]:
            return candidate
    return None


def normalise(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec")
    parser.add_argument("out_dir")
    parser.add_argument("--pages-dir", default=None,
                        help="pages/ from assemble_book.py; enables verification")
    parser.add_argument("--window", type=int, default=2,
                        help="+/- PDF pages to search for a chapter heading")
    args = parser.parse_args()

    spec = json.load(open(args.spec))
    rules = spec["folio_rules"]
    os.makedirs(args.out_dir, exist_ok=True)

    printed_by_pdf_page = {}
    pdf_by_printed = {}
    for pdf_page in range(1, spec["pdf_pages"] + 1):
        folio = printed_for(pdf_page, rules)
        printed_by_pdf_page[pdf_page] = folio
        if isinstance(folio, int):
            pdf_by_printed[folio] = pdf_page

    # Anchor the TOC to PDF pages, and FLATTEN it: the corpus convention (and
    # what the ReadingRoom server reads) is a flat list of
    # {number, title, printed_page, pdf_page, depth, pdf_page_exact}. `kind` is
    # carried along as an extra key for the tools here that want it.
    DEPTH = {"part": 0, "chapter": 1, "appendix": 1, "backmatter": 1}
    toc = []
    for entry in spec["toc"]:
        pdf_page = (pdf_for_printed(entry["printed_page"], rules)
                    if entry.get("printed_page") else None)
        toc.append({
            "number": entry.get("number") or "",
            "title": entry["title"],
            "printed_page": entry.get("printed_page"),
            "pdf_page": pdf_page,
            "depth": DEPTH.get(entry["kind"], 1),
            "pdf_page_exact": pdf_page is not None,
            "kind": entry["kind"],
        })
        for section in entry.get("sections", []) or []:
            section_pdf = (pdf_for_printed(section["printed_page"], rules)
                           if section.get("printed_page") else None)
            toc.append({
                "number": section.get("number") or "",
                "title": section["title"],
                "printed_page": section.get("printed_page"),
                "pdf_page": section_pdf,
                "depth": 2,
                "pdf_page_exact": section_pdf is not None,
                "kind": "section",
                "parent": entry.get("number") or entry["title"],
            })

    # Verify chapter headings actually land where the offset predicts.
    checks = []
    if args.pages_dir:
        for entry in toc:
            if entry.get("kind") not in ("chapter", "appendix") or not entry["pdf_page"]:
                continue
            needle = normalise(entry["title"])[:40]
            found_at = None
            for offset in range(-args.window, args.window + 1):
                page = entry["pdf_page"] + offset
                path = os.path.join(args.pages_dir, f"page-{page:04d}.md")
                if os.path.exists(path) and needle in normalise(open(path).read()):
                    found_at = page
                    break
            checks.append({
                "kind": entry.get("kind"),
                "number": entry["number"],
                "title": entry["title"],
                "printed_page": entry["printed_page"],
                "predicted_pdf_page": entry["pdf_page"],
                "found_on_pdf_page": found_at,
                "ok": found_at == entry["pdf_page"],
            })

    with open(os.path.join(args.out_dir, "page_map.json"), "w") as f:
        json.dump({
            "slug": spec["slug"],
            "pdf_pages": spec["pdf_pages"],
            "folio_rules": rules,
            "printed_by_pdf_page": printed_by_pdf_page,
            "pdf_by_printed_page": pdf_by_printed,
        }, f, indent=2)

    # Flat list, matching the other slugs in the corpus.
    with open(os.path.join(args.out_dir, "toc.json"), "w") as f:
        json.dump(toc, f, indent=2)

    if checks:
        with open(os.path.join(args.out_dir, "page_map_verification.json"), "w") as f:
            json.dump(checks, f, indent=2)
        bad = [c for c in checks if not c["ok"]]
        print(f"verification: {len(checks) - len(bad)}/{len(checks)} chapter "
              f"headings found exactly where the folio rule predicts")
        for check in bad:
            print(f"  MISMATCH {check['kind']} {check['number']} "
                  f"'{check['title'][:45]}' predicted pdf {check['predicted_pdf_page']}, "
                  f"found {check['found_on_pdf_page']}")
    print(f"-> {args.out_dir}/page_map.json, toc.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
