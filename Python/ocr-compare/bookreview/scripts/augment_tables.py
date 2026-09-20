#!/usr/bin/env python3
"""Cross-check table captions; retain tables misclassified as pictures."""
import hashlib,json,re
from collections import defaultdict
from pathlib import Path
import pypdfium2 as pdfium
from extract import walk,text,crop_source,write
HERE=Path(__file__).resolve().parent
book=json.loads((HERE/'books.json').read_text())['books'][0];root=Path(book['root'])
path=root/'parsed/objects.json';objects=json.loads(path.read_text())
classification_path=root/'curated/object-classification-review.json'
if classification_path.exists():
    indexed={o['id']:o for o in objects}
    for review in json.loads(classification_path.read_text())['items']:
        obj=indexed[review['id']]
        assert review['original_kind']=='Table' and review['reviewed_kind'] in ['Caption','Text']
        assert hashlib.sha256((root/review['image']).read_bytes()).hexdigest()==review['image_sha256'], 'Changed classification-review source image'
        if review['reviewed_kind']=='Caption':assert review['caption_for'] in indexed
        obj.setdefault('original_kind',review['original_kind'])
        obj.update(kind=review['reviewed_kind'],classification_review=review)
        if review.get('caption_for'):obj['caption_for']=review['caption_for']
manualpath=root/'curated/manual-review.json'
manual={r['id']:r for r in json.loads(manualpath.read_text())['items']} if manualpath.exists() else {}
for obj in objects:
    reviewed=manual.get(obj['id'],{})
    if reviewed.get('caption') and reviewed.get('confidence')=='high':
        obj.setdefault('raw_caption',obj.get('caption',''))
        obj.update(caption=reviewed['caption'],caption_status='Codex source-image verified caption')
by_page=defaultdict(list)
for obj in objects:by_page[obj['pdf_page']].append(obj)
pattern=re.compile(r'^Table\s+((?:\d+|[A-Z])[.\-]\d+)\b',re.I)
doc=pdfium.PdfDocument(book['pdf']);census=[];additions=[]
for p in sorted((root/'parsed/blocks').glob('*.json')):
    n=int(p.stem)
    for block,_ in walk(json.loads(p.read_text())):
        raw=block.get('html','');caption=text(raw)
        match=pattern.match(caption)
        if not match:continue
        if block.get('block_type')!='Caption' and not re.match(r'^\s*<(?:b|strong)>\s*Table',raw):continue
        label=match[1]
        # Marker classified the sentence "Table 7.3 summarizes ..." below
        # Table 7.2 as a caption. Retain that observation, not a phantom table.
        if re.match(r'^\s+(?:summarizes|shows|compares|lists|provides|gives|presents|contains|illustrates|describes)\b',caption[match.end():],re.I):
            census.append(dict(pdf_page=n,label=label,status='prose-like table reference; not added as a new table'))
            continue
        already=[o for o in by_page[n] if o['kind']=='Table' and pattern.match(o.get('caption','')) and pattern.match(o['caption'])[1]==label]
        if already:
            census.append(dict(pdf_page=n,label=label,status='mapped to Table object',object_ids=[o['id'] for o in already]));continue
        # A caption-census object that direct inspection already classified as the caption line of a
        # source-reviewed grid (curated/object-classification-review.json, caption_for) is not re-added.
        slug_id=f'{book["id"]}:p{n:04d}-table-caption-{label.replace(".","-")}'
        reviewed_caption=[o for o in by_page[n] if o['id']==slug_id and o.get('classification_review')]
        if reviewed_caption:
            census.append(dict(pdf_page=n,label=label,status='caption line; grid is a source-reviewed Table object',object_ids=[reviewed_caption[0].get('caption_for')]));continue
        capbox=block['bbox']
        candidates=[o for o in by_page[n] if o['kind'] in ['Picture','Figure']]
        def distance(o):
            b=o['bbox_top_left_points']
            overlap=max(0,min(b[2],capbox[2])-max(b[0],capbox[0]))
            return max(0,max(b[1],capbox[1])-min(b[3],capbox[3]))+(0 if overlap else 1000)
        obj=min(candidates,key=distance) if candidates else None
        if obj and distance(obj)<100:
            obj.update(original_kind=obj['kind'],kind='Table',caption=caption,rows=[],cells=[],
                status='Table caption adjacent to a picture; awaiting source-image cell transcription')
            additions.append(dict(id=obj['id'],pdf_page=n,label=label,action='reclassified derived object; raw Marker retained'))
        else:
            page=doc[n-1];bbox=[0,0,*page.get_size()];slug=f'p{n:04d}-table-caption-{label.replace(".","-")}'
            crop=root/'parsed/crops'/f'{slug}.png';crop_source(page,bbox,crop);page.close()
            import hashlib
            obj=dict(id=f'{book["id"]}:{slug}',slug=slug,pdf_page=n,kind='Table',bbox_top_left_points=bbox,
                raw_html=raw,rows=[],cells=[],caption=caption,crop=str(crop.relative_to(root)),
                crop_sha256=hashlib.sha256(crop.read_bytes()).hexdigest(),
                status='Caption census candidate; whole-page source crop; awaiting source review')
            objects.append(obj);by_page[n].append(obj)
            additions.append(dict(id=obj['id'],pdf_page=n,label=label,action='added whole-page source review candidate'))
        (root/'parsed/tables'/f'{obj["slug"]}.csv').write_text('')
        (root/'parsed/tables'/f'{obj["slug"]}.html').write_text(obj['raw_html'])
        census.append(dict(pdf_page=n,label=label,status='source-image cell review required',object_ids=[obj['id']]))
jobsfile=root/'reconciliation/jobs.json'
if jobsfile.exists():
    indexed={o['id']:o for o in objects}
    for job in json.loads(jobsfile.read_text()):
        if job['kind']!='figure':continue
        reply=root/'reconciliation/vision'/f'{job["id"]}.json'
        if not reply.exists():continue
        review=json.loads(reply.read_text())
        if review.get('status')!='reviewed' or review.get('job_fingerprint')!=job['fingerprint']:continue
        for result in review['result']['items']:
            obj=indexed.get(result['id'])
            if not obj or obj['kind']=='Table' or result.get('object_type')!='table':continue
            obj.update(original_kind=obj['kind'],kind='Table',rows=[],cells=[],
                table_discovery_review=str(reply.relative_to(root)),
                status='Figure review identified a possible table; awaiting full-page cell transcription')
            (root/'parsed/tables'/f'{obj["slug"]}.csv').write_text('')
            (root/'parsed/tables'/f'{obj["slug"]}.html').write_text(obj['raw_html'])
            additions.append(dict(id=obj['id'],pdf_page=obj['pdf_page'],
                action='figure source review found possible table; queued cell extraction'))
write(path,objects)
censuspath=root/'parsed/table-caption-census.json'
history=json.loads(censuspath.read_text()).get('augmentation_history',[]) if censuspath.exists() else []
for item in additions:
    if item not in history:history.append(item)
write(censuspath,dict(captions=census,augmented=additions,augmentation_history=history,
    scope='OCR-detected captions plus source-model figure classifications; not proof that the scan contains no other tables'))
print('Caption census:',len(census),'captions;',len(additions),'additional table candidates')
