#!/usr/bin/env python3
"""Triage reconciliation conflicts at book scale so a human/Claude only has to
vision-judge the few that genuinely need it.

A 665-pg textbook produced ~822 conflicts, but ~95% are NOT real disagreements:
they are plain-TeX-vs-LaTeX spelling, or one engine truncated, or the two engines
numbered different printed equations the same. This classifies them:

  tier1 cosmetic     - identical up to LaTeX spelling/order        -> both_correct
  tier2 garble       - exactly one side has OCR-artifact macros    -> pick clean side
  tier3 truncated    - one side much shorter & ill-formed          -> pick complete side
  misaligned/empty   - tags matched different/empty equations      -> Marker backbone
  tier4 VISION       - both clean, same equation, real symbol diff -> needs a human/Claude

Writes (next to equations.json):
  auto_verdicts.json  - verdicts for everything except tier4 (apply with resolve.py --apply)
  vision_todo.json    - tier4 only, ranked clearest-first (highest candidate similarity)

Then render strips + judge tier4:
  # make an equations.json where only tier4 tags are 'conflict', then:
  resolve.py --pdf BOOK.pdf --eqs <that>.json --merged merged.md --outdir DIR --manifest
  # batch strips into tall sheets (image judges reject multi-image reqs ~2000px):
  build_sheets.py DIR 6   # read sheets/, then record_verdicts.py DIR batch.json
  # finally apply the union of auto_verdicts.json + verdicts.json: resolve.py --apply

Usage: triage_conflicts.py equations.json OUTDIR  [pure stdlib + combine.py]
"""
import json, re, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import combine

GARBLE = re.compile(r"\\(hbox|mskip|kern|raise|lower|vbox|smash|char|hphantom|"
                    r"hfill|hskip|vrule|hrule|leaders|discretionary|mathchar|relax)|0\.0pt")
def skel(s):
    s = combine._norm(s)
    return s.replace("\\not", "").replace("/", "")
def wellformed(s):
    return not GARBLE.search(s) and s.count("{") == s.count("}")
def trigrams(s): return set(s[i:i+3] for i in range(len(s) - 2)) or {s}
def jaccard(a, b):
    A, B = trigrams(a), trigrams(b)
    return len(A & B) / len(A | B) if A | B else 1.0

def triage(eqs_path, outdir, sim_threshold=0.55):
    os.makedirs(outdir, exist_ok=True)
    eqs = json.load(open(eqs_path))
    conf = [r for r in eqs["equations"] if r["status"] == "conflict"]
    auto, vision = {}, []
    for r in conf:
        tag, n, m = r["tag"], r["nougat"], r["marker"]
        sn, sm = skel(n), skel(m)
        if sorted(sn) == sorted(sm):                                   # tier1 cosmetic
            auto[tag] = _v("both_correct", "high", m, "Identical up to LaTeX spelling/order (auto).")
        elif bool(GARBLE.search(n)) != bool(GARBLE.search(m)):         # tier2 garble
            win = "marker" if GARBLE.search(n) else "nougat"
            auto[tag] = _v(win, "medium", m if win == "marker" else n,
                           "Other candidate has OCR-artifact macros (auto).")
        elif (min(len(sn), len(sm)) / max(len(sn), len(sm), 1) < 0.6
              and wellformed(n) != wellformed(m)):                     # tier3 truncated
            win = "nougat" if (len(sn) > len(sm) and wellformed(n)) else "marker"
            auto[tag] = _v(win, "low", n if win == "nougat" else m,
                           "Other candidate truncated/ill-formed; kept more complete (auto).")
        elif not sn or not sm or jaccard(sn, sm) < sim_threshold:      # misaligned/empty
            auto[tag] = _v("marker", "low", m,
                           "Tags matched different/empty equations (misaligned); kept Marker backbone.")
        else:                                                          # tier4 vision
            r = dict(r); r["_sim"] = round(jaccard(sn, sm), 3); vision.append(r)
    vision.sort(key=lambda r: -r["_sim"])                              # clearest first
    json.dump({"_model": "auto-triage", **auto}, open(os.path.join(outdir, "auto_verdicts.json"), "w"), indent=1)
    json.dump(vision, open(os.path.join(outdir, "vision_todo.json"), "w"), indent=1)
    print(f"conflicts {len(conf)} -> auto {len(auto)} | VISION {len(vision)}")
    print(f"  wrote auto_verdicts.json ({len(auto)}) and vision_todo.json ({len(vision)}, ranked)")

def _v(verdict, conf, latex, why):
    return {"verdict": verdict, "confidence": conf, "correct_latex": latex, "reasoning": why}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: triage_conflicts.py equations.json OUTDIR")
    triage(sys.argv[1], sys.argv[2])
