#!/usr/bin/env python3
"""Merge direct source-image review records into curated/manual-review.json.

Record shapes match Humble's assemble.py contract:
  table: id, rows, footnotes, caption?, confidence, reason, unresolved, image, image_sha256
  math:  id, choice (marker|nougat|both|corrected|not_in_source), corrected, confidence, reason, image, image_sha256
  text:  id (<book>:pNNNN:text), patches [{before,after}], confidence, reason, unresolved
Never resets unrelated records; the image hash is computed at record time so a
changed source image invalidates the record (assemble.py asserts on it).
"""
import hashlib,json,datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent
BOOK=json.loads((HERE/'books.json').read_text())['books'][0];ROOT=Path(BOOK['root'])
PATH=ROOT/'curated/manual-review.json'
REVIEWER='Claude direct source-image inspection'
def load():
    if PATH.exists():return json.loads(PATH.read_text())
    return dict(reviewer=REVIEWER,scope='Direct source-image reviews enumerated by object ID and image hash; scope is limited to the listed objects.',items=[])
def save(data):
    tmp=PATH.with_suffix('.partial');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(PATH)
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def put(item):
    data=load();data['items']=[x for x in data['items'] if x['id']!=item['id']]+[item];save(data);return item
def objects():
    return {o['id']:o for o in json.loads((ROOT/'parsed/objects.json').read_text())}
def table(oid,rows,*,reason,footnotes=(),caption=None,unresolved=(),image=None,confidence='high',source_conditions='',notes=''):
    obj=objects()[oid];image=image or obj.get('context_crop') or obj['crop']
    assert rows and all(isinstance(r,list) and all(isinstance(c,str) for c in r) for r in rows)
    item=dict(id=oid,pdf_page=obj['pdf_page'],confidence=confidence,rows=rows,footnotes=list(footnotes),unresolved=list(unresolved),
              reason=reason,image=image,image_sha256=sha(image),reviewer=REVIEWER,reviewed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if caption:item['caption']=caption
    if source_conditions:item['source_conditions']=source_conditions
    if notes:item['notes']=notes
    return put(item)
def math(oid,choice,*,reason,corrected='',confidence='high',image=None,unresolved=()):
    obj=objects().get(oid)
    page=obj['pdf_page'] if obj else int(oid.split(':p')[1][:4])
    image=image or (obj['crop'] if obj else f'sources/renders/{page:04d}.jpg')
    assert choice in ['marker','nougat','both','corrected','not_in_source','unreadable']
    if choice=='corrected':assert corrected.strip()
    item=dict(id=oid,pdf_page=page,choice=choice,corrected=corrected,confidence=confidence,reason=reason,unresolved=list(unresolved),
              image=image,image_sha256=sha(image),reviewer=REVIEWER,reviewed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if obj:item['marker_before']=obj.get('latex')
    return put(item)
def text(page,patches,*,reason,confidence='high',unresolved=()):
    body=(ROOT/f'parsed/pages/{page:04d}.md').read_text()
    for b,a in patches:assert body.count(b)==1,(page,b,body.count(b))
    item=dict(id=f'{BOOK["id"]}:p{page:04d}:text',pdf_page=page,patches=[dict(before=b,after=a) for b,a in patches],confidence=confidence,
              unresolved=list(unresolved),reason=reason,image=f'sources/renders/{page:04d}.jpg',image_sha256=sha(f'sources/renders/{page:04d}.jpg'),
              reviewer=REVIEWER,reviewed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    return put(item)
if __name__=='__main__':
    d=load();print(len(d['items']),'records in',PATH)
CLASS_PATH=ROOT/'curated/object-classification-review.json'
def classify(oid,reviewed_kind,*,reason,caption_for=None):
    """Record that a Marker 'Table' object is really a Caption or Text block (applied by augment_tables.py)."""
    obj=objects()[oid];assert obj.get('original_kind','Table')=='Table' or obj['kind']=='Table'
    assert reviewed_kind in ['Caption','Text']
    if reviewed_kind=='Caption':assert caption_for in objects()
    data=json.loads(CLASS_PATH.read_text()) if CLASS_PATH.exists() else dict(reviewer=REVIEWER,items=[])
    item=dict(id=oid,pdf_page=obj['pdf_page'],original_kind='Table',reviewed_kind=reviewed_kind,image=obj['crop'],image_sha256=sha(obj['crop']),
              reason=reason,reviewer=REVIEWER,reviewed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if caption_for:item['caption_for']=caption_for
    data['items']=[x for x in data['items'] if x['id']!=oid]+[item]
    tmp=CLASS_PATH.with_suffix('.partial');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(CLASS_PATH);return item
def fragment(oid,choice,*,reason,anchor=None,corrected='',before=None,after=None,disposition=None,confidence='high',unresolved=()):
    """Nougat-only fragment verdict: 'nougat' + anchor (content already represented at a unique reading-copy string),
    'corrected' + before/after (insert a display Marker dropped), 'not_in_source', or disposition='inline symbol'."""
    item=math(oid,choice,reason=reason,corrected=corrected,confidence=confidence,unresolved=unresolved)
    data=load();rec=[x for x in data['items'] if x['id']==oid][0]
    if anchor:assert choice=='nougat';rec['representation_anchor']=anchor
    if before is not None:assert choice=='corrected' and after is not None;rec['placement_before']=before;rec['placement_after']=after
    if disposition:rec['fragment_disposition']=disposition
    save(data);return rec
