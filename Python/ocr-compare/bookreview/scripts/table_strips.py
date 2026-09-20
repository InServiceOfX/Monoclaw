#!/usr/bin/env python3
"""Render a Table object's bounding box from the PDF at 3x in N horizontal strips and print Marker's rows.
Usage: table_strips.py OBJECT_ID N OUTPREFIX [pad_pt]"""
import json,sys
from pathlib import Path
import pypdfium2 as pdfium
HERE=Path(__file__).resolve().parent
book=json.loads((HERE/'books.json').read_text())['books'][0];root=Path(book['root'])
oid,n,prefix=sys.argv[1],int(sys.argv[2]),sys.argv[3];pad=float(sys.argv[4]) if len(sys.argv)>4 else 6
rot=int(sys.argv[5]) if len(sys.argv)>5 else 0   # rotate the crop (degrees, PIL counter-clockwise) before splitting into strips
o=[o for o in json.loads((root/'parsed/objects.json').read_text()) if o['id']==oid][0]
pdf=pdfium.PdfDocument(book['pdf']);page=pdf[o['pdf_page']-1];s=3
im=page.render(scale=s).to_pil();x0,y0,x1,y1=o['bbox_top_left_points']
crop=im.crop((int((x0-pad)*s),int((y0-pad)*s),int((x1+pad)*s),int((y1+pad)*s)))
if rot:crop=crop.rotate(rot,expand=True)
W,Hh=crop.size;H=Hh/n
for i in range(n):
    a=max(0,int(i*H-pad*s));b=min(Hh,int((i+1)*H+pad*s))
    crop.crop((0,a,W,b)).save(f'{prefix}{i}.png')
rows=o['rows'];rows=json.loads(rows) if isinstance(rows,str) else rows
print(len(rows),'marker rows;',n,'strips ->',prefix)
for i,r in enumerate(rows):print(i,json.dumps(r,ensure_ascii=False))
