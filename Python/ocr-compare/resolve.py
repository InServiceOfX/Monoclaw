#!/usr/bin/env python3
"""
LLM conflict-resolver tier for the Nougat+Marker reconciliation (xAI / Grok).

For each equation flagged `conflict` in equations.json, this:
  1. Finds the PDF page the equation lives on (monotonic scan of the text layer).
  2. Renders that page to a PNG.
  3. Asks Grok (vision) which LaTeX rendering matches the page — nougat, marker,
     both, or neither — and to emit the corrected LaTeX.
  4. Writes resolved.md (merged.md with CONFLICT flags replaced by the verdict),
     equations_resolved.json, and resolutions.md.

Provider: xAI Grok via the OpenAI-compatible API (base_url https://api.x.ai/v1),
default model grok-4.3, structured output via response_format json_schema.
Needs XAI_API_KEY in the env for a real run. Use --dry-run to test the
page-finding + rendering plumbing without calling the API.

Usage:
  python3 resolve.py --pdf sample.pdf --eqs reconciled/equations.json \
      --merged reconciled/merged.md --outdir reconciled/ [--dry-run] [--model ...]
"""
import argparse, base64, json, os, re, sys
import pypdfium2 as pdfium

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string",
                    "enum": ["nougat", "marker", "both_correct", "both_wrong"]},
        "correct_latex": {"type": "string",
                          "description": "The equation as it should appear, in LaTeX, matching the PDF."},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "reasoning": {"type": "string",
                      "description": "One sentence: the specific token that decided it."},
    },
    "required": ["verdict", "correct_latex", "confidence", "reasoning"],
    "additionalProperties": False,
}

PROMPT = """You are verifying OCR of a physics paper. The image is one page of the PDF.
Two OCR tools produced different LaTeX for equation ({tag}) on this page.

NOUGAT:
{nougat}

MARKER:
{marker}

Compare each against the equation as actually printed on the page (mind spinor
indices, sub/superscripts, bracket types ⟨⟩ vs [], primes, and bars). Decide which
is correct. If both are wrong, give the correct LaTeX yourself. Return JSON only."""


def render_pages_text(pdf_path):
    """Return (pdf, [page_text, ...]) — text layer per page for locating equations."""
    pdf = pdfium.PdfDocument(pdf_path)
    texts = []
    for i in range(len(pdf)):
        tp = pdf[i].get_textpage()
        texts.append(tp.get_text_range())
    return pdf, texts


def find_page(tag, page_texts, last_page):
    """First page index >= last_page whose text layer contains '(tag)'. Monotonic."""
    needle = f"({tag})"
    for i in range(last_page, len(page_texts)):
        if needle in page_texts[i]:
            return i
    # fall back: search from the top
    for i in range(len(page_texts)):
        if needle in page_texts[i]:
            return i
    return None


def find_equation_bbox(page, textpage, tag):
    """Locate the equation label '(tag)' and return its PDF-point bbox
    (left, bottom, right, top). Handles two-column layouts: an equation label is
    the rightmost token within its own column on its text line, whereas an inline
    citation has more text to its right. Picks the topmost such label. Returns
    None if not found."""
    w, _ = page.get_size()
    mid = w / 2.0
    # all chars on the page, with centers (for the column / line-end test)
    n = textpage.count_chars()
    chars = []
    for i in range(n):
        l, b, r, t = textpage.get_charbox(i)
        chars.append((l, b, r, t, (l + r) / 2.0, (b + t) / 2.0))

    def is_line_end_label(x1, yc, side_left):
        """True if no char in the same column sits to the right on the same line."""
        for (l, b, r, t, cx, cy) in chars:
            if (cx < mid) != side_left:
                continue                      # different column
            if abs(cy - yc) > 4:
                continue                      # different text line
            if r > x1 + 2:
                return False                  # something to the right → not a label
        return True

    try:
        searcher = textpage.search(f"({tag})", match_case=True)
    except TypeError:
        searcher = textpage.search(f"({tag})")
    candidates, fallback = [], None
    while True:
        hit = searcher.get_next()
        if hit is None:
            break
        idx, count = hit
        boxes = [textpage.get_charbox(i) for i in range(idx, idx + count)]
        l = min(b[0] for b in boxes); btm = min(b[1] for b in boxes)
        r = max(b[2] for b in boxes); top = max(b[3] for b in boxes)
        yc = (btm + top) / 2.0
        if fallback is None or r > fallback[2]:
            fallback = (l, btm, r, top)
        if is_line_end_label(r, yc, (l + r) / 2.0 < mid):
            candidates.append((l, btm, r, top))
    if candidates:
        return max(candidates, key=lambda bb: bb[3])   # topmost label
    return fallback


def render_png(pdf, page_index, scale=2.0, bbox=None,
               pad_above=72, pad_below=36):
    """Render the page (or a tall-padded band around bbox) to PNG bytes.
    bbox is (left, bottom, right, top) in PDF points; we keep full page width
    and crop a horizontal strip so multi-line equations stay intact."""
    page = pdf[page_index]
    crop = (0, 0, 0, 0)
    if bbox is not None:
        w_pts, h_pts = page.get_size()
        _, y0, _, y1 = bbox
        bottom_crop = max(0.0, y0 - pad_below)
        top_crop = max(0.0, h_pts - (y1 + pad_above))
        crop = (0, bottom_crop, 0, top_crop)
    bitmap = page.render(scale=scale, crop=crop)
    pil = bitmap.to_pil()
    from io import BytesIO
    buf = BytesIO()
    pil.save(buf, format="PNG")
    return buf.getvalue()


def resolve_one(client, model, tag, nougat, marker, png_bytes):
    b64 = base64.standard_b64encode(png_bytes).decode()
    resp = client.chat.completions.create(
        model=model,
        max_tokens=8000,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "verdict", "strict": True, "schema": SCHEMA},
        },
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
                {"type": "text",
                 "text": PROMPT.format(tag=tag, nougat=nougat, marker=marker)},
            ],
        }],
    )
    return json.loads(resp.choices[0].message.content)


def write_outputs(eqs, resolutions, merged_path, outdir, model_label):
    """Write equations_resolved.json, resolutions.md, resolved.md from a
    {tag: {verdict, correct_latex, confidence, reasoning, page}} dict."""
    for r in eqs["equations"]:
        if r["tag"] in resolutions:
            r["resolution"] = resolutions[r["tag"]]
    json.dump(eqs, open(os.path.join(outdir, "equations_resolved.json"), "w"), indent=2)

    lines = ["# Conflict Resolutions (vision pass)\n",
             f"Model: {model_label}\n",
             "| eq | page | winner | conf | corrected LaTeX |",
             "|----|------|--------|------|-----------------|"]
    for tag, v in sorted(resolutions.items(), key=lambda x: int(x[0])):
        latex = v["correct_latex"].replace("|", "\\|")
        lines.append(f"| ({tag}) | {v.get('page','?')} | **{v['verdict']}** | {v['confidence']} | `{latex}` |")
    open(os.path.join(outdir, "resolutions.md"), "w").write("\n".join(lines))

    merged = open(merged_path).read()
    for tag, v in resolutions.items():
        pat = re.compile(r"<!-- eq \(" + re.escape(tag) + r"\) ⚠ CONFLICT.*?-->", re.DOTALL)
        repl = (f"<!-- eq ({tag}) ✓ RESOLVED → {v['verdict']} ({v['confidence']}): "
                f"{v['correct_latex']}  [{v['reasoning']}] -->")
        merged = pat.sub(repl.replace("\\", "\\\\"), merged)
    open(os.path.join(outdir, "resolved.md"), "w").write(merged)

    winners = {}
    for v in resolutions.values():
        winners[v["verdict"]] = winners.get(v["verdict"], 0) + 1
    print(f"Wrote resolved.md, equations_resolved.json, resolutions.md to {outdir}/")
    print("Verdict tally:", winners)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--eqs", required=True)
    ap.add_argument("--merged", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--model", default="grok-4.3")
    ap.add_argument("--dry-run", action="store_true",
                    help="render strips, no model call")
    ap.add_argument("--manifest", action="store_true",
                    help="render strips + write manifest.json for an external "
                         "judge (e.g. Claude Code) to fill in, then --apply")
    ap.add_argument("--apply", metavar="VERDICTS_JSON",
                    help="write outputs from a verdicts file "
                         "{tag:{verdict,correct_latex,confidence,reasoning,page}}")
    args = ap.parse_args()

    eqs = json.load(open(args.eqs))

    # --apply: no rendering needed, just emit outputs from supplied verdicts.
    if args.apply:
        verdicts = json.load(open(args.apply))
        label = verdicts.pop("_model", "claude-code") if isinstance(verdicts, dict) else "claude-code"
        write_outputs(eqs, verdicts, args.merged, args.outdir, label)
        return

    conflicts = [r for r in eqs["equations"] if r["status"] == "conflict"]
    if not conflicts:
        print("No conflicts to resolve.")
        return

    pdf, page_texts = render_pages_text(args.pdf)
    os.makedirs(os.path.join(args.outdir, "pages"), exist_ok=True)

    client = None
    if not (args.dry_run or args.manifest):
        from openai import OpenAI
        if not os.environ.get("XAI_API_KEY"):
            sys.exit("ERROR: XAI_API_KEY not set. Use --manifest (Claude Code judge) "
                     "or set the key.")
        client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")

    last_page = 0
    resolutions = {}
    manifest = []
    for r in conflicts:
        tag = r["tag"]
        page = find_page(tag, page_texts, last_page)
        if page is None:
            print(f"eq ({tag}): page not found, skipping")
            continue
        last_page = page
        textpage = pdf[page].get_textpage()
        bbox = find_equation_bbox(pdf[page], textpage, tag)
        png = render_png(pdf, page, scale=5.0, bbox=bbox) if bbox else render_png(pdf, page)
        png_path = os.path.join(args.outdir, "pages", f"page_{page+1}_eq{tag}.png")
        with open(png_path, "wb") as f:
            f.write(png)

        if args.dry_run or args.manifest:
            mode = "cropped strip @5x" if bbox else "FULL PAGE @2x (bbox not found)"
            print(f"eq ({tag}) -> page {page+1}  ({len(png)//1024} KB, {mode})")
            manifest.append({"tag": tag, "page": page + 1, "image": png_path,
                             "nougat": r["nougat"], "marker": r["marker"]})
            continue

        verdict = resolve_one(client, args.model, tag, r["nougat"], r["marker"], png)
        verdict["page"] = page + 1
        resolutions[tag] = verdict
        print(f"eq ({tag}) p{page+1}: {verdict['verdict']} ({verdict['confidence']}) — {verdict['reasoning']}")

    if args.manifest:
        mpath = os.path.join(args.outdir, "manifest.json")
        json.dump(manifest, open(mpath, "w"), indent=2)
        print(f"\nManifest written to {mpath}. Have Claude Code read each 'image' and "
              f"the two candidates, write verdicts.json, then run --apply verdicts.json.")
        return
    if args.dry_run:
        print(f"\nDry run complete: {len(conflicts)} conflicts -> {args.outdir}/pages/.")
        return

    write_outputs(eqs, resolutions, args.merged, args.outdir, args.model)


if __name__ == "__main__":
    main()
