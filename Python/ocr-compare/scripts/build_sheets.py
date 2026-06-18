#!/usr/bin/env python3
"""Build vertical composite contact sheets from resolve.py --manifest strips, so
a vision judge (e.g. Claude Code) can read them at book scale.

WHY THIS EXISTS: resolve.py --manifest renders each conflict to a tall strip at
scale=5.0 (~2161px wide). A judge tool that reads images often rejects
*multi-image* requests whose dimensions approach ~2000px ("many-image" limit),
so reading the strips one-per-call is slow and feeding several at once fails.
A single tall image, however, loads fine. This script stacks several strips into
one downscaled sheet (<=TARGET_W wide) with the eq tag burned into a header band,
so the judge reads ONE sheet per call and still sees ~6 equations.

Reads from RECONCILED_DIR (the resolve.py --outdir):
  manifest.json   - [{tag, page, image, nougat, marker}, ...] from --manifest
  verdicts.json   - {tag: {...}} verdicts already recorded (skipped; optional)
Writes into RECONCILED_DIR:
  sheets/sheet_NNN.png        - composite, ordered by manifest (clearest-first)
  sheets_meta/sheet_NNN.json  - [{tag, page, nougat, marker}] for that sheet

Then: read each sheet PNG, compare nougat vs marker against the printed eq, and
record verdicts with record_verdicts.py.

Usage: build_sheets.py RECONCILED_DIR [STRIPS_PER_SHEET=6]
Needs Pillow -> run with venv-resolve's python.
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

TARGET_W = 1500   # downscale strips to this width: keeps a tall sheet legible
HEADER_H = 46
PAD = 10


def load_font():
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, 30)
    return ImageFont.load_default()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    base = os.path.abspath(sys.argv[1])
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 6

    manifest = json.load(open(os.path.join(base, "manifest.json")))
    try:
        done = set(json.load(open(os.path.join(base, "verdicts.json"))))
    except FileNotFoundError:
        done = set()
    done.discard("_model")

    remaining = [e for e in manifest if e["tag"] not in done]
    print(f"manifest={len(manifest)} done={len(done)} remaining={len(remaining)}")

    os.makedirs(os.path.join(base, "sheets"), exist_ok=True)
    os.makedirs(os.path.join(base, "sheets_meta"), exist_ok=True)
    font = load_font()

    for i in range(0, len(remaining), per):
        group = remaining[i:i + per]
        imgs = []
        for e in group:
            im = Image.open(e["image"]).convert("RGB")
            if im.width != TARGET_W:
                h = int(im.height * TARGET_W / im.width)
                im = im.resize((TARGET_W, h), Image.LANCZOS)
            imgs.append(im)
        total_h = sum(HEADER_H + im.height + PAD for im in imgs) + PAD
        sheet = Image.new("RGB", (TARGET_W, total_h), "white")
        d = ImageDraw.Draw(sheet)
        y = PAD
        for e, im in zip(group, imgs):
            d.rectangle([0, y, TARGET_W, y + HEADER_H], fill=(30, 30, 60))
            d.text((12, y + 8), f'TAG {e["tag"]}  (page {e["page"]})',
                   fill="white", font=font)
            y += HEADER_H
            sheet.paste(im, (0, y))
            y += im.height + PAD
        idx = i // per
        sheet.save(os.path.join(base, "sheets", f"sheet_{idx:03d}.png"))
        meta = [{"tag": e["tag"], "page": e["page"],
                 "nougat": e["nougat"], "marker": e["marker"]} for e in group]
        json.dump(meta, open(os.path.join(base, "sheets_meta",
                                          f"sheet_{idx:03d}.json"), "w"), indent=2)
        print(f"sheet_{idx:03d}.png {sheet.size} tags={[e['tag'] for e in group]}")

    n = (len(remaining) + per - 1) // per
    print(f"\nTOTAL SHEETS: {n}")


if __name__ == "__main__":
    main()
