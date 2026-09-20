# Book review runbook — OCR two engines, triage with a local VLM, inspect the source, publish

This is the operational guide for the pipeline that produced the reviewed propulsion/combustion
corpora (Humble, Huzel & Huang, Sutton verification, Williams, Turns, Hill & Peterson —
`Data/Public/books/EngineeringPhysics/PROPULSION-CORPUS.md`). It is written for an agent
(Claude Code, Codex, Grok, a harness, or a person) that has to **run it on a new book** or
**continue an unfinished book** without re-deriving anything. The older, lighter paths
(equation-tag reconciliation for LaTeX-typeset books; page-accurate Marker only) are in
`../AGENTS.md`; use this one when the mathematics of a scanned or engineering-typeset book
has to be checked against the page.

The one-sentence contract: **two independent OCR readings (Marker, Nougat) are aligned per page;
a local vision model is used only to triage; every display equation, table and OCR-only fragment
that the two readings and the model do not settle is inspected on the source image by the
reviewing agent and recorded with the image hash; prose is never edited automatically.**

The reviewing agent must be able to look at PNG crops. A text-only model cannot do step 5.

---

## 0. Layout

```
bookreview/                      canonical copy (this directory) — never run it here
  run_ocr.sh                     both OCR passes + reconcile          (GPU)
  review_after_ocr.sh            waits for OCR, then finish.py         (GPU)
  finish.py                      bounded VLM review → assemble → publish
  finalize.sh                    CPU-only finalisation, idempotent
  books.example.json             → copy to scripts/books.json in your work dir
  review-model.json              the calibrated VLM (files + sha256s)
  calibration-acceptance.json    gate: model signature + protocol that finish.py asserts
  scripts/                       the pipeline (see §10 for what each does)

<book>-work/                     a per-book copy of the above (e.g. hillpeterson-work/)
  scripts/books.json             the only per-book configuration
  OCR-STATE.txt  finish-state.json  gpu.lock  STATUS.md   run state + your log

<root>/  (books.json "root", next to the PDF)      the corpus — what gets published
  sources/   native/ renders/ marker/ nougat/ page-map.json pages.json source.json
  parsed/    objects.json pages/ crops/ tables/ reconciled-pages/ book-reconciled.md
             EQUATIONS.md TABLES.md FIGURES.md equations.json tables.json figures.json
             chapters/ inline-math.json headings.json coverage.json
  reconciliation/  equations.json jobs.json vision/*.json publication-summary.json
                   unresolved.json unreviewed-context.json notation-normalisation.json
  curated/   YOUR inputs and YOUR verdicts (the authority) — see §4, §5
  logs/  provenance/  INDEX.md  toc.json
```

## 1. Prerequisites (once per machine)

- NVIDIA GPU with ≥12 GB (everything here ran on one RTX 3060). `nvidia-smi -L` — note that the
  **docker `--gpus device=N` index follows nvidia-smi order** while `CUDA_VISIBLE_DEVICES` follows
  CUDA order; on the reference machine the 3060 is nvidia-smi `1` and CUDA `0`. `finish.py` uses
  `--gpus device=1`; change it if your card is elsewhere.
- Python venvs via **uv** (never system pip): `../scripts/setup_envs.sh nougat marker` creates
  `$OCR_VENV_DIR/venv-nougat` and `venv-marker` (Python 3.10, CUDA torch). Paths come from
  `../scripts/_paths.sh` (`OCR_STORAGE`, `OCR_VENV_DIR`, weights dirs); override in
  `../scripts/env.sh`. Marker/Nougat weights must already be cached (`HF_HUB_OFFLINE=1` is set).
  `venv-marker` also provides `pypdfium2` and Pillow, which the inspection tools use.
- `rustc` (the page-local equation comparator `scripts/math_tokens.rs` is compiled by `run_ocr.sh`).
- Graphviz `dot` (schematic rendering only).
- Docker with the NVIDIA runtime and the image `ghcr.io/ggml-org/llama.cpp:server-cuda` already
  pulled (`finish.py` runs with `--pull never`). The VLM weights named in `review-model.json`
  (Qwythos-9B Q6_K GGUF + F16 mmproj) must exist at `directory`. The **whole** spec — including
  `directory` — is hashed into `model_signature`, which `finish.py` compares with
  `calibration-acceptance.json`. On another machine: edit `directory`, verify the two file sha256s
  still match, then write the new signature (`python -c 'import sys;sys.path.insert(0,"scripts");import vision_review;print(vision_review.MODEL_SIGNATURE)'`)
  into `calibration-acceptance.json`; that is a path change, not a re-calibration. Any change to the
  weights or the prompt/protocol *is* a re-calibration (§3).
- **One GPU job at a time.** `run_ocr.sh` holds `gpu.lock`; `finish.py` must not start until
  `OCR-STATE.txt` says `OCR and comparison complete` (that is all `review_after_ocr.sh` does). Never
  start a second book's OCR while another is running.

## 2. Start a book

```bash
cp -r Monoclaw/Python/ocr-compare/bookreview  <slug>-work && cd <slug>-work
cp books.example.json scripts/books.json      # edit: id, title, authors, pdf, root, force_ocr, expected_pdf_pages, sha256
export OCR_PATHS_SH=/path/to/Monoclaw/Python/ocr-compare/scripts/_paths.sh   # only if the work dir is not inside the repo
nohup bash run_ocr.sh > ocr-console.log 2>&1 &
nohup bash review_after_ocr.sh > review-console.log 2>&1 &    # waits, then runs finish.py
```

`books.json` fields: `id` (object-id prefix, e.g. `hillpeterson:p0184-equation-11`), `pdf`,
`root` (the corpus directory; created), `force_ocr` (`true` for scans; `false` for born-digital
PDFs so Marker uses the text layer), `expected_pdf_pages` (asserted everywhere),
`source_kind` (free text that ends up in INDEX.md), `sha256` of the PDF, optional
`notation_rules` (§7).

`run_ocr.sh` states (`OCR-STATE.txt`): `Marker and source inventory running` → `Marker complete;
structural extraction and Nougat running` → `Both OCR passes complete; reconciliation preparation
running` → `OCR and comparison complete; source review and packaging remain`, or `FAILED at line N`.
Rough cost on the 3060: Marker (forced OCR) ≈ 6 pages/min (Williams, 699 pages: 119 min); Nougat
(batch 8) ≈ 30 pages/min (699 pages: 22 min); reconcile takes seconds.
To **continue** a book from a fresh copy of the scripts (no OCR to run): copy `bookreview/` over the
work dir, point `scripts/books.json` at the existing `root`, and compile the comparator first —
`rustc -O scripts/math_tokens.rs -o scripts/math_tokens` — `triage_math.py` calls it and crashes
without it (`run_ocr.sh` normally does this). Everything except `run_ocr.sh` and `finish.py` is
CPU-only and idempotent, but note that `assemble.py` **writes into `root`** (`parsed/reconciled-pages`,
`book-reconciled.md`, ledgers) and `publish_notation.py` runs after it — so after any ad-hoc
assemble, finish with `bash finalize.sh` to leave the published files consistent.

If a page-accurate Marker run already exists (`ocr-compare/marker/{chunks,images,marker_book.log}`),
copy it into `sources/marker/` with a `REUSED.txt` note instead of re-running Marker
(`hillpeterson-work/run_ocr.sh` is the worked example).

What `reconcile.py` leaves in `reconciliation/`: `equations.json` (every Marker display object with
its page-local Nougat alignment and status `different | label_disagreement | format_only |
marker_only`, plus `nougat_unmatched` fragments) and `jobs.json` (one review job per object or
fragment, kinds `text | math | table | unmatched_math | figure`, each with a fingerprint over
image + candidate readings).

## 3. Model review (`finish.py`) — what it does and does not do

Run by `review_after_ocr.sh`. Order: assert the calibration gate (`calibration-acceptance.json`
must carry the current `REVIEW_PROTOCOL` and the sha256 of `review-model.json` — **if you change the
model or the prompt you must re-calibrate on direct transcriptions first**) → `catalog_book.py`
(folio rules) → `augment_tables.py` → `reconcile.py` → start the llama.cpp container
(`<id>-source-review`, port 8878, label `org.propulsion.task=<id>-book-<date>`) → review jobs in the
order **math → table → unmatched_math → figure** (never `text`: whole-page prose review failed
source-fidelity checks on Humble and is disabled by policy) → stop the container → `triage_math.py`
→ `assemble.py` → `publish_book.py`.

- A job whose objects already have records in `curated/manual-review.json` or
  `curated/agreement-review.json` is **skipped** — so the earlier you record direct verdicts, the
  less GPU time is spent. Reviewing tables and fragments yourself while the math pass runs is the
  normal way to work.
- Replies are grammar-constrained (GBNF built per job by `vision_review.job_grammar`); a length-limited reply is left `failed`
  and not retried with a bigger budget. Verdicts land in `reconciliation/vision/<job>.json` with the
  raw reply, prompt/grammar hashes and model signature. `assemble.py` runs every 100 jobs.
- Progress: `finish-state.json` (stage, completed/total, counts) and one summary line per 100
  jobs in `review-console.log`. Server log: `<root>/logs/vision-server-*.log`. The container is
  removed on exit or exception. ≈ 12 s per math job, 8 s per figure crop.
- Job fingerprints include the candidate readings, so a change to `parsed/objects.json` (e.g. a
  classification review) makes old verdicts `stale` and a re-run of `finish.py` would redo them.
  Don't re-run the finisher after such changes unless you want that.

**The model's verdict is never applied on its own.** `triage_math.py` re-derives every verdict from
the raw reply and places a transcription automatically only when two independent readings agree
after stylistic normalisation (Marker = Nougat; model = Marker; model = Nougat), recording it in
`curated/agreement-review.json`. Everything else goes to `curated/triage.json` for you.

## 4. Inputs you write by hand (`curated/`)

- `folio-checkpoints.json` (optional): `{"<pdf_page>": <printed_page>, ...}` read directly from a
  few page renders (`sources/renders/NNNN.jpg`). `catalog_book.py` infers per-region offset rules
  from OCR'd running heads/feet and reports/uses your checkpoints as overrides. Result:
  `curated/folio-rules.json`, `sources/page-map.json`. Keep a `folio-checkpoints.README.md` saying
  what you read where.
- `contents.json`: `[{"number": "1", "title": "...", "printed_start": 3, "pdf_start": 15,
  "evidence": "..."}, ...]` for chapters, appendices, answers, index. Drives the chapter files and
  the INDEX.md table (`toc.json`).
- `INDEX-notes.md`: appended verbatim to INDEX.md — page rule, notation of the print vs OCR, print
  slips transcribed as printed, what the schematics cover, superseded earlier products.
- `object-classification-review.json` (via `record_manual.classify`, §5): Marker "Table" objects
  that are really captions or two-column text (index pages, symbol lists laid out in columns).
- `schematics/*.mmd` (§6).

## 5. The direct-inspection loop (this is the review)

All recording goes through `scripts/record_manual.py`; every record carries the object id, the
crop/page image path and its sha256, your reason, a confidence and the timestamp. `assemble.py`
asserts the hash still matches, so a changed source image invalidates the record. Never edit
`parsed/pages/*.md`, `parsed/objects.json` or `reconciliation/*` by hand.

Verdict precedence (what wins when several exist): `curated/manual-review.json` (you) →
`curated/agreement-review.json` (two independent readings) → `reconciliation/vision/*.json` (model,
triage only) → `parsed/objects.json` (raw Marker).

### 5a. Display math

```bash
PY="$OCR_VENV_DIR/venv-marker/bin/python"
$PY -B scripts/triage_math.py            # → curated/triage.json; prints accepted / needs_direct
$PY -B scripts/inspect_sheet.py 0 8 /tmp/sheet.png   # crops of the first 8 open items stacked, + MARKER/NOUGAT/MODEL text
# look at /tmp/sheet.png, then:
$PY -B - <<'EOF'
import sys;sys.path.insert(0,'scripts');import record_manual as rm
rm.math('mybook:p0184-equation-11','corrected',corrected=r"\dot{m}_t c_{pt}(T_{04}-T_{05}) = \dot{m}_c c_{pc}(T_{03}-T_{02}). \tag{5.43}",
        reason='Direct crop inspection: subscripts are t/pt; Marker read l/pl.')
rm.math('mybook:p0189-equation-7','marker',reason='Direct crop inspection: Marker exact.')
EOF
```
Loop until `needs_direct` is 0. Choices: `marker` | `nougat` | `both` | `corrected` (give
`corrected=`) | `not_in_source` | `unreadable`. Rules that kept the six corpora consistent:
- Transcribe **what is printed**, including the equation label as `\tag{5.43}` (a `\qquad (5.43)`
  in Marker's text is also accepted; `fix_placements.py` and `assemble.py` keep one label).
  Print slips are transcribed as printed and described in `reason`; put them in `notes`, not
  `unresolved` (an `unresolved` list means the *transcription* is open).
- Multi-line displays → `aligned`/`gathered`; annotated balances → `\underbrace`; stacked verbal
  definitions → `\begin{array}`; one-line displays that the print joins with "and"/"or"/"to" stay on
  one line with `\quad\text{and}\quad` (Marker splits them and drops the word).
- Upright/roman symbols of the print (Mach number `\mathrm{M}`, `\mathrm{Pr}`, species
  `\mathrm{H_2O}`) are kept upright in corrections; a retained Marker display keeps Marker's italics
  (say so in INDEX-notes).
- Zoom when unsure: crop the object's `crop` from `parsed/objects.json` with Pillow at 2–3×, or
  render the page from the PDF with `pypdfium2` at `scale=3` (`scripts/table_strips.py` does this
  for any object id).
- A display Marker dropped entirely appears only as a Nougat fragment (§5c).

### 5b. Tables

```bash
$PY -B scripts/inspect_tables.py 0 4 /tmp/tab.png         # context crops of the first 4 unrecorded Table objects + Marker rows + model rows
$PY -B scripts/table_strips.py mybook:p0706-table-3 3 /tmp/s706_ 6 -90   # 3× page-render strips of the bbox; last arg rotates (landscape tables)
$PY -B - <<'EOF'
import sys;sys.path.insert(0,'scripts');import record_manual as rm
rm.table('mybook:p0066-table-9',[["Species","Mole fraction"],["H₂","0.1944"],["Total","1.0001"]],
         caption='TABLE 2.2 Sample STANJAN result',footnotes=['Source: …'],reason='Direct source-crop inspection of every cell: …')
rm.classify('mybook:p0254-table-6','Caption',caption_for='mybook:p0254-table-7',reason='object is only the caption line')
rm.classify('mybook:p0760-table-1','Text',reason='two-column index page laid out as a grid; not a data table')
EOF
```
Cells are strings (keep signs, exponents, units, digit counts; blanks are not zeros). Flatten
two-level headers into the column names, fold unit sub-rows into row labels, merge wrapped labels
into one cell, and say so in `reason`. `unresolved=[...]` only for cells you could not read.
Every Table object needs either a `table` record or a `classify` record. The model's table verdicts
are held unresolved whenever they change the row count or the numeric inventory; treat them as a
second reading, not as an answer. Nougat produces nothing for dense/rotated appendix tables — there
your inspection is the second reading.

### 5c. Nougat-only fragments (`unmatched_math`)

`triage_math.py` settles most fragments deterministically before any model verdict: a fragment whose
symbol sequence is contained in a display on the same assembled page is *anchored*; ≤5 tokens is an
*inline symbol*; an empty Nougat block is rejected (the model hallucinates an equation into it).
The rest:
```bash
$PY -B scripts/inspect_fragments.py 0 6 /tmp/fr_    # 2× page renders + Nougat text + the page's displays
$PY -B - <<'EOF'
import sys;sys.path.insert(0,'scripts');import record_manual as rm
rm.fragment('mybook:p0086:nougat-only-3','nougat',anchor="$dp = -\\rho u du$",reason='present inline in the reading copy; anchored')   # anchor must occur exactly once on the page
rm.fragment('mybook:p0482:nougat-only-1','corrected',corrected=r"\int_{\rm cs} u_x\,d\dot{m} = \dot{m}u_e. \tag{10.2}",
            before="momentum-flux term as\n\n![](../../sources/marker/images/_page_481_Figure_15.jpeg)",
            after="momentum-flux term as\n\n$$\\int_{\\rm cs} u_x\\,d\\dot{m} = \\dot{m}u_e. \\tag{10.2}$$\n\n![](../../sources/marker/images/_page_481_Figure_15.jpeg)",
            reason='eq. (10.2) dropped by Marker; inserted from the source')                    # before must occur exactly once in parsed/pages/NNNN.md
rm.fragment('mybook:p0108:nougat-only-4','not_in_source',reason='Nougat repetition artefact')
EOF
```

### 5d. Prose

Not model-edited, by policy. A unique literal patch found during inspection:
`rm.text(page,[("before","after")],reason=...)` (the `before` string must occur once on the page).

### 5e. Figures

The model describes every figure/picture crop (`parsed/FIGURES.md`); descriptions at medium/low
confidence stay listed in `reconciliation/unresolved.json` and the crop is the authority. Only
topology-like figures are transcribed (§6). Blank chapter-end pages detected as "pictures" are a
known harmless leftover.

## 6. Schematics (Mermaid)

Flow/feed-system diagrams go into `curated/schematics/<figure>.mmd`, rendered by
`scripts/render_schematics.py curated/schematics/` (Graphviz → `.svg/.png/.dot` + `render-audit.json`
listing every node and edge). The renderer accepts a deliberately small subset and **raises** on
anything else rather than dropping connections: `flowchart TD|LR|…`, `subgraph id["label"] … end`,
nodes `id["label"]`, junctions `id((" "))`, edges `-->`, `<-->`, `-.-` (shaft/gear coupling), an
optional edge label `-->|"label"|`, **one edge per line**, nodes declared before they are used, no
`-.->`, no `(("x"))` circles. Write a `README.md` in the directory saying which figures were
transcribed, from which page, and what was deliberately left out.

## 7. Per-book hooks

- `scripts/triage_math.py` `T_FIX`: glyph normalisation used **for comparison only** (the print's
  script/Fraktur letters that both OCR engines misread). The shipped list is Hill & Peterson's; prune
  or extend it for your book — a wrong entry only makes the comparator agree or disagree, it never
  changes published text.
- `scripts/publish_notation.py`: rewrites glyphs in the published files; **opt-in** via
  `"notation_rules": "hillpeterson"` in `books.json` (add your own key + rule list otherwise it is a
  no-op). Only rewrite glyphs that are unambiguous in the whole book; document the rule in
  INDEX-notes and it is recorded in `reconciliation/notation-normalisation.json`.
- Equation-label regexes (`extract.py` `printed_labels`, `reconcile.py` `LABEL`) accept `\tag{…}`,
  `(13)`, `(2–1)`, `(5.43)`, `(IV.10)`, primed/lettered variants; extend if the book numbers
  equations differently.
- `finish.py` `KINDS` (default `math, table, unmatched_math, figure`) and the docker GPU index.

## 8. Finalise and publish

```bash
bash finalize.sh      # augment_tables → triage → assemble → promote_agreement_placements → fix_placements → assemble → triage → assemble → publish_book → publish_notation
```
Two assembles are needed because fragment anchors are checked against the page *as just assembled*
(with placements applied). `promote_agreement_placements.py` turns still-unplaced agreement
corrections into explicit placements; `fix_placements.py` resolves corrections whose Marker object
spans several `$$` blocks (multi-line displays) by recording a unique `placement_before/after`.

Then check, in this order:
1. `reconciliation/publication-summary.json`: `required_source_review_status` has only `reviewed`;
   `counts`; `unresolved_records`.
2. `reconciliation/unresolved.json`: must contain **no** `equation`/`Table`/`table` entries; figure
   descriptions at medium confidence are acceptable and are said so in INDEX-notes.
3. Relative links (the only "broken" hits should be LaTeX `[…](t)` inside math):
   ```python
   import re;from pathlib import Path;root=Path('.');bad=0
   for md in list(root.glob('*.md'))+list((root/'parsed').glob('*.md'))+list((root/'parsed/chapters').glob('*.md'))+list((root/'parsed/tables').glob('*.md')):
       for m in re.finditer(r'\]\(([^)\s]+)\)',md.read_text()):
           h=m.group(1)
           if h.startswith(('http','#')) or re.match(r'^[a-z](?:\)|$)',h):continue
           bad+= not (md.parent/h.split('#')[0]).resolve().exists()
   print('broken',bad)
   ```
4. `INDEX.md`: header counts, chapter table (printed and PDF pages), INDEX-notes present.
5. If the book belongs to a corpus index (`EngineeringPhysics/build_corpus_index.py`), add it to the
   `for slug,… in [...]` loop and run `python3 build_corpus_index.py` — the row is derived from the
   publication summary, `parsed/coverage.json`, `parsed/tables.json`, `sources/page-map.json`.
6. Keep a `STATUS.md` in the work dir (it is copied to `<root>/provenance/TASK-HISTORY.md` at publish
   time, together with every script and `books.json`). Log what was systematic, what was a print
   slip, and timestamps.

**Done means:** every required job reviewed, 0 unresolved equation/table records, 0 broken links,
INDEX-notes written, corpus index refreshed. Do not infer completion from counts of files — read
`publication-summary.json` and `unresolved.json`.

## 9. Failure modes already met (and their fixes, all in the shipped scripts)

- Marker: drops result lines of worked examples, boxes, forward/reverse rate constants, captions of
  annotated balances, equation labels, the word joining two displays on one line, whole displays
  next to figures; reads script/Fraktur glyphs as other letters, `v̄` as `ν̄`, species subscripts as
  zeros, Cyrillic look-alikes in tables; emits rotated tables column-wise or as multi-line dumps;
  closes radicals early. Nougat: garbles engineering typography (I↔l, ν↔v), produces empty
  display blocks, repetition artefacts, and nothing at all for dense tables.
- The VLM: hallucinates an equation into an empty Nougat block (rejected before it sees them);
  over-escapes LaTeX or runs to the length limit (left `failed`, inspected directly); calls clean
  crops "unreadable"; changes table row counts (held). Its confidence is not evidence.
- `simple_tokens` must keep command boundaries (`\kappa a`, not `\kappaa`), canonicalise primes and
  sub/superscript order, normalise arrows to one symbol *before* unwrapping `\mathrm{}`; fragment
  anchoring must use the reconciled page, not the raw Marker page, after corrections are placed.
- `augment_tables.py` re-added caption-census candidates as duplicate tables until classified
  objects were skipped; `publish_book.py` chapter ranges were wrong until the roman-folio rule was
  ignored in `pdf_of`.
- A second finisher run after a classification review re-reviewed hundreds of jobs (fingerprints
  changed) — wasted GPU time, no harm.
- Background waiters can be killed by the machine's memory guard; the OCR/finisher processes survive.
  Poll `OCR-STATE.txt` / `finish-state.json` rather than trusting a waiter.

## 10. What each script does

| script | role |
|---|---|
| `inventory.py` | PDFium native text, 1× renders (`sources/renders`), hashes, `sources/source.json` |
| `marker_book.py` | Marker in resumable 16-page chunks (`sources/marker/chunks`), `--no-force-ocr` for born-digital |
| `extract.py` | Marker block tree → `parsed/objects.json` (Equation/Table/Figure/Picture/Caption), page files, crops, tables, inline math |
| `nougat_pages.py` | Nougat per page with raw tokens (`sources/nougat/pages/NNNN.mmd` + metadata) |
| `math_tokens.rs` | conservative LaTeX token comparator used by reconcile (build: `rustc -O`) |
| `reconcile.py` | page-local alignment of Marker displays with Nougat, statuses, fragments, review jobs |
| `catalog_book.py` | folio rules from running heads (+ your checkpoints), page map, book identity |
| `augment_tables.py` | caption census; applies classification reviews and reviewed captions |
| `vision_review.py` | one VLM job: prompt + grammar → verdict record |
| `finish.py` | the bounded model pass (§3) |
| `triage_math.py` | verdict re-derivation, two-readings rule, fragment anchoring → `curated/triage.json`, `agreement-review.json` |
| `inspect_sheet.py`, `inspect_tables.py`, `inspect_fragments.py`, `table_strips.py` | render what you must look at |
| `record_manual.py` | `math`, `table`, `text`, `classify`, `fragment` → `curated/manual-review.json`, `object-classification-review.json` |
| `promote_agreement_placements.py`, `fix_placements.py` | turn corrections into unique page placements |
| `assemble.py` | applies verdicts by precedence → `parsed/reconciled-pages`, `book-reconciled.md`, ledgers, `publication-summary.json`, `unresolved.json` |
| `publish_book.py` | `INDEX.md`, `EQUATIONS.md`, `TABLES.md`, `FIGURES.md`, chapter files, `toc.json`, `provenance/` |
| `publish_notation.py` | opt-in glyph pass (§7) |
| `render_schematics.py` | Mermaid subset → Graphviz (§6) |

Worked examples of every step, with the decisions and their reasons, are in the work directories
`humble-work/`, `williams-work/`, `turns-work/`, `hillpeterson-work/` (each `STATUS.md`) and in each
corpus's `provenance/` and `curated/` directories.
