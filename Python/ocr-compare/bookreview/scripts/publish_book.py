#!/usr/bin/env python3
"""Portable navigation after assembly: tables (CSV/JSON/MD), equation and
figure catalogues, chapter files from curated/contents.json, INDEX.md and
provenance. Generalized from humble-work/scripts/publish_humble.py."""
import csv,json,re,shutil
from collections import Counter,defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent
book=json.loads((HERE/'books.json').read_text())['books'][0];root=Path(book['root']);bid=book['id']
def write(p,data):p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
summary=json.loads((root/'reconciliation/publication-summary.json').read_text())
objects=json.loads((root/'parsed/objects.json').read_text())
equations=json.loads((root/'reconciliation/equations.json').read_text())
pagemap={x['pdf_page']:x['printed_page'] for x in json.loads((root/'sources/page-map.json').read_text())['pages']}
manualpath=root/'curated/manual-review.json'
manualrecord=json.loads(manualpath.read_text()) if manualpath.exists() else {}
manual={r['id']:dict(r,reviewer=manualrecord.get('reviewer','direct source-image inspection')) for r in manualrecord.get('items',[])}
ledgers={}
for p in (root/'reconciliation/pages').glob('*.json'):
    for e in json.loads(p.read_text())['edits_and_decisions']:ledgers[e['id']]=e
# ---- tables
table_index=[]
for obj in objects:
    if obj['kind']!='Table':continue
    reviewpath=root/'parsed/tables'/f'{obj["slug"]}-source-review.json'
    review=json.loads(reviewpath.read_text()) if reviewpath.exists() else None
    if obj['id'] in manual:review=manual[obj['id']]
    selected=review['rows'] if review and review.get('confidence')=='high' and not review.get('unresolved') and review.get('rows') else obj['rows']
    status='source-image reviewed cell transcription' if selected is not obj['rows'] else 'provisional OCR cells'
    rel=f'parsed/tables/{obj["slug"]}-selected.csv'
    with (root/rel).open('w',newline='') as f:csv.writer(f).writerows(selected)
    table_index.append(dict(id=obj['id'],pdf_page=obj['pdf_page'],printed_page=pagemap.get(obj['pdf_page']),
        caption=(review or {}).get('caption',obj.get('caption','')),
        source_crop=review.get('image',obj['crop']) if review else obj['crop'],raw_source_crop=obj['crop'],
        raw_csv=f'parsed/tables/{obj["slug"]}.csv',raw_html=f'parsed/tables/{obj["slug"]}.html',
        selected_csv=rel,selected_rows=selected,status=status,review_method=(review or {}).get('reviewer','local source-image model' if review else None),
        footnotes=(review or {}).get('footnotes',[]),unresolved=(review or {}).get('unresolved',[]),
        raw_cells_with_spans=obj.get('cells',[]),review=review))
write(root/'parsed/tables.json',table_index)
tablemd=[f'# {book["title"]} — table data','',
    'CSV cells are strings: preserve signs, exponents, units and significant digits. Blank cells are not zeros. '
    'The selected view uses high-confidence source-image review where available and marks raw OCR otherwise; '
    '[tables.json](tables.json) carries footnotes, unresolved cells, raw span metadata and the full review record.','',
    '| PDF page | Printed | Table / caption | Status | Data | Notes | Source |','|---:|---:|---|---|---|---|---|']
for t in table_index:
    notes_path=t['selected_csv'].replace('-selected.csv','-source-review.md')
    notes=f'[Review](../{notes_path})' if (root/notes_path).exists() else '—'
    tablemd.append(f'| {t["pdf_page"]} | {t["printed_page"] or ""} | {(t["caption"] or "(no caption detected)").replace("|","/")[:160]} | {t["status"]} | [CSV](../{t["selected_csv"]}) | {notes} | [Image](../{t["source_crop"]}) |')
(root/'parsed/TABLES.md').write_text('\n'.join(tablemd)+'\n')
# ---- equations catalogue
eq_index=[]
for row in equations['equations']:
    led=ledgers.get(row['id'],{})
    chosen=led.get('selected_latex') or row.get('marker')
    eq_index.append(dict(id=row['id'],pdf_page=row['pdf_page'],printed_page=pagemap.get(row['pdf_page']),
        printed_labels=row.get('printed_labels',[]),latex=chosen,marker=row.get('marker'),nougat=row.get('nougat'),
        comparison=row['status'],decision=led.get('status','no ledger entry'),crop=row['crop']))
write(root/'parsed/equations.json',eq_index)
eqmd=[f'# {book["title"]} — display equations','',
      f'{len(eq_index)} display objects detected by Marker; `latex` is the reading-copy form after source review (Marker retained unless a high-confidence source review replaced it). '
      'Comparison = conservative Marker/Nougat token comparison. Not a proof of the printed mathematics.','']
bychap=defaultdict(list)
for e in eq_index:bychap[e['pdf_page']].append(e)
for n in sorted(bychap):
    eqmd.append(f'## PDF page {n}'+(f' · printed {pagemap.get(n)}' if pagemap.get(n) else ''))
    for e in bychap[n]:
        lab=(' ('+', '.join(e['printed_labels'])+')') if e['printed_labels'] else ''
        eqmd+=['',f'`{e["id"]}`{lab} — {e["decision"]} — [crop](../{e["crop"]})','',f'$$\n{e["latex"]}\n$$']
    eqmd.append('')
(root/'parsed/EQUATIONS.md').write_text('\n'.join(eqmd)+'\n')
# ---- figures catalogue
reviewed=json.loads((root/'parsed/visual-objects-reviewed.json').read_text()) if (root/'parsed/visual-objects-reviewed.json').exists() else []
rv={o['id']:o for o in reviewed}
fig_index=[]
for obj in objects:
    if obj['kind'] not in ['Figure','Picture']:continue
    v=rv.get(obj['id'],{}).get('source_review')
    fig_index.append(dict(id=obj['id'],kind=obj['kind'],pdf_page=obj['pdf_page'],printed_page=pagemap.get(obj['pdf_page']),
        caption=obj.get('caption',''),crop=obj['crop'],context_crop=obj.get('context_crop'),
        object_type=(v or {}).get('object_type'),description=(v or {}).get('description'),visible_labels=(v or {}).get('visible_labels'),
        axes=(v or {}).get('axes'),review_confidence=(v or {}).get('confidence'),review_unresolved=(v or {}).get('unresolved')))
write(root/'parsed/figures.json',fig_index)
figmd=[f'# {book["title"]} — figures and pictures','',
       f'{len(fig_index)} figure/picture crops extracted by Marker with the nearest caption. Descriptions, visible labels and axes come from the local vision model where reviewed (not independent verification).','',
       '| PDF page | Printed | Kind | Caption | Model description | Crop |','|---:|---:|---|---|---|---|']
for f in fig_index:
    figmd.append(f'| {f["pdf_page"]} | {f["printed_page"] or ""} | {f["kind"]} | {(f["caption"] or "").replace("|","/")[:120]} | {(f["description"] or "").replace("|","/")[:160]} | [image](../{f["context_crop"] or f["crop"]}) |')
(root/'parsed/FIGURES.md').write_text('\n'.join(figmd)+'\n')
# ---- chapters
contents=json.loads((root/'curated/contents.json').read_text()) if (root/'curated/contents.json').exists() else []
rules=json.loads((root/'sources/page-map.json').read_text())['rules']
def pdf_of(printed):
    for r in rules:
        if r.get('style')=='roman' or 'blank' in str(r.get('printed_equals','')):continue   # arabic folios only
        n=printed+r['offset']
        if r['pdf_from']<=n<=r['pdf_to']:return n
    return None
toc=[];chapterdir=root/'parsed/chapters';chapterdir.mkdir(exist_ok=True)
for i,c in enumerate(contents):
    start=c.get('pdf_start') or pdf_of(c['printed_start']);end=(contents[i+1].get('pdf_start') or pdf_of(contents[i+1]['printed_start']))-1 if i+1<len(contents) else book['expected_pdf_pages']
    if start is None:continue
    slug=f'{str(c["number"]).lower()}-'+re.sub('[^a-z0-9]+','-',c['title'].lower()).strip('-')
    rel=f'parsed/chapters/{slug}.md'
    rows=[f'# {c["number"]}. {c["title"]}','',f'Printed start {c["printed_start"]}; PDF pages {start}–{end}.','',
          'Each page links the reading transcription, raw OCR, source image and decision ledger.','']
    for n in range(start,end+1):rows.append(f'- [PDF page {n}](../reconciled-pages/{n:04d}.md)')
    (root/rel).write_text('\n'.join(rows)+'\n')
    toc.append(dict(chapter=c['number'],title=c['title'],printed_start=c['printed_start'],pdf_start=start,pdf_end=end,path=rel,
        locator_evidence=c.get('evidence','printed start read from the book contents pages; PDF location via the recorded folio rules')))
write(root/'toc.json',toc)
# ---- INDEX
counts=summary.get('counts',{});uc=summary.get('unreviewed_context',{})
kinds=Counter(o['kind'] for o in objects)
display_ids={o['id'] for o in objects if o['kind']=='Equation'}
direct_display=len(display_ids&manual.keys());direct_tables=sum(t['id'] in manual for t in table_index)
index=[f'# {book["title"]}'+(f': {book["subtitle"]}' if book.get('subtitle') else ''),'',
       f'{", ".join(book["authors"])}. {book["edition"]}','',
       f'Source: {book.get("source_kind","")}. {book["expected_pdf_pages"]} PDF pages.','',
       f'All {summary["marker_pages"]}/{book["expected_pdf_pages"]} PDF pages have Marker output and {summary["compared_pages"]}/{book["expected_pdf_pages"]} an independent Nougat comparison. '
       f'Review status: **{summary["status"]}**; {summary["unresolved_records"]} unresolved records. '
       'Counts measure extraction/review coverage, not proof of error-free text or physics.','',
       f'Detected: {kinds.get("Equation",0)} display equations, {json.loads((root/"parsed/coverage.json").read_text())["inline_math"]} inline expressions, {kinds.get("Table",0)} tables, {kinds.get("Figure",0)+kinds.get("Picture",0)} figures/pictures. '
       f'Source-review counts: {counts.get("equations_source_reviewed",0)} displays retained by review, {counts.get("equations_corrected",0)} corrected, {counts.get("equations_ocr_agreement",0)} by independent OCR agreement; '
       f'{sum(t["status"].startswith("source-image") for t in table_index)}/{len(table_index)} tables with reviewed cells; {direct_display} displays and {direct_tables} tables directly inspected by the session agent.','',
       f'General prose: {uc.get("text",0)} pages retain complete OCR without an accepted whole-page source review (policy: no automatic prose edits).','',
       '- [Reading transcription](parsed/book-reconciled.md)',
       '- [Display equations catalogue](parsed/EQUATIONS.md) · [equations.json](parsed/equations.json)',
       '- [Table data: CSV, JSON, footnotes and source crops](parsed/TABLES.md) · [tables.json](parsed/tables.json)',
       '- [Figures and pictures with model descriptions](parsed/FIGURES.md) · [figures.json](parsed/figures.json)',
       '- [Inline math inventory](parsed/inline-math.json) · [headings](parsed/headings.json)',
       '- [Per-page source map](sources/page-map.json) · [chapter map](toc.json)',
       '- [Review coverage](reconciliation/publication-summary.json) · [unresolved items](reconciliation/unresolved.json) · [unreviewed context](reconciliation/unreviewed-context.json)',
       '- [Review policy](curated/review-scope.json) · [direct source-image checks](curated/manual-review.json)',
       '- [Raw Marker backbone](parsed/book.md) · [raw Nougat pages](sources/nougat/pages/)',
       '- [How this corpus was made](provenance/README.md)','']
if toc:
    index+=['| Chapter | Title | Printed start | PDF pages |','|---|---|---:|---:|']
    for c in toc:index.append(f'| {c["chapter"]} | [{c["title"]}]({c["path"]}) | {c["printed_start"]} | {c["pdf_start"]}–{c["pdf_end"]} |')
extra=root/'curated/INDEX-notes.md'
if extra.exists():index+=['',extra.read_text().strip()]
(root/'INDEX.md').write_text('\n'.join(index)+'\n')
prov=root/'provenance';prov.mkdir(exist_ok=True)
for filename in ['finish.py','run_ocr.sh','STATUS.md','review-model.json','calibration-acceptance.json']:
    src=HERE.parent/filename
    if src.exists():shutil.copy2(src,prov/('TASK-HISTORY.md' if filename=='STATUS.md' else filename))
for s in HERE.glob('*.py'):shutil.copy2(s,prov/s.name)
shutil.copy2(HERE/'books.json',prov/'books.json')
(prov/'README.md').write_text(f'# Reuse and provenance — {book["title"]}\n\n'
    'Reading requires only Markdown/JSON/CSV/image support; no model, GPU or service is needed.\n\n'
    f'Source: {book.get("source_kind","")}. The PDF was inventoried with PDFium (native text, 1x renders, hashes). '
    f'Marker ran in resumable 16-page chunks ({"forced OCR" if book["force_ocr"] else "native text layer"}), rendering Markdown and a JSON block tree; '
    'Nougat ran independently on every page with raw tokens, per-page Markdown and hash-checked completion records. '
    'Objects keep page identity, bounds, source crops, equations, tables and raw HTML with cell spans. '
    'Display equations were aligned page-locally and compared with a conservative token comparison (math_tokens.rs). '
    'Differences, tables, Nougat-only fragments and figure crops were reviewed against source images by the local vision model recorded in review-model.json '
    '(bounded calibration inherited from the Humble run: calibration-acceptance.json). Direct source-image inspections in curated/manual-review.json override model verdicts. '
    'Whole-page prose was not model-edited. All raw outputs are retained; relative links are used for reading products.\n\n'
    'Scripts in this directory are the exact task-local copies used; books.json records source/corpus paths.\n')
print(json.dumps(dict(tables=len(table_index),reviewed_tables=sum(t['status'].startswith('source-image') for t in table_index),equations=len(eq_index),figures=len(fig_index),chapters=len(toc))))
