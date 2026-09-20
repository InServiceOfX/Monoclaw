#!/usr/bin/env python3
"""Stack the source crops of triage items [start, start+count) into one PNG for
direct inspection, and print the candidate readings. Usage: inspect_sheet.py START COUNT OUT.png"""
import json,sys
from pathlib import Path
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
book=json.loads((HERE/'books.json').read_text())['books'][0];root=Path(book['root'])
start,count,out=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
items=json.loads((root/'curated/triage.json').read_text())['items']
manual=root/'curated/manual-review.json'
done={r['id'] for r in json.loads(manual.read_text())['items']} if manual.exists() else set()
todo=[it for it in items if it['id'] not in done]
sel=todo[start:start+count]
ims=[]
for it in sel:
    crop=it.get('crop')
    if not crop:
        # Nougat-only fragment: show the page render region? use full page at reduced scale
        im=Image.open(root/f'sources/renders/{it["pdf_page"]:04d}.jpg').convert('RGB')
    else:im=Image.open(root/crop).convert('RGB')
    if im.width>1100:im=im.resize((1100,int(im.height*1100/im.width)))
    ims.append((it['id'],im))
W=max(im.width for _,im in ims);H=sum(im.height+28 for _,im in ims)
sheet=Image.new('RGB',(W,H),'white');d=ImageDraw.Draw(sheet);y=0
for k,im in ims:
    d.text((6,y+6),k,fill='red');sheet.paste(im,(0,y+24));y+=im.height+28
sheet.save(out)
print('remaining',len(todo),'showing',start,'..',start+len(sel)-1,'->',out)
for it in sel:
    print('==',it['id'],'|',it['why'])
    print('  MARKER:',it.get('marker'));print('  NOUGAT:',it.get('nougat'));print('  MODEL :',it.get('model'))
