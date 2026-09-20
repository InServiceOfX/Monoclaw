#!/usr/bin/env python3
"""Page map (PDF page -> printed folio) from OCR'd running heads/feet, plus
book identity. Rules are inferred per contiguous region of constant offset and
recorded with their evidence; curated/folio-checkpoints.json (pdf_page ->
printed page, read directly from renders) overrides and is reported."""
import json,re
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
book=json.loads((HERE/'books.json').read_text())['books'][0];root=Path(book['root'])
def write(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
N=book['expected_pdf_pages']
def _roman(n):
    out='';
    for v,sym in [(1000,'m'),(900,'cm'),(500,'d'),(400,'cd'),(100,'c'),(90,'xc'),(50,'l'),(40,'xl'),(10,'x'),(9,'ix'),(5,'v'),(4,'iv'),(1,'i')]:
        while n>=v:out+=sym;n-=v
    return out
ROMAN=re.compile(r'^(?=[ivxlc]+$)m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$')
def folio_candidates(text):
    lines=[l.strip() for l in text.splitlines() if l.strip()]
    cands=[]
    for l in lines[:3]+lines[-3:]:
        l=re.sub(r'^[#*\s]+|[#*\s]+$','',l)
        for tok in re.findall(r'\b\d{1,3}\b',l):
            # accept a bare number at either end of a short line (running head/foot)
            if re.fullmatch(r'\d{1,3}',l) or re.match(r'^\d{1,3}\s',l) or re.search(r'\s\d{1,3}$',l):
                cands.append(int(tok))
        if ROMAN.match(l.lower()):cands.append(l.lower())
    return cands
observed={}
for n in range(1,N+1):
    texts=[]
    for p in [root/'parsed/pages'/f'{n:04d}.md',root/'sources/native/pages'/f'{n:04d}.txt']:
        if p.exists():texts.append(p.read_text().split('mathematical authority.\n\n')[-1])
    c=Counter()
    for t in texts:
        for x in folio_candidates(t):c[x]+=1
    if c:
        val,_=c.most_common(1)[0]
        observed[n]=val
checkpoints={}
cp=root/'curated/folio-checkpoints.json'
if cp.exists():checkpoints={int(k):v for k,v in json.loads(cp.read_text()).items()}
# Dominant arabic offset per page using neighbourhood voting.
offsets={n:n-v for n,v in observed.items() if isinstance(v,int)}
for n,v in checkpoints.items():
    if isinstance(v,int):offsets[n]=n-v
pages=[];rules=[];current=None
for n in range(1,N+1):
    window=[offsets[k] for k in range(n-6,n+7) if k in offsets]
    off=Counter(window).most_common(1)[0][0] if len(window)>=3 else None
    if n in checkpoints:
        printed=checkpoints[n];status='folio read directly from render (checkpoint)'
        off=n-printed if isinstance(printed,int) else None
    elif off is not None and n-off>=1:
        printed=n-off
        status=('OCR folio agrees with local offset' if observed.get(n)==printed else 'inferred from neighbouring folios; not individually verified')
    elif isinstance(observed.get(n),str):
        printed=observed[n];status='roman folio read by OCR';off=None
    else:
        printed=None;status='no folio evidence (front/back matter, blank or figure page)'
    pages.append(dict(pdf_page=n,printed_page=printed,status=status,ocr_folio=observed.get(n)))
    if off is not None:
        if current and current['offset']==off:current['pdf_to']=n
        else:
            current=dict(pdf_from=n,pdf_to=n,offset=off,printed_equals=f'PDF page minus {off}' if off>=0 else f'PDF page plus {-off}');rules.append(current)
    else:current=None
rules=[r for r in rules if r['pdf_to']-r['pdf_from']>=3]
# Explicit, evidence-backed rules (read from renders) override the inference.
explicit=root/'curated/folio-rules.json'
absent=[]
if explicit.exists():
    spec=json.loads(explicit.read_text());rules=spec['rules'];absent=spec.get('absent_printed_folios',[])
    for page in pages:
        n=page['pdf_page'];hit=next((r for r in rules if r['pdf_from']<=n<=r['pdf_to']),None)
        if hit is None:
            page.update(printed_page=None,status='outside every folio rule');continue
        if hit.get('style')=='roman':
            page.update(printed_page=hit.get('roman',{}).get(str(n),None) or _roman(n-hit.get('offset',0)),status='roman front matter by rule: '+hit['evidence']);continue
        printed=n-hit['offset']
        page.update(printed_page=printed,status=('OCR folio agrees with rule' if page.get('ocr_folio')==printed else 'by rule; folio not read on this page')+' — '+hit['evidence'])
write(root/'sources/page-map.json',dict(book=book['id'],pages=pages,rules=rules,checkpoints=checkpoints,absent_printed_folios=absent,explicit_rules=explicit.exists(),
    evidence='Folios read from OCR running heads/feet with neighbourhood voting; checkpoints (if any) were read directly from page renders.',
    ocr_folio_pages=len(observed)))
src=root/'sources/source.json'
if src.exists():
    d=json.loads(src.read_text());d.update({k:v for k,v in book.items() if k!='sha256'});write(src,d)
print(json.dumps(dict(pages=N,ocr_folios=len(observed),rules=rules,checkpoints=len(checkpoints)),indent=1))
