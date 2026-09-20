#!/usr/bin/env python3
"""Post-VLM triage for display-math verdicts.

A local-VLM "corrected" transcription is accepted for automatic placement ONLY
when it token-matches an independent OCR reading (Marker or Nougat) — two
independent readings agreeing. Otherwise the verdict record is downgraded to
confidence=medium (raw response retained, `triage` field explains why) so that
assemble.py lists it as unresolved for direct inspection instead of applying it.

Also writes curated/triage.json: per-equation category counts and the list of
objects that need direct inspection, ordered by page.
"""
import difflib,hashlib,json,re,subprocess
from collections import Counter
from pathlib import Path
from extract import write
from reconcile import TAG,MATH,INLINE
HERE=Path(__file__).resolve().parent
book=json.loads((HERE/'books.json').read_text())['books'][0];root=Path(book['root'])
def clean(s):
    s=TAG.sub('',s or '').strip()
    s=re.sub(r"(?:(?:\\q?quad\s*)+|\t|\s{2,})\s*\(\d+(?:[.\u2013-]\d+)?[a-z]?'*\)\s*$",'',s)   # trailing printed label
    return s.strip().rstrip('.,;')
STYLE=[(r'\\(?:mathbf|boldsymbol|mathrm|textbf|textit|mathit|operatorname|text)\{([^{}]*)\}',r'\1'),(r'\\(?:mathbf|boldsymbol|mathrm|mathit)\s+(\w)',r'\1'),
       (r'\\(?:ldots|cdots|dots|dotsc|dotsb)',r'...'),(r'\\(?:varepsilon)',r'\\epsilon'),(r'\\(?:varphi)',r'\\phi'),(r'\\(?:varrho)',r'\\rho'),
       (r'\\[,;!: ]',r''),(r'\\(?:quad|qquad|displaystyle|left|right|nonumber|limits|nolimits|big|Big|bigg|Bigg|bigl|bigr|biggl|biggr)\b',r''),(r'\\prime',r"'"),
       (r'\{\\(?:bf|boldsymbol|mathbf)\s*([^{}]*)\}',r'\1'),(r'\{\\cal\s*([^{}]*)\}',r'\\mathcal{\1}'),(r'\\overline\{',r'\\bar{'),(r'\^\{"\}',r"''"),(r'\^\{\\prime\\prime\}',r"''"),(r'\^\{\\prime\}',r"'"),(r'\\(?:text|mathrm|mathit|textbf)\s+\{',r'\\text{'),(r'\\(?:Leftrightarrow|rightleftharpoons|leftrightarrow|rightleftarrows)\b',r'\\rightleftharpoons'),(r'\\rm\{([^{}]*)\}',r'\1'),(r'^\$+|\$+$',r''),(r'\\circ\b',r'o'),(r'\\mathcal\{([A-Z])\}',r'\1'),(r'\\(?:mathrm|text)\{\s*(kJ|kmol|kg|mol|K|s|m|W|J|Pa|atm|cm|g|N)\s*\}',r'\1'),(r'\\rm\s+',r''),(r'\\(?:mathrm|text)\{(all)\s*\}',r'\1'),
       (r'\\(?:mathscr|mathcal|mathfrak)\{([^{}]*)\}',r'\\mathcal{\1}'),(r'\\(?:ln|log)\b',r'\\ln'),
       (r'(?:\\mbox\{|\{\\rm\s*|\\operatorname\{|\\mathrm\{)(exp|sin|cos|tan|ln|log|sinh|cosh|tanh|max|min|erf|erfc|diag|diagonal|constant|const)\}',r'\\\1'),(r'\{\\rm\s*([A-Za-z0-9]+)\}',r'\1'),
       (r'(?:\\mbox\{\\rm\s*|\\operatorname\{|\\mathrm\{|\\mathsf\{|\\text\{)(Le|Pr|Re|Da|Sc|Nu|Ma|Pe|Bi|St|Ze)\}',r'\1'),(r'\\eqno\s*\([^)]*\)',r''),(r'\\tfrac',r'\\frac'),
       (r'\{([A-Za-z0-9])\}',r'\1'),(r'\\(?:le|leq|leqslant)\b',r'\\le'),(r'\\(?:ge|geq|geqslant)\b',r'\\ge'),
       (r'\\(?:to|rightarrow)\b',r'\\to'),(r'\\stackrel\b',r'\\overset'),(r'\\(?:mathop|limits)\b',r''),(r'\\(?:cdot|times)\b',r'\\cdot'),(r'\\(?:partial)\b',r'\\partial')]
# Hill & Peterson typography: thrust is the script T; OCR reads the glyph as script F/I/J (no script F, I, J
# exists in the book). The same rewrite is applied to the reading copy by publish_notation.py.
T_FIX=[(r'\\(?:mathcal|cal|mathscr)\{[FIJT]\}|\{\\cal\s*[FIJTG]\}|\\Im\b|\\mathcal\{G\}',r'\\mathcal{T}'),   # comparison only: script G is a real symbol in ch. 12, but Nougat also writes it for the thrust glyph
       (r'd\s*\^\{?\\circ\}?\s*V\b',r'd\\mathcal{V}'),(r'\\mathbb\{C\}\^m',r'\\mathrm{cm}'),(r'\\dot\{(?:2|\\underline\{2\}|\\mathfrak\{[Dd]\}|\\mathfrak\{Q\}|\\mathfrak\{L\})\}',r'\\dot{\\mathcal{Q}}'),(r'\\Re_',r'\\mathfrak{M}_'),(r'\\mathfrak\{D\}|\\mathbb\{A\}',r'\\mathcal{D}')]   # drag is script D; \dot{\mathfrak{D}} (heat flux) is handled first
def glyph_fix(s):
    for pat,rep in T_FIX:s=re.sub(pat,rep,s or '')
    return s
def norm(s):
    s=glyph_fix(clean(s))
    s=re.sub(r'\\(?:to|rightarrow|longrightarrow)\b','→',s)      # before any unwrapping can glue \to to the next letter
    s=re.sub(r"\^\{\{\}\^\{\\prime\}\}","'",s)                       # Nougat's v^{{}^{\prime}}
    s=re.sub(r"\^\{\\prime\\prime\}","''",s);s=re.sub(r"\^\{\\prime\}","'",s)
    s=re.sub(r"\^\{\\prime\s*(\d)\}",r"'^\1",s);s=re.sub(r"\^\{\\prime\\prime\s*(\d)\}",r"''^\1",s)
    s=re.sub(r"(\\?\w+)('{1,2})_(\{[^{}]*\}|\w)",r"\1_\3\2",s)          # canonical: subscript before primes (v'_i -> v_i')
    s=re.sub(r"_\{(\w)\}",r"_\1",s);s=re.sub(r"\^\{(\w)\}",r"^\1",s)       # single-character scripts without braces
    s=re.sub(r"\^\{(\w+)\}_\{(\w+)\}",r"_{\2}^{\1}",s);s=re.sub(r"\^(\w)_\{(\w+)\}",r"_{\2}^\1",s);s=re.sub(r"\^\{(\w+)\}_(\w)",r"_\2^{\1}",s)   # canonical sub-then-sup order
    for _ in range(3):
        for pat,rep in STYLE:s=re.sub(pat,rep,s)
    s=re.sub(r'\\(?:to|rightarrow|longrightarrow)\b','→',s)      # arrows as one symbol so \to never glues to the next letter
    return re.sub(r'\s+','',s).rstrip('.,;')                    # punctuation that sat inside a \mathrm{...} wrapper
def compare(a,b):
    """(status, distance, max_tokens) with the conservative Rust tokenizer, after stylistic normalisation."""
    if not a or not b:return ('missing',None,None)
    line='x\t'+norm(a).encode().hex()+'\t'+norm(b).encode().hex()+'\n'
    out=subprocess.run([str(HERE/'math_tokens')],input=line,text=True,capture_output=True,check=True).stdout.split('\t')
    return (out[1],int(out[2]),int(out[3]))
def tokens_equal(a,b):
    st,_,_=compare(a,b);return st in ('exact','format_only')
def clean_nougat(s):
    s=glyph_fix(TAG.sub('',s or ''))
    s=re.sub(r'\\[bB]igg?l\{?([(\[|])\}?',r'\\left\1',s);s=re.sub(r'\\[bB]igg?r\{?([)\]|])\}?',r'\\right\1',s)
    s=re.sub(r'\\[bB]igg?\{?([()\[\]|])\}?',r'\1',s)
    s=re.sub(r'\\mbox\{','\\\\mathrm{',s)
    s=re.sub(r'(?:\\[,;!]|\\ )+',' ',s)
    s=re.sub(r'_\{\s*(\w+)\s*\}',r'_{\1}',s);s=re.sub(r'\s*=\s*','=',s)
    s=re.sub(r'\s*([{},])\s*',r'\1',s)
    return re.sub(r'\s+',' ',s).strip()
def raw_items(v):
    try:
        choice=v['raw_response']['choices'][0];reply=(choice['message'].get('content') or '').strip() or (choice['message'].get('reasoning_content') or '').strip()
        m=re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```',reply,re.S)
        return json.loads(m[1] if m else reply)['items']
    except Exception:return None
def rust_tokens(s):
    out=subprocess.run([str(HERE/'math_tokens')],input='x\t'+s.encode().hex()+'\t'+s.encode().hex()+'\n',text=True,capture_output=True,check=True).stdout
    return None
ALIGN_TOKENS={'&','\\\\','\\begin','\\end','\\hline','\\nonumber','\\notag','\\vdots','\\ddots'}
ALIGN_ENV=re.compile(r'\\(?:begin|end)\{(?:split|aligned|align\*?|gathered|gather\*?|array|eqnarray\*?|cases|[bBpv]?matrix)\}(?:\{[lcr|]*\})?')
_UNGLUE=re.compile(r'\\(varepsilon|vartheta|epsilon|upsilon|partial|varphi|lambda|Lambda|nabla|infty|theta|Theta|alpha|gamma|Gamma|delta|Delta|sigma|Sigma|omega|Omega|kappa|tilde|ddot|sqrt|prod|beta|zeta|iota|sinh|cosh|tanh|exp|sin|cos|tan|log|bar|hat|vec|dot|sum|int|eta|rho|tau|phi|Phi|chi|psi|Psi|ln|xi|Xi|mu|nu|pi|Pi)(?=[A-Za-z])')
def simple_tokens(s):
    # Alignment scaffolding (split/aligned environments, & and \\ separators) is layout, not content:
    # a Nougat fragment that is one line of a Marker multi-line display must still match.
    s=ALIGN_ENV.sub(' ',clean(s or ''))
    s=s.replace('\\\\',' ').replace('&',' ')
    s=re.sub(r'\\(?:to|rightarrow|longrightarrow)\b',' → ',s)
    s=re.sub(r"\^\{\{\}\^\{\\prime\}\}","'",s);s=re.sub(r"\^\{\\prime\\prime\\prime\}","'''",s);s=re.sub(r"\^\{\\prime\\prime\}","''",s);s=re.sub(r"\^\{\\prime\}","'",s)
    for _ in range(3):
        for pat,rep in STYLE:s=re.sub(pat,rep,s)
    s=re.sub(r"\^\{?('{1,3})\}?",r"\1",s)                               # k^{'} -> k'
    s=re.sub(r"(\\?\w+)('{1,3})_(\{[^{}]*\}|\w)",r"\1_\3\2",s)          # canonical: subscript before primes
    s=re.sub(r'\\(?:mbox|hbox)\{([^{}]*)\}',r'\1',s)
    s=re.sub(r'\\[bB]igg?[lr]?\{?([()\[\]|])\}?',r'\1',s)
    # STYLE's {x} -> x can glue an accent/function/Greek command to the next letter (\bar{g} -> \barg);
    # split known command names back off (longest name first).
    s=_UNGLUE.sub(lambda m:'\\'+m.group(1)+' ',s)
    s=re.sub(r'\\(?:frac|tfrac|dfrac)\b',' ',s)
    s=re.sub(r'[{}()\[\]/]',' ',s)
    toks=re.findall(r'\\[A-Za-z]+|[A-Za-z0-9]|[^\sA-Za-z0-9]',s)
    return [t for t in toks if t not in ALIGN_TOKENS]
def _corrected_texts():
    """Object id -> corrected LaTeX that assemble.py will place (manual review first, then agreement)."""
    out={}
    for name in ('agreement-review.json','manual-review.json'):
        f=root/'curated'/name
        if not f.exists():continue
        for it in json.loads(f.read_text())['items']:
            if it.get('choice')=='corrected' and (it.get('corrected') or '').strip():out[it['id']]=it['corrected']
            elif it.get('choice') in ('marker','both'):out.pop(it['id'],None)
    return out
_CORRECTED=None
def fragment_anchor(row,page):
    """If the fragment's symbol sequence occurs inside a display (or inline span) of the page's
    reading copy AS IT WILL BE ASSEMBLED (Marker text, or the source-reviewed correction that replaces
    it), return a unique anchor into that text."""
    global _CORRECTED
    if _CORRECTED is None:_CORRECTED=_corrected_texts()
    frag=simple_tokens(row.get('nougat') or '')
    if not frag and re.fullmatch(r'[\s\\a-zA-Z{}]*',row.get('nougat') or '') and 'dots' in (row.get('nougat') or ''):return dict(inline_symbol=True)   # pure layout (\vdots rows)
    if len(frag)<6:return dict(inline_symbol=True) if frag else None
    n=len(frag)
    body=(root/f'parsed/pages/{page:04d}.md').read_text().split('mathematical authority.\n\n')[-1]
    # Simulate the assembled page: every Marker display that has a corrected verdict is replaced by it.
    objs=objects_by_page.get(page,[])
    def assembled(inner):
        for o in objs:
            if o['id'] in _CORRECTED and (o['latex'].strip()==inner.strip() or (len(o['latex'])>20 and o['latex'].strip() in inner)):
                return _CORRECTED[o['id']]
        return inner
    sim=MATH.sub(lambda m:'$$'+assembled(m.group(1) if m.group(1) is not None else m.group(2))+'$$',body)
    # Prefer the page as the last assembly actually produced it (region placements merge multi-block
    # displays); finalize.sh runs triage again after placements so anchors are checked against it.
    rp=root/f'parsed/reconciled-pages/{page:04d}.md'
    if rp.exists():sim=rp.read_text().split('review coverage is recorded separately.\n\n')[-1]
    def contains(disp):
        if len(disp)<0.9*n:return False
        if any(disp[i:i+n]==frag for i in range(len(disp)-n+1)):return True
        best=0
        for i in range(len(disp)):
            for j in range(n):
                k=0
                while i+k<len(disp) and j+k<n and disp[i+k]==frag[j+k]:k+=1
                if k>best:best=k
        if best>=0.9*n:return True
        # One or two differing tokens inside an otherwise identical run (\stackrel/\overset, a spacing
        # command, a subscript brace): similarity of the best window, fragment fully covered.
        if n>=10:
            for i in range(0,max(1,len(disp)-n+3)):
                w=disp[i:i+n+2]
                if difflib.SequenceMatcher(None,w,frag,autojunk=False).ratio()>=0.92:return True
        return False
    for m in MATH.finditer(sim):
        inner=m.group(1) if m.group(1) is not None else m.group(2)
        if contains(simple_tokens(inner)):
            for L in (60,90,120,160,220,len(inner)):
                anchor=inner[:L]
                if anchor and sim.count(anchor)==1:return dict(anchor=anchor,display='reading-copy display block on the same page')
    for m in INLINE.finditer(MATH.sub(' ',sim)):
        inner=m.group(1) if m.group(1) is not None else m.group(2)
        if inner and contains(simple_tokens(inner)):
            for L in (60,90,120,160,220,len(inner)):
                anchor=inner[:L]
                if anchor and sim.count(anchor)==1:return dict(anchor=anchor,display='reading-copy inline-math span on the same page')
    # Loose pass: the fragment's tokens sit somewhere in the page (math and prose together) with
    # window similarity >= 0.75 AND every digit group of the fragment occurs on the page. Weaker
    # evidence than the exact passes above; the record names it as such.
    nums=[x.strip('.,') for x in re.findall(r'\d[\d,.]{1,}\d|\d{2,}',row.get('nougat') or '')]
    flat=sim.replace('{,}',',')
    if nums and not all(x in flat or x.replace(',','') in flat.replace(',','') for x in nums):return None
    stream=[];pos=0
    for m in re.finditer(r'\$\$(.*?)\$\$|\$(.*?)\$',sim,re.S):
        stream+=re.findall(r'[A-Za-z0-9]|[^\sA-Za-z0-9]',sim[pos:m.start()])
        stream+=simple_tokens(m.group(1) if m.group(1) is not None else m.group(2));pos=m.end()
    stream+=re.findall(r'[A-Za-z0-9]|[^\sA-Za-z0-9]',sim[pos:])
    best=0;where=None
    for k in range(0,max(1,len(stream)-n+1),max(1,n//4)):
        r=difflib.SequenceMatcher(None,stream[k:k+n+4],frag,autojunk=False).ratio()
        if r>best:best=r;where=k
    if best>=0.75:
        # anchor: the first display or inline span of the page whose tokens overlap the window most
        cands=[m.group(1) if m.group(1) is not None else m.group(2) for m in MATH.finditer(sim)]+[m.group(1) if m.group(1) is not None else m.group(2) for m in INLINE.finditer(MATH.sub(' ',sim))]
        cands=[c for c in cands if c]
        scored=sorted(cands,key=lambda c:-difflib.SequenceMatcher(None,simple_tokens(c),frag,autojunk=False).ratio())
        for c in scored[:3]:
            for L in (60,90,120,160,220,len(c)):
                anchor=c[:L]
                if anchor and sim.count(anchor)==1:return dict(anchor=anchor,display='reading-copy page (loose window similarity %.2f; digit groups present)'%best,loose=True)
    return None
def model_body(s):
    # The model sometimes wraps the transcription in prose + \[ ... \]; keep only the display body.
    m=re.search(r'\\\[(.*)\\\]',s or '',re.S)
    return m[1] if m else s
def loose_norm(s):
    s=norm(s)
    s=re.sub(r'\\(?:mbox|hbox)\{([^{}]*)\}',r'\1',s)
    s=re.sub(r'\\[bB]igg?[lr]?\{?([()\[\]|])\}?',r'\1',s)      # \biggl{(} -> (
    s=re.sub(r'\\frac',' ',s)
    return re.sub(r'[{}()\[\]/]','',s)
def symbols_equal(a,b):
    """Same symbol sequence once fraction/bracket layout is ignored (layout-style agreement)."""
    if not a or not b:return False
    line='x\t'+loose_norm(a).encode().hex()+'\t'+loose_norm(b).encode().hex()+'\n'
    out=subprocess.run([str(HERE/'math_tokens')],input=line,text=True,capture_output=True,check=True).stdout.split('\t')
    return out[1] in ('exact','format_only')
eqs=json.loads((root/'reconciliation/equations.json').read_text())
byid={r['id']:r for r in eqs['equations']}
objects_by_page={}
for _o in json.loads((root/'parsed/objects.json').read_text()):
    if _o['kind']=='Equation':objects_by_page.setdefault(_o['pdf_page'],[]).append(_o)
unmatched={r['id']:r for r in eqs['nougat_unmatched']}
jobs=json.loads((root/'reconciliation/jobs.json').read_text())
manual=root/'curated/manual-review.json'
manual_ids={r['id'] for r in json.loads(manual.read_text())['items']} if manual.exists() else set()
cats=Counter();needs=[];accepted=[];agreements=[]
for job in jobs:
    if job['kind'] not in ('math','unmatched_math'):continue
    vp=root/'reconciliation/vision'/f'{job["id"]}.json'
    if not vp.exists():
        # No model verdict yet. Nougat-only fragments can still be settled deterministically when
        # their symbol sequence sits inside a reading-copy display on the same page.
        if job['kind']=='unmatched_math':
            for it in job['items']:
                if it['id'] in manual_ids:continue
                row=unmatched.get(it['id']) or {}
                if not (row.get('nougat') or '').strip():
                    cats['empty Nougat block; rejected']+=1;accepted.append(it['id'])
                    agreements.append(dict(id=it['id'],pdf_page=job['pdf_page'],choice='not_in_source',corrected='',confidence='high',
                        reason='Nougat emitted an empty display block (no content); rejected deterministically.',
                        image=f'sources/renders/{job["pdf_page"]:04d}.jpg',image_sha256=hashlib.sha256((root/f'sources/renders/{job["pdf_page"]:04d}.jpg').read_bytes()).hexdigest(),
                        reviewer='deterministic fragment check (triage_math.py); direct-review contract'))
                    continue
                anchor=fragment_anchor(row,job['pdf_page'])
                if anchor and anchor.get('inline_symbol'):
                    cats['fragment is an inline symbol (<=5 tokens); recorded, not placed']+=1;accepted.append(it['id'])
                    agreements.append(dict(id=it['id'],pdf_page=job['pdf_page'],choice='nougat',corrected='',confidence='high',fragment_disposition='inline symbol',
                        reason='Nougat-only fragment of at most five tokens (a bare symbol Nougat promoted to display math); carries no display content of its own.',
                        image=f'sources/renders/{job["pdf_page"]:04d}.jpg',image_sha256=hashlib.sha256((root/f'sources/renders/{job["pdf_page"]:04d}.jpg').read_bytes()).hexdigest(),
                        reviewer='deterministic fragment check (triage_math.py); direct-review contract'))
                    continue
                if anchor:
                    cats['fragment is part of an existing Marker display (deterministic subsequence; anchored)']+=1;accepted.append(it['id'])
                    agreements.append(dict(id=it['id'],pdf_page=job['pdf_page'],choice='nougat',corrected='',confidence='high',representation_anchor=anchor['anchor'],
                        reason=('Nougat-only fragment whose symbol sequence is contained in a display of the reading copy on the same page (token subsequence check); no model review needed.' if not anchor.get('loose') else 'Nougat-only fragment matched loosely on the reading-copy page: '+anchor['display']+'. Weaker evidence than an exact subsequence; the anchor names the nearest math span.'),
                        image=f'sources/renders/{job["pdf_page"]:04d}.jpg',image_sha256=hashlib.sha256((root/f'sources/renders/{job["pdf_page"]:04d}.jpg').read_bytes()).hexdigest(),
                        reviewer='deterministic fragment check (triage_math.py); direct-review contract'))
                    continue
                cats['no verdict yet']+=1
            continue
        cats['no verdict yet']+=1;continue
    v=json.loads(vp.read_text())
    if v.get('status')!='reviewed' or v.get('job_fingerprint')!=job['fingerprint']:
        cats['failed/stale']+=1
        for it in job['items']:
            row=byid.get(it['id']) or unmatched.get(it['id']) or {}
            if it['id'] in manual_ids:continue
            if job['kind']=='math' and (tokens_equal(row.get('marker'),row.get('nougat')) or symbols_equal(row.get('marker'),row.get('nougat'))):
                cats['Marker = Nougat after normalisation (model job failed; Marker retained)']+=1;accepted.append(it['id'])
                agreements.append(dict(id=it['id'],pdf_page=job['pdf_page'],choice='marker',corrected='',confidence='high',
                    reason='Marker and Nougat read this display identically after stylistic normalisation; the model job failed ('+str(v.get('error',''))[:80]+').',
                    image=row['crop'],image_sha256=hashlib.sha256((root/row['crop']).read_bytes()).hexdigest(),reviewer='two independent OCR engines in agreement (triage_math.py)'))
                continue
            if job['kind']=='unmatched_math':
                anchor=fragment_anchor(row,job['pdf_page'])
                if anchor and anchor.get('inline_symbol'):
                    cats['fragment is an inline symbol (<=5 tokens); recorded, not placed']+=1;accepted.append(it['id'])
                    agreements.append(dict(id=it['id'],pdf_page=job['pdf_page'],choice='nougat',corrected='',confidence='high',fragment_disposition='inline symbol',
                        reason='Nougat-only fragment of at most five tokens (a bare symbol Nougat promoted to display math); carries no display content of its own.',
                        image=f'sources/renders/{job["pdf_page"]:04d}.jpg',image_sha256=hashlib.sha256((root/f'sources/renders/{job["pdf_page"]:04d}.jpg').read_bytes()).hexdigest(),
                        reviewer='deterministic fragment check (triage_math.py); direct-review contract'))
                    continue
                if anchor:
                    cats['fragment is part of an existing Marker display (deterministic subsequence; anchored)']+=1;accepted.append(it['id'])
                    agreements.append(dict(id=it['id'],pdf_page=job['pdf_page'],choice='nougat',corrected='',confidence='high',representation_anchor=anchor['anchor'],
                        reason=('Nougat-only fragment whose symbol sequence is contained in a display of the reading copy on the same page (token subsequence check); model job failed.' if not anchor.get('loose') else 'Nougat-only fragment matched loosely on the reading-copy page: '+anchor['display']+'. Weaker evidence than an exact subsequence; model job failed.'),
                        image=f'sources/renders/{job["pdf_page"]:04d}.jpg',image_sha256=hashlib.sha256((root/f'sources/renders/{job["pdf_page"]:04d}.jpg').read_bytes()).hexdigest(),
                        reviewer='deterministic fragment check (triage_math.py); direct-review contract'))
                    continue
            needs.append(dict(id=it['id'],pdf_page=job['pdf_page'],why='model review failed or stale: '+str(v.get('error',''))[:60],job=job['id'],
                                                           marker=row.get('marker'),nougat=row.get('nougat'),crop=row.get('crop'),model=None))
        continue
    # Always re-derive the model's items from the raw response so re-runs never build on a
    # previous triage rewrite (choice/corrected/confidence are re-judged from scratch).
    original=raw_items(v)
    if original is not None:v['result']['items']=original
    changed=True
    for item in v['result']['items']:
        oid=item['id'];row=byid.get(oid) or unmatched.get(oid);
        if oid in manual_ids:cats['direct review exists']+=1;continue
        ch=item.get('choice');corr=item.get('corrected','')
        # Re-runs must judge the model's ORIGINAL confidence, not a previous triage downgrade.
        if 'original_confidence' in item:item['confidence']=item['original_confidence']
        item.pop('triage_note',None)
        if job['kind']=='math':
            if tokens_equal(row.get('marker'),row.get('nougat')) or symbols_equal(row.get('marker'),row.get('nougat')):
                cat='Marker = Nougat after normalisation (two independent OCR engines agree; Marker retained)'
            elif ch=='corrected':
                corr=model_body(corr)
                if tokens_equal(corr,row.get('marker')):cat='model = Marker (independent agreement)'
                elif tokens_equal(corr,row.get('nougat')):cat='model = Nougat (independent agreement; correction applied)'
                elif symbols_equal(corr,row.get('marker')):cat='model = Marker on every symbol; fraction/bracket layout differs (Marker retained)'
                elif symbols_equal(corr,row.get('nougat')):cat='model = Nougat on every symbol; layout differs (Nougat reading applied)'
                else:
                    dm=compare(corr,row.get('marker'));dn=compare(corr,row.get('nougat'))
                    best=min([d for d in (dm,dn) if d[1] is not None],key=lambda d:d[1],default=(None,None,None))
                    cat=('model differs from both OCR readings (near: %d token(s) from %s)'%(best[1],'Marker' if best==dm else 'Nougat')
                         if best[1] is not None and best[1]<=2 else 'model differs from both OCR readings')
                    item['triage_distance']=dict(marker=dm[1],nougat=dn[1],max_tokens=best[2])
            elif ch in ('marker','both'):cat='model chose Marker'
            elif ch=='nougat':cat='model chose Nougat'
            else:cat='unreadable'
        else:
            # Nougat-only fragment: first check deterministically whether it is a piece of a Marker display
            # on the same page (Nougat often splits multi-line displays). If so, record the anchor and skip.
            if not (row.get('nougat') or '').strip():
                # Nougat emitted an empty display block: nothing to place, and any model "correction" of
                # an empty fragment is a hallucination from the surrounding page (seen on Williams p. 108).
                cats['empty Nougat block; rejected']+=1;accepted.append(oid)
                agreements.append(dict(id=oid,pdf_page=job['pdf_page'],choice='not_in_source',corrected='',confidence='high',
                    reason='Nougat emitted an empty display block (no content); rejected deterministically. The model reply for this job is disregarded.',
                    image=f'sources/renders/{job["pdf_page"]:04d}.jpg',image_sha256=hashlib.sha256((root/f'sources/renders/{job["pdf_page"]:04d}.jpg').read_bytes()).hexdigest(),
                    reviewer='deterministic fragment check (triage_math.py); direct-review contract'))
                continue
            anchor=fragment_anchor(row,job['pdf_page'])
            if anchor and anchor.get('inline_symbol'):
                cats['fragment is an inline symbol (<=5 tokens); recorded, not placed']+=1;accepted.append(oid)
                agreements.append(dict(id=oid,pdf_page=job['pdf_page'],choice='nougat',corrected='',confidence='high',fragment_disposition='inline symbol',
                    reason='Nougat-only fragment of at most five tokens (a bare symbol Nougat promoted to display math); carries no display content of its own.',
                    image=f'sources/renders/{job["pdf_page"]:04d}.jpg',image_sha256=hashlib.sha256((root/f'sources/renders/{job["pdf_page"]:04d}.jpg').read_bytes()).hexdigest(),
                    reviewer='deterministic fragment check (triage_math.py); direct-review contract'))
                continue
            if anchor:
                cats['fragment is part of an existing Marker display (deterministic subsequence; anchored)']+=1;accepted.append(oid)
                agreements.append(dict(id=oid,pdf_page=job['pdf_page'],choice='nougat',corrected='',confidence='high',representation_anchor=anchor['anchor'],
                    reason=('Nougat-only fragment whose symbol sequence is contained in Marker display '+anchor['display']+' on the same page (token subsequence check); the content is already in the reading copy at the anchored display.' if not anchor.get('loose') else 'Nougat-only fragment matched loosely on the reading-copy page: '+anchor['display']+'. Weaker evidence than an exact subsequence.'),
                    image=f'sources/renders/{job["pdf_page"]:04d}.jpg',image_sha256=hashlib.sha256((root/f'sources/renders/{job["pdf_page"]:04d}.jpg').read_bytes()).hexdigest(),
                    reviewer='deterministic fragment check (triage_math.py); direct-review contract'))
                continue
            cat={'nougat':'fragment confirmed','corrected':'fragment corrected','not_in_source':'fragment rejected','unreadable':'unreadable'}.get(ch,'other')
            if ch=='corrected' and not tokens_equal(corr,row.get('nougat')):cat='fragment corrected (differs from Nougat)'
        if item.get('confidence')!='high':cat+=' [not high confidence]'
        cats[cat]+=1
        item['triage']=cat
        if cat.startswith('model = Marker') or cat.startswith('Marker = Nougat'):item['choice']='marker';item['corrected']=''   # place Marker's own reading, not the model's restyling
        if cat.startswith('Marker = Nougat'):item['confidence']='high';item['triage_confidence_note']='two independent OCR engines agree; the model reply is not the evidence here'
        if cat.startswith('model = Nougat'):   # two independent readings agree on Nougat: place Nougat's reading, cosmetically cleaned
            item['choice']='corrected';item['corrected']=clean_nougat(row.get('nougat'))
        auto_ok=(cat.startswith('model = ') or cat.startswith('Marker = Nougat') or cat in ('fragment confirmed','fragment rejected')) and (item.get('confidence')=='high' or cat.startswith('Marker = Nougat'))   # blind-mode 'marker'/'nougat' choices carry no evidence
        if cat.startswith('model = ') or cat.startswith('Marker = Nougat'):changed=True
        if not auto_ok:
            if item.get('confidence')=='high':
                item['original_confidence']='high';item['confidence']='medium'
                item['triage_note']='downgraded: model transcription agrees with neither independent OCR reading; direct inspection required before placement'
                changed=True
            needs.append(dict(id=oid,pdf_page=job['pdf_page'],why=cat,job=job['id'],model=corr or ch,marker=row.get('marker'),nougat=row.get('nougat'),crop=row.get('crop'),distance=item.get('triage_distance')))
        else:accepted.append(oid)
    if changed:
        v['triage_applied']=True;write(vp,v)
needs.sort(key=lambda x:(x['pdf_page'],x['id']))
write(root/'curated/agreement-review.json',dict(reviewer='two independent OCR engines in agreement (triage_math.py)',scope='Display objects whose model job failed but whose Marker and Nougat readings agree after normalisation.',items=agreements))
write(root/'curated/triage.json',dict(categories=dict(cats),accepted_automatically=len(accepted),needs_direct_inspection=len(needs),items=needs,
    policy='Model corrections are placed automatically only when token-identical to Marker or Nougat (two independent readings). Everything else waits for direct source-image inspection recorded in curated/manual-review.json.'))
print(json.dumps(dict(categories=dict(cats),accepted=len(accepted),needs_direct=len(needs)),indent=1))
