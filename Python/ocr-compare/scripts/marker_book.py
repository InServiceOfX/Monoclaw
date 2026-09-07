#!/usr/bin/env python3
"""Run Marker over a LARGE, PAGE-ACCURATE book, keeping structure, not just text.

Why this exists (vs. marker_chunked.py): marker_chunked concatenates markdown
into one flat blob. For a *scanned* book with no text layer we need more:

  * page-accurate output  -- every PDF page is delimited, so printed page
    numbers can be mapped and figures/tables/equations can be cited by page;
  * the block tree        -- Marker's JSON renderer labels each block
    (Equation, Table, Figure, Caption, SectionHeader ...) with a bbox, which is
    what lets us inventory the math/tables/graphs afterwards;
  * extracted figure images -- the graphs in a scanned book only exist as
    pixels, so we crop and keep them;
  * resumability          -- a 766-page book is hours of GPU time, and a crash
    at page 700 must not throw away pages 0-699.

Models are loaded ONCE and the document is BUILT once per chunk, then rendered
twice (markdown + json) off that same Document, so the structured output costs
no extra GPU time.

Run with the MARKER venv's python (weights env vars come from _paths.sh):

    "$OCR_VENV_DIR/venv-marker/bin/python" scripts/marker_book.py IN.pdf OUTDIR

Layout produced under OUTDIR:
    chunks/md/00000-00031.md      paginated markdown per chunk
    chunks/json/00000-00031.json  Marker block tree per chunk
    images/<page>_<block>.png     extracted figures/pictures
    chunks/done/00000-00031.ok    resume sentinels
    marker_book.log               progress

Env knobs (all optional):
    MARKER_CHUNK=32            pages per chunk (lower = less peak RAM/VRAM)
    MARKER_REC_BATCH=16        recognition batch size (lower = less VRAM)
    MARKER_DET_BATCH=8         detection batch size
    MARKER_LAYOUT_BATCH=8      layout batch size
"""

import argparse
import gc
import json
import os
import sys
import time
import traceback

import pypdfium2 as pdfium
import torch

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser
from marker.renderers.markdown import MarkdownRenderer
from marker.renderers.json import JSONRenderer

PAGE_SEPARATOR = "-" * 48


def log(message, handle):
    line = f"[marker_book {time.strftime('%H:%M:%S')}] {message}"
    print(line, flush=True)
    handle.write(line + "\n")
    handle.flush()


def build_config(start, end):
    """Marker config for one page range.

    force_ocr is on because this driver targets scans: the PDF carries no text
    layer, and forcing OCR keeps behaviour identical on the odd page that does
    carry stray text (page numbers stamped by the scanner, say).
    paginate_output is what gives us the per-page delimiters.
    """
    return ConfigParser(
        {
            "page_range": f"{start}-{end}",
            "output_format": "markdown",
            "force_ocr": True,
            "paginate_output": True,
            "page_separator": PAGE_SEPARATOR,
            "recognition_batch_size": int(os.environ.get("MARKER_REC_BATCH", 16)),
            "detection_batch_size": int(os.environ.get("MARKER_DET_BATCH", 8)),
            "layout_batch_size": int(os.environ.get("MARKER_LAYOUT_BATCH", 8)),
            "ocr_error_batch_size": int(os.environ.get("MARKER_DET_BATCH", 8)),
            "table_rec_batch_size": 2,
        }
    ).generate_config_dict()


def save_images(images, images_dir, handle):
    """Persist Marker's extracted figure crops. Names are already page-scoped."""
    saved = 0
    for name, image in (images or {}).items():
        path = os.path.join(images_dir, os.path.basename(name))
        try:
            image.save(path)
            saved += 1
        except Exception as exc:  # a bad crop must not kill a 3-hour run
            log(f"  WARN could not save image {name}: {exc}", handle)
    return saved


def block_to_dict(block):
    """JSONBlockOutput -> plain JSON-safe dict.

    Marker hangs raw PIL images off the `images` field of picture/figure
    blocks, which pydantic's model_dump cannot serialize. The pixels are
    already written to disk by save_images(), so here we keep only the image
    *names* -- that is the join key back to images/.
    """
    # Marker's ids and section-hierarchy values are BlockId objects, not the
    # plain strings the pydantic model advertises -- coerce every one of them.
    out = {
        "id": str(block.id),
        "block_type": str(block.block_type),
        "html": block.html,
        "bbox": [float(v) for v in block.bbox],
    }
    if block.section_hierarchy:
        out["section_hierarchy"] = {str(k): str(v)
                                    for k, v in block.section_hierarchy.items()}
    if block.images:
        # Keyed by BlockId objects, and the values are base64 payloads we drop.
        out["image_names"] = sorted(str(k) for k in block.images)
    if block.children:
        out["children"] = [block_to_dict(child) for child in block.children]
    return out


def json_to_dict(rendered):
    """JSONOutput -> plain dict, dropping unserializable image payloads."""
    return {
        "block_type": str(rendered.block_type),
        "children": [block_to_dict(page) for page in rendered.children],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    parser.add_argument("outdir")
    parser.add_argument("--chunk", type=int,
                        default=int(os.environ.get("MARKER_CHUNK", 32)))
    parser.add_argument("--start", type=int, default=0,
                        help="first PDF page, 0-based inclusive")
    parser.add_argument("--end", type=int, default=None,
                        help="last PDF page, 0-based inclusive")
    args = parser.parse_args()

    md_dir = os.path.join(args.outdir, "chunks", "md")
    json_dir = os.path.join(args.outdir, "chunks", "json")
    done_dir = os.path.join(args.outdir, "chunks", "done")
    images_dir = os.path.join(args.outdir, "images")
    for directory in (md_dir, json_dir, done_dir, images_dir):
        os.makedirs(directory, exist_ok=True)

    total_pages = len(pdfium.PdfDocument(args.pdf))
    last = total_pages - 1 if args.end is None else min(args.end, total_pages - 1)

    handle = open(os.path.join(args.outdir, "marker_book.log"), "a")
    log(f"START {args.pdf}", handle)
    log(f"  pages {args.start}-{last} of {total_pages}, chunk={args.chunk}", handle)

    ranges = [
        (start, min(start + args.chunk - 1, last))
        for start in range(args.start, last + 1, args.chunk)
    ]
    pending = [r for r in ranges
               if not os.path.exists(os.path.join(done_dir, f"{r[0]:05d}-{r[1]:05d}.ok"))]
    log(f"  {len(ranges)} chunks, {len(pending)} pending, "
        f"{len(ranges) - len(pending)} already done", handle)
    if not pending:
        log("NOTHING TO DO -- all chunks already complete", handle)
        return 0

    t_models = time.time()
    models = create_model_dict()
    log(f"  models loaded in {time.time() - t_models:.0f}s", handle)

    t_all = time.time()
    failures = []
    for index, (start, end) in enumerate(pending, 1):
        tag = f"{start:05d}-{end:05d}"
        t_chunk = time.time()
        try:
            config = build_config(start, end)
            converter = PdfConverter(artifact_dict=models, config=config)

            # Build ONCE, render TWICE -- the expensive OCR/layout work is in
            # build_document, so the JSON block tree is effectively free.
            document = converter.build_document(args.pdf)

            markdown_rendered = converter.resolve_dependencies(MarkdownRenderer)(document)
            json_rendered = converter.resolve_dependencies(JSONRenderer)(document)

            # Images first: the figure crops are the only copy of a scanned
            # graph, so never risk losing them to a later serialization error.
            images_saved = save_images(
                getattr(markdown_rendered, "images", None), images_dir, handle)

            with open(os.path.join(md_dir, f"{tag}.md"), "w") as f:
                f.write(markdown_rendered.markdown)
            with open(os.path.join(json_dir, f"{tag}.json"), "w") as f:
                json.dump(json_to_dict(json_rendered), f, ensure_ascii=False,
                          default=str)  # last-resort coercion for stray marker objects

            with open(os.path.join(done_dir, f"{tag}.ok"), "w") as f:
                f.write(f"{len(markdown_rendered.markdown)} chars, "
                        f"{images_saved} images, {time.time() - t_chunk:.0f}s\n")

            elapsed = time.time() - t_all
            rate = elapsed / index
            log(f"  [{index}/{len(pending)}] pages {start}-{end}: "
                f"{len(markdown_rendered.markdown)} chars, {images_saved} images, "
                f"{time.time() - t_chunk:.0f}s "
                f"(eta {rate * (len(pending) - index) / 60:.0f} min)", handle)

            del document, markdown_rendered, json_rendered, converter
        except Exception:
            failures.append(tag)
            log(f"  FAIL chunk {tag}:\n{traceback.format_exc()}", handle)
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    log(f"DONE in {(time.time() - t_all) / 60:.0f} min, "
        f"{len(failures)} failed chunks: {failures}", handle)
    handle.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
