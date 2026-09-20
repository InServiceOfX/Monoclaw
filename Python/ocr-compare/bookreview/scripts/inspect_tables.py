#!/usr/bin/env python3
"""Stack the source crops of Table objects that have no direct-inspection record yet
into one PNG, and print the Marker grid and the model's grid (when its job has landed).
Usage: inspect_tables.py START COUNT OUT.png"""
import json,sys,glob
from pathlib import Path
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
book=json.loads((HERE/'books.json').read_text())['books'][0];root=Path(book['root'])
start,count,out=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
objs=[o for o in json.loads((root/'parsed/objects.json').read_text()) if o['kind']=='Table']
manual=root/'curated/manual-review.json'
done={r['id'] for r in json.loads(manual.read_text())['items']} if manual.exists() else set()
cls=root/'curated/object-classification-review.json'
if cls.exists():done|={r['id'] for r in json.loads(cls.read_text())['items']}
verdicts={}
for p in glob.glob(str(root/'reconciliation/vision/*-table-*.json')):
    d=json.loads(Path(p).read_text())
    try:
        content=json.loads(d['raw_response']['choices'][0]['message']['content'])
        for it in content.get('items',[]):verdicts[it['id']]=it
    except Exception as e:pass
todo=[o for o in objs if o['id'] not in done]
sel=todo[start:start+count]
ims=[]
for o in sel:
    im=Image.open(root/(o.get('context_crop') or o['crop'])).convert('RGB')
    if im.width>1100:im=im.resize((1100,int(im.height*1100/im.width)))
    ims.append((o['id'],im))
W=max(im.width for _,im in ims);H=sum(im.height+28 for _,im in ims)
sheet=Image.new('RGB',(W,H),'white');d=ImageDraw.Draw(sheet);y=0
for k,im in ims:
    d.text((6,y+6),k,fill='red');sheet.paste(im,(0,y+24));y+=im.height+28
sheet.save(out)
print('remaining',len(todo),'of',len(objs),'showing',start,'..',start+len(sel)-1,'->',out)
for o in sel:
    print('==',o['id'],'| caption:',o.get('caption') or '-','| status:',o.get('status'))
    print('  MARKER rows:',json.dumps(o.get('rows'),ensure_ascii=False)[:1500])
    v=verdicts.get(o['id'])
    if v:print('  MODEL  rows:',json.dumps(v.get('rows'),ensure_ascii=False)[:1500]);print('  MODEL conf:',v.get('confidence'),'| unresolved:',v.get('unresolved'),'| footnotes:',v.get('footnotes'));print('  MODEL reason:',v.get('reason','')[:400])
    else:print('  MODEL: (job not landed)')
