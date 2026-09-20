#!/usr/bin/env python3
"""Prepare source-image review jobs from independent per-page OCR candidates."""
import argparse
import difflib
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image, ImageDraw
from bs4 import BeautifulSoup
import pypdfium2 as pdfium
from extract import walk, write

HERE=Path(__file__).resolve().parent
MATH=re.compile(r'\\\[(.*?)\\\]|\$\$(.*?)\$\$',re.S)
INLINE=re.compile(r'\\\((.*?)\\\)|(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)',re.S)
LABEL=re.compile(r"\\tag\*?\{([^{}]+)\}|\(([IVX]+\.)?\s*(\d+(?:[.\u2013-]\d+)?[a-z]?'*)\)\s*$")
TAG=re.compile(r'\\tag\*?\{([^{}]+)\}')

def labels(s):return [a or b+c for a,b,c in LABEL.findall(s)]
def clean_math(s):
    # A trailing (1.25) could be mathematical data, not an equation number.
    # Only explicit LaTeX tags are safe to remove for formula comparison.
    return TAG.sub('',s).strip().rstrip('.')
def similarity(a,b):
    return difflib.SequenceMatcher(None,re.sub(r'\s+','',clean_math(a)),re.sub(r'\s+','',clean_math(b)),autojunk=False).ratio()
def words(s):
    s=MATH.sub(' ',s);s=INLINE.sub(' ',s)
    s=re.sub(r'!\[[^\]]*\]\([^)]*\)',' ',s)
    return re.findall(r"[A-Za-zÀ-ÿ]+(?:['’-][A-Za-zÀ-ÿ]+)*",s.lower())
def fingerprint(data):return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def sheet(root,job,out):
    images=[]
    for item in job['items']:
        img=Image.open(root/item['crop']).convert('RGB')
        if img.width>1400:img=img.resize((1400,round(img.height*1400/img.width)))
        images.append((item['id'],img))
    width=max(im.width for _,im in images)
    result=Image.new('RGB',(max(width,800),sum(im.height+35 for _,im in images)), 'white')
    draw=ImageDraw.Draw(result);y=0
    for key,im in images:
        draw.text((8,y+8),key,fill='black');result.paste(im,(0,y+30));y+=im.height+35
    result.save(out)

def prepare(book):
    root=Path(book['root']);out=root/'reconciliation'
    for folder in ['jobs','images','page-diffs']:(out/folder).mkdir(parents=True,exist_ok=True)
    objects=json.loads((root/'parsed/objects.json').read_text())
    bypage=defaultdict(list)
    for obj in objects:bypage[obj['pdf_page']].append(obj)
    records=[];jobs=[];comparison=[];unmatched=[];page_reports=[]
    doc=pdfium.PdfDocument(book['pdf'])
    def add_job(kind,page,items,image_path=None):
        key=f'{book["id"]}-p{page:04d}-{kind}-{len(jobs):05d}'
        job=dict(id=key,book=book['id'],kind=kind,pdf_page=page,items=items,
                 source_pdf_sha256=json.loads((root/'sources/source.json').read_text())['sha256'])
        path=out/'images'/f'{key}.png'
        if image_path:
            job['image']=image_path
        elif kind=='math':
            sheet(root,job,path);job['image']=str(path.relative_to(root))
        else:
            pageobj=doc[page-1];bitmap=pageobj.render(scale=2.5)
            bitmap.to_pil().save(path);bitmap.close();pageobj.close()
            job['image']=str(path.relative_to(root))
        job['image_sha256']=hashlib.sha256((root/job['image']).read_bytes()).hexdigest()
        job['fingerprint']=fingerprint(job)
        write(out/'jobs'/f'{key}.json',job);jobs.append(job)

    for n in range(1,len(doc)+1):
        np=root/'sources/nougat/pages'/f'{n:04d}.mmd'
        mp=root/'parsed/pages'/f'{n:04d}.md'
        if not (np.is_file() and mp.is_file()):continue
        nougat=np.read_text();marker=mp.read_text()
        nm=[dict(latex=a or b,labels=labels(a or b),start=m.start(),end=m.end())
            for m in MATH.finditer(nougat) for a,b in [m.groups()]]
        used=set()
        for obj in bypage[n]:
            if obj['kind']!='Equation':continue
            candidates=[]
            for i,other in enumerate(nm):
                if i in used:continue
                score=similarity(obj['latex'],other['latex'])
                same=bool(set(obj['printed_labels'])&set(other['labels']))
                if same:score+=1
                candidates.append((score,i))
            score,i=max(candidates,default=(0,None))
            other=nm[i] if i is not None and score>=.36 else None
            if other:used.add(i)
            row=dict(obj,marker=obj['latex'],nougat=other['latex'] if other else None,
                     alignment='same printed label' if score>=1 else 'page-local token similarity' if other else 'unmatched',
                     match_score=score,status='awaiting comparison')
            records.append(row)
            if other:
                comparison.append('\t'.join([row['id'],clean_math(row['marker']).encode().hex(),clean_math(row['nougat']).encode().hex()]))
            else:row['status']='marker_only'
        for i,other in enumerate(nm):
            if i not in used:
                item=dict(id=f'{book["id"]}:p{n:04d}:nougat-only-{i}',pdf_page=n,
                          nougat=other['latex'],marker=None,status='nougat_only',
                          alignment='No matching Marker display object')
                unmatched.append(item)
        mw,nw=words(marker.split('OCR transcription; consult source images for mathematical authority.\n\n')[-1]),words(nougat)
        # Diff is an inventory, not a claim all differences are errors. Equations,
        # references, hyphenation and dropped headers can change paragraph tokens.
        matcher=difflib.SequenceMatcher(None,mw,nw,autojunk=False)
        spans=[]
        for tag,a,b,c,d in matcher.get_opcodes():
            if tag=='equal':continue
            spans.append(dict(marker=' '.join(mw[max(0,a-8):min(len(mw),b+8)]),
                              nougat=' '.join(nw[max(0,c-8):min(len(nw),d+8)]),
                              marker_range=[a,b],nougat_range=[c,d],kind=tag))
        meta=json.loads((root/'sources/nougat/metadata'/f'{n:04d}.json').read_text())
        report=dict(pdf_page=n,word_similarity=matcher.ratio(),spans=spans,
                    nougat_quality_flags=meta['quality_flags'],native_text=str((root/'sources/native/pages'/f'{n:04d}.txt').relative_to(root)))
        write(out/'page-diffs'/f'{n:04d}.json',report);page_reports.append(report)
        # Save all source text for page-level review. Judge only differences;
        # one model need not be selected wholesale for a mixed-quality page.
        # Prose-only token equality does not imply inline-math equality. Review
        # every page's text/inline content, even when this coarse diff is empty.
        add_job('text',n,[dict(id=f'{book["id"]}:p{n:04d}:text',
            marker=marker,nougat=nougat,
            source_native=(root/'sources/native/pages'/f'{n:04d}.txt').read_text(),
            notes=meta['quality_flags'])])
    result=subprocess.run([str(HERE/'math_tokens')],input='\n'.join(comparison)+'\n' if comparison else '',text=True,capture_output=True,check=True)
    indexed={r['id']:r for r in records}
    for line in result.stdout.splitlines():
        key,status,distance,total=line.split('\t');row=indexed[key]
        explicit_nougat_labels=TAG.findall(row['nougat'])
        if row['printed_labels'] and explicit_nougat_labels and set(row['printed_labels'])!=set(explicit_nougat_labels):
            status='label_disagreement'
        row.update(status=status,token_edit_distance=int(distance),max_tokens=int(total))
    pending=defaultdict(list)
    for row in records:
        if row['status'] not in ['exact','format_only']:
            pending[row['pdf_page']].append({k:row[k] for k in ['id','marker','nougat','crop','printed_labels','alignment']})
    for page,items in pending.items():
        # Limit height as well as count; preserve source crop resolution.
        batch=[];height=0
        for item in items:
            im=Image.open(root/item['crop']);h=im.height+35
            if batch and (len(batch)>=3 or height+h>2200):
                add_job('math',page,batch);batch=[];height=0
            batch.append(item);height+=h
        if batch:add_job('math',page,batch)
    for row in unmatched:
        add_job('unmatched_math',row['pdf_page'],[row])
    for obj in objects:
        if obj['kind'] in ['Figure','Picture','Table']:
            # Marker can crop a real table after just its first few rows (e.g.
            # Table 3.1). Review tables against the entire source page so the
            # reviewer can recover rows outside the detected box.
            table_object=obj['kind']=='Table'
            add_job('table' if table_object else 'figure',obj['pdf_page'],[dict(obj)],
                    None if table_object else obj.get('context_crop',obj['crop']))
    write(out/'equations.json',dict(equations=records,nougat_unmatched=unmatched))
    write(out/'jobs.json',jobs)
    summary=dict(pages_compared=len(page_reports),expected_pages=len(doc),
                 equations=len(records),equation_status=dict(Counter(r['status'] for r in records)),
                 nougat_unmatched=len(unmatched),jobs=len(jobs),job_types=dict(Counter(j['kind'] for j in jobs)))
    write(out/'summary.json',summary)
    print(book['id'],summary,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--book');args=ap.parse_args()
    for book in json.loads((HERE/'books.json').read_text())['books']:
        if not args.book or args.book==book['id']:prepare(book)
