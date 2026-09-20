#!/usr/bin/env python3
"""Read-only PDF inventory; retain native text, page geometry and source renders."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
import pypdfium2 as pdfium

HERE = Path(__file__).resolve().parent

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

for book in json.loads((HERE / 'books.json').read_text())['books']:
    root = Path(book['root'])
    for folder in ['sources/native/pages', 'sources/renders', 'provenance', 'logs',
                   'parsed/pages', 'parsed/objects', 'reconciliation', 'curated']:
        (root / folder).mkdir(parents=True, exist_ok=True)
    source = Path(book['pdf'])
    digest = sha(source)
    manifest = root / 'sources/source.json'
    if manifest.exists():
        assert json.loads(manifest.read_text())['sha256'] == digest
    write(manifest, dict(book, sha256=digest, bytes=source.stat().st_size))
    doc = pdfium.PdfDocument(source)
    assert len(doc) == book['expected_pdf_pages']
    pages = []
    for i in range(len(doc)):
        page = doc[i]
        tp = page.get_textpage()
        text = tp.get_text_range()
        path = root / 'sources/native/pages' / f'{i+1:04d}.txt'
        path.write_text(text)
        bitmap = page.render(scale=1)
        image = bitmap.to_pil().convert('RGB')
        render_hash = hashlib.sha256(image.tobytes()).hexdigest()
        image.save(root / 'sources/renders' / f'{i+1:04d}.jpg', quality=88)
        pages.append(dict(pdf_page=i+1, size_points=list(page.get_size()),
                          native_characters=len(text), native_sha256=sha(path),
                          render_rgb_sha256=render_hash))
        bitmap.close(); tp.close(); page.close()
    write(root / 'sources/pages.json', pages)
    groups = {}
    for page in pages:
        groups.setdefault(page['render_rgb_sha256'], []).append(page['pdf_page'])
    write(root / 'sources/duplicate-renders.json', [p for p in groups.values() if len(p)>1])
    (root / 'sources/native/book.txt').write_text('\f'.join(
        (root/'sources/native/pages'/f'{i+1:04d}.txt').read_text() for i in range(len(doc))))
    for command, filename in [('pdfinfo','pdfinfo.txt'), ('pdffonts','pdffonts.txt')]:
        result = subprocess.run([command, str(source)], capture_output=True, text=True, check=True)
        (root / 'sources' / filename).write_text(result.stdout)
    for name, path in {
        'marker_book.py': HERE/'marker_book.py',
        'nougat_pages.py': HERE/'nougat_pages.py',
        'inventory.py': Path(__file__)
    }.items():
        target = root / 'provenance' / name
        if target.exists():
            assert sha(target) == sha(path), f'Provenance changed: {name}'
        else:
            shutil.copy2(path, target)
    print(book['id'], len(pages), 'pages inventoried', digest, flush=True)
