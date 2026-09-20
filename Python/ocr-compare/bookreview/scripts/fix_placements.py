#!/usr/bin/env python3
"""Resolve 'placement unresolved' corrections: when Marker's JSON object latex spans
several $$ blocks in the page Markdown (multi-line displays), assemble.py cannot
match it to a single block. For each such direct-review record, find the run of
consecutive display blocks in the page body whose concatenated symbols equal the
object's latex (or contain it) and record an explicit unique placement region
(placement_before -> placement_after) on the manual-review item."""
import json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import record_manual as rm
from reconcile import MATH
from triage_math import loose_norm,simple_tokens
root=rm.ROOT;book=rm.BOOK
HEADER='OCR transcription; consult source images for mathematical authority.\n\n'
unres=json.loads((root/'reconciliation/unresolved.json').read_text())
targets={u['id'] for u in unres if u.get('status','').startswith('source-reviewed candidate retained in ledger; placement unresolved')}
objs=rm.objects();data=rm.load();fixed=[];failed=[]
for it in data['items']:
    if it['id'] not in targets or 'choice' not in it:continue
    obj=objs.get(it['id']);page=it['pdf_page']
    body=(root/f'parsed/pages/{page:04d}.md').read_text().split(HEADER,1)[-1]
    want=re.sub(r'\s+','',loose_norm(obj['latex'] if obj else ''))
    INLINE=re.compile(r'\$\$(.*?)\$\$|\\\[(.*?)\\\]|(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)',re.S)
    def region_norm(text):
        # keep only the mathematics of the region (display + inline); prose/annotations/labels are dropped
        spans=[next(g for g in m.groups() if g is not None) for m in INLINE.finditer(text)]
        t=' '.join(spans)
        t=re.sub(r'\\tag\*?\{[^{}]*\}','',t)
        return re.sub(r'\s+','',loose_norm(t))
    blocks=[(m.start(),m.end(),m.group(1) if m.group(1) is not None else m.group(2)) for m in MATH.finditer(body)]
    paras=[m.end() for m in re.finditer(r'\n\n',body)]+[len(body)]
    found=None
    for i in range(len(blocks)):
        b0=blocks[i][0]
        ends=[e for e in paras if e>blocks[i][1]][:10]
        for e in ends:
            reg=body[b0:e].rstrip()
            rn=region_norm(reg)
            if want and rn.startswith(want):found=(b0,b0+len(reg));break
            if len(rn)>3*len(want)+80:break
        if found:break
    if not found:
        from difflib import SequenceMatcher
        for i in range(len(blocks)):
            b0=blocks[i][0];ends=[e for e in paras if e>blocks[i][1]][:10]
            for e in ends:
                reg=body[b0:e].rstrip();rn=region_norm(reg)
                if len(rn)>=0.9*len(want) and want:
                    m=SequenceMatcher(None,rn,want,autojunk=False).find_longest_match(0,len(rn),0,len(want))
                    if m.size>=0.93*len(want) and m.a==0 and m.b==0:found=(b0,b0+len(reg));break
                if len(rn)>3*len(want)+80:break
            if found:break
    if not found:failed.append(it['id']);continue
    region=body[found[0]:found[1]]
    if body.count(region)!=1:failed.append(it['id']);continue
    chosen=it['corrected'] if it['choice']=='corrected' else (obj['latex'] if it['choice']=='marker' else None)
    if not chosen:failed.append(it['id']);continue
    it['placement_before']=region;it['placement_after']='$$'+chosen.strip()+'$$'
    it['placement_note']='Marker rendered this display as several consecutive blocks/lines in the page Markdown; the whole region is replaced by the reviewed reading.'
    fixed.append(it['id'])
rm.save(data)
print(json.dumps(dict(fixed=len(fixed),failed=failed)))
