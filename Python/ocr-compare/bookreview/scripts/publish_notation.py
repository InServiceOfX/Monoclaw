#!/usr/bin/env python3
"""Per-book typography pass (OPT-IN: runs only when books.json has "notation_rules": "hillpeterson").
Hill & Peterson example: thrust is the script letter 𝒯 (\\mathcal{T}) throughout this
book, but the OCR engines read the glyph variously as \\mathcal{F}, \\mathcal{I} or \\mathcal{J}
(no script F, I or J is used anywhere in the book). Apply the same rewrite used by
triage_math.py to every math span of the reading products and record what changed.
Idempotent; runs after assemble.py / publish_book.py.
"""
import json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
book=json.loads((HERE/'books.json').read_text())['books'][0];root=Path(book['root'])
if book.get('notation_rules')!='hillpeterson':
    print(json.dumps(dict(math_spans_changed=0,files_changed=0,skipped='no notation_rules for this book')));sys.exit(0)
NU=[(r'\\(?:mathcal|cal|mathscr)\{[FIJ]\}|\\Im\b',r'\\mathcal{T}'),(r'\\mathscr\{T\}',r'\\mathcal{T}'),(r'd\s*\^\{?\\circ\}?\s*V\b',r'd\\mathcal{V}'),(r'\\dot\{(?:2|\\underline\{2\}|\\mathfrak\{[Dd]\})\}',r'\\dot{\\mathcal{Q}}'),(r'\\mathfrak\{D\}',r'\\mathcal{D}')]
def nu_fix(s):
    for pat,rep in NU:s=re.sub(pat,rep,s)
    return s
MATH=re.compile(r'(\$\$.*?\$\$|\\\[.*?\\\]|(?<!\$)\$(?!\$).*?(?<!\$)\$(?!\$))',re.S)
changed=0;files=0
def fix_text(text):
    global changed
    def sub(m):
        global changed
        new=nu_fix(m[0])
        if new!=m[0]:changed+=1
        return new
    return MATH.sub(sub,text)
for p in [root/'parsed/book-reconciled.md',root/'parsed/EQUATIONS.md',*sorted((root/'parsed/reconciled-pages').glob('*.md'))]:
    if not p.exists():continue
    before=changed;t=p.read_text();n=fix_text(t)
    if n!=t:p.write_text(n);files+=1
eq=root/'parsed/equations.json'
if eq.exists():
    data=json.loads(eq.read_text());k=0
    for e in data:
        if e.get('latex'):
            new=nu_fix(e['latex'])
            if new!=e['latex']:e['latex']=new;e['notation_normalised']='script F/I/J -> script T (thrust glyph)';k+=1
    eq.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n');changed+=k
rec=root/'reconciliation/notation-normalisation.json'
rec.write_text(json.dumps(dict(book=book['id'],rule='\\mathcal{F}, \\mathcal{I}, \\mathcal{J} rewritten to \\mathcal{T} (thrust), and d^\\circ V to d\\mathcal{V} (volume element, script V), and \\dot{2} / \\dot{\\mathfrak{D}} to \\dot{\\mathcal{Q}} (heat-flux script Q), and undotted \\mathfrak{D} to \\mathcal{D} (drag, script D): the book uses the script T for thrust from eq. (1.1) on and no script F, I or J anywhere; both OCR engines misread the glyph. Every direct inspection of such glyphs in curated/manual-review.json confirms it.',
    math_spans_changed=changed,files_changed=files),indent=2)+'\n')
print(json.dumps(dict(math_spans_changed=changed,files_changed=files)))
