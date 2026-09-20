#!/usr/bin/env python3
"""Extract completed Marker chunks without altering raw model output.

Page-scoped identifiers are essential: Hairer equation labels repeat in each
chapter. Native text, Markdown, full block HTML, inline/display math, captions,
table grids and source crops are separate retained products.
"""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup
import pypdfium2 as pdfium

HERE = Path(__file__).resolve().parent
DELIMITER = re.compile(r'\{(\d+)\}-{10,}\s*')

def write(path, data):
    tmp = path.with_suffix(path.suffix+'.partial')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    tmp.replace(path)

def walk(block, parent=None):
    yield block, parent
    for child in block.get('children', []):
        yield from walk(child, block)

def text(raw):
    return BeautifulSoup(raw or '', 'html.parser').get_text(' ', strip=True)

def crop_source(page,bbox,path,margin=10):
    if path.exists():return
    width,height=page.get_size();left,top,right,bottom=bbox
    bitmap=page.render(scale=2.5,crop=(max(0,left-margin),max(0,height-bottom-margin),
        max(0,width-right-margin),max(0,top-margin)))
    bitmap.to_pil().save(path);bitmap.close()

def table(raw):
    soup = BeautifulSoup(raw, 'html.parser')
    cells, occupied = [], {}
    for row, tr in enumerate(soup.find_all('tr')):
        col = 0
        for td in tr.find_all(['td','th'], recursive=False):
            while (row,col) in occupied: col += 1
            rs, cs = int(td.get('rowspan',1)), int(td.get('colspan',1))
            cell = dict(row=row,column=col,rowspan=rs,colspan=cs,
                        text=td.get_text(' ',strip=True),html=td.decode_contents())
            cells.append(cell)
            for r in range(row,row+rs):
                for c in range(col,col+cs): occupied[r,c] = cell
            col += cs
    nr = max((r for r,c in occupied),default=-1)+1
    nc = max((c for r,c in occupied),default=-1)+1
    grid = [['' for _ in range(nc)] for _ in range(nr)]
    for cell in cells: grid[cell['row']][cell['column']] = cell['text']
    return dict(cells=cells, rows=grid, status='OCR; spans retained; not source reviewed')

def run(book):
    root = Path(book['root'])
    marker = root/'sources/marker'
    out = root/'parsed'
    for folder in ['pages','blocks','objects','crops','tables']:
        (out/folder).mkdir(parents=True,exist_ok=True)
    doc = pdfium.PdfDocument(book['pdf'])
    pages, trees, origins = {}, {}, {}
    for done in sorted((marker/'chunks/done').glob('*.ok')):
        jp = marker/'chunks/json'/f'{done.stem}.json'
        mp = marker/'chunks/md'/f'{done.stem}.md'
        assert jp.is_file() and mp.is_file(), f'Incomplete checkpoint {done}'
        md = mp.read_text()
        hits = list(DELIMITER.finditer(md))
        for i, match in enumerate(hits):
            n = int(match[1])+1
            assert n not in pages, f'Duplicate page {n}'
            pages[n] = md[match.end():hits[i+1].start() if i+1<len(hits) else len(md)].strip()
            origins[n] = str(jp.relative_to(root))
        for tree in json.loads(jp.read_text())['children']:
            n = int(re.search(r'/page/(\d+)/',tree['id'])[1])+1
            assert n not in trees, f'Duplicate block page {n}'
            trees[n] = tree
    assert set(pages) == set(trees), 'Markdown and structured page coverage differ'
    objects, inline, headings, census = [], [], [], []
    for n in sorted(pages):
        page = doc[n-1]
        walked = list(walk(trees[n]))
        captions = [b for b,_ in walked if b.get('block_type')=='Caption']
        page_objects = []
        write(out/'blocks'/f'{n:04d}.json',trees[n])
        raw = pages[n]
        readable = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',
                          lambda m:f'![{m[1]}](../../sources/marker/images/{Path(m[2]).name})', raw)
        (out/'pages'/f'{n:04d}.md').write_text(
            f'# PDF page {n}\n\n[Source image](../../sources/renders/{n:04d}.jpg) · '
            f'[Native text](../../sources/native/pages/{n:04d}.txt)\n\n'
            'OCR transcription; consult source images for mathematical authority.\n\n'+readable+'\n')
        for block, parent in walked:
            kind = block.get('block_type')
            rawhtml = block.get('html','')
            if kind=='SectionHeader':
                headings.append(dict(pdf_page=n,title=text(rawhtml),bbox=block['bbox']))
            if not block.get('children') and kind!='Equation':
                for k, math in enumerate(BeautifulSoup(rawhtml,'html.parser').find_all('math')):
                    inline.append(dict(id=f'{book["id"]}:p{n:04d}:{block["id"]}:inline{k}',
                                       pdf_page=n,latex=math.get_text(),bbox=block['bbox'],
                                       display=math.get('display'),containing_type=kind))
            if kind not in ['Equation','Figure','Picture','Table']: continue
            slug = f'p{n:04d}-{kind.lower()}-{block["id"].split("/")[-1]}'
            bbox = block['bbox']
            crop = out/'crops'/f'{slug}.png'
            # PDFium crop=(left,bottom,right,top) distances removed.
            crop_source(page,bbox,crop)
            row = dict(id=f'{book["id"]}:{slug}',slug=slug,pdf_page=n,kind=kind,
                       bbox_top_left_points=bbox,raw_html=rawhtml,
                       crop=str(crop.relative_to(root)),chunk_json=origins[n],
                       crop_sha256=hashlib.sha256(crop.read_bytes()).hexdigest(),
                       status='unreviewed OCR')
            if kind=='Equation':
                maths = BeautifulSoup(rawhtml,'html.parser').find_all('math')
                row['latex'] = '\n'.join(m.get_text() for m in maths) if maths else text(rawhtml)
                # Equation labels often sit OUTSIDE <math>, including primed
                # labels such as (1.4'). Preserve them in the object index.
                row['printed_labels'] = re.findall(r'\\tag\*?\{([^{}]+)\}',row['latex'])
                outside=BeautifulSoup(rawhtml,'html.parser')
                for math in outside.find_all('math'):math.decompose()
                row['printed_labels'] += [a+b for a,b in re.findall(
                    r"\(([IVX]+\.)?\s*(\d+(?:[.\u2013-]\d+)?[a-z]?'*)\)\s*$",outside.get_text(' ',strip=True))]
                # Williams-style labels typeset inside the display: ... \quad (15)
                row['printed_labels'] += re.findall(r"\\q?quad\s*\((\d+(?:[.\u2013-]\d+)?[a-z]?'*)\)\s*$",row['latex'].strip())
                row['printed_labels']=list(dict.fromkeys(row['printed_labels']))
            else:
                def distance(cap):
                    a,z = bbox,cap['bbox']
                    overlap = max(0,min(a[2],z[2])-max(a[0],z[0]))
                    gap = max(0,max(a[1],z[1])-min(a[3],z[3]))
                    return gap + (0 if overlap else 1000)
                cap = min(captions,key=distance) if captions else None
                row['caption'] = text(cap.get('html','')) if cap and distance(cap)<100 else ''
                row['caption_status'] = 'nearest geometrically associated caption; unreviewed'
                if cap and distance(cap)<100:
                    row['caption_bbox_top_left_points']=cap['bbox']
                    a,z=bbox,cap['bbox']
                    context_bbox=[min(a[0],z[0]),min(a[1],z[1]),max(a[2],z[2]),max(a[3],z[3])]
                    context=out/'crops'/f'{slug}-context.png'
                    crop_source(page,context_bbox,context)
                    row['context_crop']=str(context.relative_to(root))
                    row['context_crop_sha256']=hashlib.sha256(context.read_bytes()).hexdigest()
                    row['context_bbox_top_left_points']=context_bbox
                if kind=='Table':
                    row.update(table(rawhtml))
                    (out/'tables'/f'{slug}.html').write_text(rawhtml)
                    with (out/'tables'/f'{slug}.csv').open('w',newline='') as f:
                        csv.writer(f).writerows(row['rows'])
            objects.append(row); page_objects.append(row)
        write(out/'objects'/f'{n:04d}.json',page_objects)
        census.append(dict(pdf_page=n,characters=len(raw),
                           blocks=dict(Counter(b['block_type'] for b,_ in walked))))
        page.close()
    write(out/'objects.json',objects)
    write(out/'inline-math.json',inline)
    write(out/'headings.json',headings)
    coverage = dict(expected_pages=len(doc),completed_pages=len(pages),
                    missing_pages=sorted(set(range(1,len(doc)+1))-set(pages)),
                    objects=dict(Counter(o['kind'] for o in objects)),
                    inline_math=len(inline),pages=census)
    write(out/'coverage.json',coverage)
    (out/'book.md').write_text(f'# {book["title"]}\n\n{book["edition"]}\n\n'
        'Provisional OCR; page images and all raw candidates are retained.\n\n' +
        '\n\n'.join(f'## PDF page {n}\n\n[Page with source links](pages/{n:04d}.md)\n\n'+
        re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',
               lambda m:f'![{m[1]}](../sources/marker/images/{Path(m[2]).name})',pages[n]) for n in sorted(pages)))
    print(book['id'], {k:v for k,v in coverage.items() if k not in ['pages','missing_pages']},flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--book');args=ap.parse_args()
    for book in json.loads((HERE/'books.json').read_text())['books']:
        if args.book is None or args.book==book['id']: run(book)
