#!/usr/bin/env python3
"""Merge a batch of vision verdicts into verdicts.json (for resolve.py --apply).

After reading a contact sheet from build_sheets.py, the judge writes a small batch
file and runs this to append to RECONCILED_DIR/verdicts.json. correct_latex and
page are pulled from manifest.json so the batch only carries the decision, not the
full LaTeX -- except when neither candidate is right, where an explicit "latex"
override supplies a reconstruction.

BATCH_JSON is a list of objects:
  {"tag": "6.23", "verdict": "marker",  "reasoning": "...", "confidence": "high"}
  {"tag": "8.3",  "verdict": "nougat",  "reasoning": "..."}                # conf defaults high
  {"tag": "6.22", "verdict": "custom",  "latex": "...\\tag{6.22}", "reasoning": "..."}

verdict in {marker, nougat, both_correct, custom}. correct_latex resolves as:
  explicit "latex"  >  manifest nougat field (verdict==nougat)  >  manifest marker field.

Schema written per tag (matches resolve.py write_outputs):
  {verdict, correct_latex, confidence, reasoning, page}

Usage: record_verdicts.py RECONCILED_DIR BATCH_JSON  [pure stdlib]
"""
import json, os, sys


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    base, batch_path = os.path.abspath(sys.argv[1]), sys.argv[2]

    manifest = {e["tag"]: e for e in json.load(open(os.path.join(base, "manifest.json")))}
    vpath = os.path.join(base, "verdicts.json")
    try:
        verdicts = json.load(open(vpath))
    except FileNotFoundError:
        verdicts = {"_model": "claude-code"}
    batch = json.load(open(batch_path))

    for b in batch:
        tag, v = b["tag"], b["verdict"]
        m = manifest[tag]
        latex = b.get("latex") or (m["nougat"] if v == "nougat" else m["marker"])
        verdicts[tag] = {"verdict": v, "correct_latex": latex,
                         "confidence": b.get("confidence", "high"),
                         "reasoning": b["reasoning"], "page": m["page"]}
        print(f"  {tag:10s} -> {v}")

    json.dump(verdicts, open(vpath, "w"), indent=2)
    print(f"verdicts.json now has {len([k for k in verdicts if k != '_model'])} verdicts")


if __name__ == "__main__":
    main()
