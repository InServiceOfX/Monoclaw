#!/usr/bin/env python3
"""Render 2x page images for Nougat-only fragments that have no settled record, and print the fragment text
with the reconciled page's nearby lines. Usage: inspect_fragments.py START COUNT OUTPREFIX"""
import json,sys,re
from pathlib import Path
import pypdfium2 as pdfium
HERE=Path(__file__).resolve().parent
book=json.loads((HERE/'books.json').read_text())['books'][0];root=Path(book['root'])
start,count,prefix=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
a=json.loads((root/'curated/agreement-review.json').read_text())['items'];m=json.loads((root/'curated/manual-review.json').read_text())['items']
settled={x['id'] for x in a}|{x['id'] for x in m}
jobs=json.loads((root/'reconciliation/jobs.json').read_text());jobs=jobs['jobs'] if isinstance(jobs,dict) else jobs
todo=[it for j in jobs if j['kind']=='unmatched_math' for it in j['items'] if it['id'] not in settled]
sel=todo[start:start+count];pdf=pdfium.PdfDocument(book['pdf'])
print('remaining',len(todo),'showing',start,'..',start+len(sel)-1)
for k,it in enumerate(sel):
    p=it['pdf_page'];pdf[p-1].render(scale=2).to_pil().save(f'{prefix}{k}.png')
    print('==',it['id'],'| PDF',p,'->',f'{prefix}{k}.png');print('  NOUGAT:',(it.get('nougat') or '').replace('\n',' ⏎ ')[:600])
    rp=root/f'parsed/reconciled-pages/{p:04d}.md'
    txt=(rp.read_text().split('review coverage is recorded separately.\n\n',1)[-1]) if rp.exists() else (root/f'parsed/pages/{p:04d}.md').read_text()
    disp=[l for l in txt.splitlines() if l.strip().startswith('$$') or '\\tag' in l]
    print('  PAGE DISPLAYS:',' | '.join(d.strip()[:90] for d in disp)[:900])
