#!/usr/bin/env python3
"""Run Marker on a LARGE PDF in page-range chunks, loading the models ONCE.

Why this exists: `marker_single` on a big book (e.g. 665 pp) builds the whole
document in memory and OOMs (~10 GB RSS killed the 665-pg Srednicki run). This
driver loads the Marker/Surya models a single time, then converts the PDF in
fixed page-range chunks, freeing per-chunk memory in between, and concatenates
the markdown. Batch sizes are capped to fit an 8 GB GPU on dense-math pages.

Run it with the MARKER venv's python (weights env vars are set by the caller,
e.g. scripts/run_ocr_large.sh, or by sourcing scripts/_paths.sh):

    "$OCR_VENV_DIR/venv-marker/bin/python" scripts/marker_chunked.py IN.pdf OUT.md

Env knobs (all optional):
    MARKER_CHUNK=16            pages per chunk (lower = less peak RAM/VRAM)
    MARKER_REC_BATCH=8         recognition batch size  (lower = less VRAM)
    MARKER_DET_BATCH=4         detection batch size
    MARKER_LAYOUT_BATCH=4      layout batch size
"""
import sys, os, gc, time
import pypdfium2 as pdfium
import torch
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser
from marker.output import text_from_rendered

def main():
    if len(sys.argv) < 3:
        sys.exit("usage: marker_chunked.py IN.pdf OUT.md [chunk] [total_pages]")
    pdf_path, out_md = sys.argv[1], sys.argv[2]
    chunk = int(sys.argv[3]) if len(sys.argv) > 3 else int(os.environ.get("MARKER_CHUNK", 16))
    total = int(sys.argv[4]) if len(sys.argv) > 4 else len(pdfium.PdfDocument(pdf_path))
    rec = int(os.environ.get("MARKER_REC_BATCH", 8))
    det = int(os.environ.get("MARKER_DET_BATCH", 4))
    lay = int(os.environ.get("MARKER_LAYOUT_BATCH", 4))

    print(f"[marker_chunked] {pdf_path}\n  pages={total} chunk={chunk} "
          f"batch(rec/det/lay)={rec}/{det}/{lay} -> {out_md}", flush=True)
    t0 = time.time()
    models = create_model_dict()                       # load all models ONCE
    print(f"[marker_chunked] models loaded in {time.time()-t0:.0f}s", flush=True)

    parts = []
    for start in range(0, total, chunk):
        end = min(start + chunk - 1, total - 1)
        cfg = ConfigParser({
            "page_range": f"{start}-{end}", "output_format": "markdown",
            "recognition_batch_size": rec, "detection_batch_size": det,
            "layout_batch_size": lay, "ocr_error_batch_size": det, "table_rec_batch_size": 2,
        }).generate_config_dict()
        conv = PdfConverter(artifact_dict=models, config=cfg)
        ts = time.time()
        rendered = conv(pdf_path)
        text, _, _ = text_from_rendered(rendered)
        parts.append(text)
        print(f"[marker_chunked] pages {start}-{end}: {len(text)} chars "
              f"in {time.time()-ts:.0f}s", flush=True)
        del rendered, conv
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    with open(out_md, "w") as f:
        f.write("\n\n".join(parts))
    print(f"[marker_chunked] DONE {len(''.join(parts))} chars in "
          f"{time.time()-t0:.0f}s -> {out_md}", flush=True)

if __name__ == "__main__":
    main()
