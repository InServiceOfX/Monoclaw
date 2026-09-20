#!/usr/bin/env python3
"""Publish a traceable reading transcription and unresolved-review inventory.

Raw Marker/Nougat/native text is immutable. Only unique literal edits with a
high-confidence source-image verdict are applied. Ambiguous placements remain
visible in the per-page ledger, never silently guessed.
"""
import argparse,hashlib,json,re
from collections import Counter,defaultdict
from pathlib import Path
from extract import write
from reconcile import MATH

HERE=Path(__file__).resolve().parent
HEADER='OCR transcription; consult source images for mathematical authority.\n\n'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def patch_prose(body,before,after):
    if body.count(before)!=1:return body,'nonunique or missing literal anchor'
    start=body.index(before);end=start+len(before)
    if any(start<m.end() and end>m.start() for m in MATH.finditer(body)):
        return body,'text patch overlaps a separately reviewed display formula'
    return body.replace(before,after,1),None

def replace_formula(body,old,chosen,labels):
    # Markdown and JSON renderers differ in spacing and in where labels live.
    # Match one whole display by identical non-whitespace source tokens only.
    def normalized(value):
        for label in labels:
            value=re.sub(r'\\tag\*?\{'+re.escape(label)+r'\}', '', value)
            value=re.sub(r'\('+re.escape(label)+r'\)\s*$', '', value)
        return re.sub(r'\s+','',value)
    if not old.strip():return body,False
    matches=[]
    for match in MATH.finditer(body):
        group=1 if match.group(1) is not None else 2
        if normalized(match.group(group))==normalized(old):matches.append((match.start(group),match.end(group)))
    if len(matches)!=1:return body,False
    start,end=matches[0]
    return body[:start]+chosen+body[end:],True

def assemble(book):
    root=Path(book['root']);parsed=root/'parsed';rec=root/'reconciliation'
    jobs=json.loads((rec/'jobs.json').read_text())
    equations=json.loads((rec/'equations.json').read_text())
    objects=json.loads((parsed/'objects.json').read_text())
    coverage=json.loads((parsed/'coverage.json').read_text())
    pagemap={x['pdf_page']:x['printed_page'] for x in json.loads((root/'sources/page-map.json').read_text())['pages']}
    scopefile=root/'curated/review-scope.json'
    review_scope=json.loads(scopefile.read_text()) if scopefile.exists() else {}
    bounded=review_scope.get('automatic_prose_edits') is False
    required_kinds=set(review_scope.get('required_review_kinds',[]))
    model_proposals=[]
    annotations=defaultdict(list)
    annotationfile=root/'annotations/errata-review.json'
    if annotationfile.exists():
        for item in json.loads(annotationfile.read_text())['entries']:annotations[item['pdf_page']].append(item)
    verdicts={};jobstates=[]
    for job in jobs:
        path=rec/'vision'/f'{job["id"]}.json'
        row=dict(id=job['id'],kind=job['kind'],pdf_page=job['pdf_page'],status='pending')
        if path.exists():
            data=json.loads(path.read_text())
            if data.get('job_fingerprint')!=job['fingerprint']:row['status']='stale verdict'
            elif data.get('status')=='reviewed':
                row['status']='reviewed'
                if bounded and job['kind']=='text':
                    row['status']='model proposal retained; not accepted as source verification'
                    model_proposals.append(dict(job=job['id'],record=str(path.relative_to(root)),
                        disposition='Not applied: prose reviewer failed source-fidelity assessment',result=data['result']))
                else:
                    for item in data['result']['items']:
                        verdicts[item['id']]=dict(item,job=job['id'],record=str(path.relative_to(root)),
                            image=job['image'],image_sha256=job['image_sha256'],reviewer='local source-image model')
            else:row.update(status='failed',error=data.get('error'))
        jobstates.append(row)
    # Two authority files: direct inspections (manual-review.json) and, lower priority, automatic
    # two-engine agreements recorded by triage_math.py for jobs whose model review failed.
    reviewed_all={}
    for relfile,method in [('curated/agreement-review.json','Marker/Nougat agreement (triage; model job failed)'),
                           ('curated/manual-review.json','direct source-image inspection')]:
        manualfile=root/relfile
        if not manualfile.exists():continue
        manual=json.loads(manualfile.read_text())
        for item in manual['items']:
            assert sha(root/item['image'])==item['image_sha256'], 'Changed manually reviewed source image'
            verdicts[item['id']]=dict(item,record=relfile,reviewer=item.get('reviewer',manual['reviewer']))
            reviewed_all[item['id']]=method
    # Objects reclassified by direct inspection (curated/object-classification-review.json: a Marker 'Table'
    # that is really a caption or a two-column text block) need no table verdict; their table jobs are settled.
    classfile=root/'curated/object-classification-review.json'
    if classfile.exists():
        for item in json.loads(classfile.read_text())['items']:
            assert sha(root/item['image'])==item['image_sha256'], 'Changed classification-review source image'
            reviewed_all.setdefault(item['id'],f"direct classification review (object is a {item['reviewed_kind']}, not a table)")
    for job,state in zip(jobs,jobstates):
        if reviewed_all and all(item['id'] in reviewed_all for item in job['items']):
            methods=sorted({reviewed_all[item['id']] for item in job['items']})
            state.update(status='reviewed',method=' + '.join(methods))
    bypage=defaultdict(list)
    for row in equations['equations']+equations['nougat_unmatched']:bypage[row['pdf_page']].append(row)
    visual=defaultdict(list)
    for obj in objects:
        if obj['kind']!='Equation':visual[obj['pdf_page']].append(obj)
    out=parsed/'reconciled-pages';out.mkdir(exist_ok=True)
    ledgers=[];unresolved=[];unreviewed=[];masters=[];counts=Counter();pageobjects=[]
    for n in range(1,book['expected_pdf_pages']+1):
        rawpage=parsed/'pages'/f'{n:04d}.md'
        if not rawpage.exists():continue
        body=rawpage.read_text().split(HEADER,1)[-1]
        ledger=[];notes=[]
        # Text patches refer to the original Marker body. Apply text first;
        # display math is adjudicated separately and never changed heuristically.
        textid=f'{book["id"]}:p{n:04d}:text';tv=verdicts.get(textid)
        if tv:
            for patch in tv['patches']:
                if patch['before']==patch['after']:continue
                entry=dict(id=textid,kind='text',before=patch['before'],after=patch['after'],verdict=tv['record'])
                patched,problem=patch_prose(body,patch['before'],patch['after'])
                if tv['confidence']=='high' and problem is None:
                    body=patched;entry['status']='applied literal source-reviewed patch'
                    counts['text_patches_applied']+=1
                else:
                    entry['status']='unresolved: '+(problem or 'confidence below high');unresolved.append(dict(pdf_page=n,**entry))
                ledger.append(entry)
            if tv['confidence']!='high' or tv['unresolved']:
                unresolved.append(dict(id=textid,pdf_page=n,kind='text',status='source review needs follow-up',verdict=tv))
        for row in bypage[n]:
            verdict=verdicts.get(row['id']);chosen=row.get('marker');status=row['status']
            entry=dict(id=row['id'],kind='equation',status=status,
                       marker=row.get('marker'),nougat=row.get('nougat'))
            if status in ['exact','format_only'] and not verdict:
                entry['status']='independent OCR agreement; not separately source-verified'
                counts['equations_ocr_agreement']+=1
            elif verdict:
                entry['verdict']=verdict
                decision=verdict['choice']
                if verdict['confidence']!='high' or decision=='unreadable':
                    entry['status']='unresolved source review';unresolved.append(dict(pdf_page=n,**entry))
                elif decision=='not_in_source':
                    entry['status']='Nougat-only candidate rejected by source review';chosen=None
                else:
                    chosen=(row.get('marker') if decision in ['marker','both'] else row.get('nougat') if decision=='nougat' else verdict['corrected'])
                    entry['selected_latex']=chosen
                    if not isinstance(chosen,str) or not chosen.strip() or (decision=='both' and not row.get('nougat')):
                        entry['status']='unresolved: source review selected an unavailable OCR candidate'
                        unresolved.append(dict(pdf_page=n,**entry))
                    elif chosen==row.get('marker'):
                        entry['status']='Marker retained by source review';counts['equations_source_reviewed']+=1
                    elif verdict.get('fragment_disposition')=='inline symbol':
                        # A Nougat-only fragment of at most five tokens (a bare symbol such as f,
                        # T_s or c_p that Nougat promoted to display math) carries no display
                        # content of its own; it is recorded, not placed.
                        assert 'direct' in str(verdict.get('reviewer','')) or 'Claude' in str(verdict.get('reviewer',''))
                        entry['status']='Nougat-only fragment is an inline symbol (<=5 tokens); no display content to place'
                        counts['unmatched_inline_symbols']=counts.get('unmatched_inline_symbols',0)+1
                    elif verdict.get('representation_anchor'):
                        # Nougat can promote definitions, inline math or one
                        # line of an existing display into a second object.
                        # A directly checked, unique reading-copy anchor proves
                        # that the source content is already represented.
                        assert 'direct' in str(verdict.get('reviewer','')) or 'Claude' in str(verdict.get('reviewer',''))
                        anchor=verdict['representation_anchor']
                        if body.count(anchor)==1:
                            entry['status']='source-reviewed content already represented at explicit unique anchor'
                            counts['unmatched_content_represented']+=1
                        else:
                            entry['status']='source-reviewed representation anchor unresolved'
                            unresolved.append(dict(pdf_page=n,**entry))
                    else:
                        # An omitted label is not a request to remove the
                        # book's equation number. Preserve one existing label
                        # explicitly, while keeping the model's exact answer
                        # in selected_latex and its raw review record.
                        replacement=chosen
                        original_labels=row.get('printed_labels',[])
                        if len(original_labels)==1 and not re.search(r'\\tag\*?\{',chosen):
                            replacement=chosen+r' \tag{'+original_labels[0]+'}'
                            entry['label_handling']='Retained the existing OCR equation label; reviewer omitted a label. This retention is not an independent label verification.'
                        if verdict.get('placement_before'):
                            before=verdict['placement_before'];after=verdict['placement_after']
                            assert 'direct' in str(verdict.get('reviewer','')) or 'Claude' in str(verdict.get('reviewer','')), 'Region replacement requires direct source review'
                            placed=body.count(before)==1
                            patched=body.replace(before,after,1) if placed else body
                            entry['placement_method']='explicit unique source-reviewed region; retained exact before/after in verdict'
                        else:
                            patched,placed=replace_formula(body,row.get('marker') or '',replacement,original_labels)
                        if placed:
                            body=patched
                            entry['status']='applied source-reviewed equation to uniquely token-identical display'
                            counts['equations_corrected']+=1
                        else:
                            entry['status']='source-reviewed candidate retained in ledger; placement unresolved'
                            unresolved.append(dict(pdf_page=n,**entry))
                            notes+=['',f'Equation placement needs review: `{row["id"]}`.', '', '$$'+chosen+'$$' if chosen else 'Unreadable.']
            else:
                entry['status']='awaiting source review';unresolved.append(dict(pdf_page=n,**entry))
            ledger.append(entry)
        for obj in visual[n]:
            classification=obj.get('classification_review')
            if classification and obj['kind'] in ['Caption','Text']:
                assert sha(root/classification['image'])==classification['image_sha256'], 'Changed classification-review source image'
                ledger.append(dict(id=obj['id'],kind=obj['kind'],status='source-verified object classification; text reviewed at page level',
                    classification_review=classification))
                pageobjects.append(dict(obj,classification_status='source-verified'))
                continue
            v=verdicts.get(obj['id'])
            entry=dict(id=obj['id'],kind=obj['kind'],source_crop=obj['crop'],verdict=v,
                       status='source-reviewed' if v and v['confidence']=='high' and not v.get('unresolved') else 'unresolved')
            if bounded and obj['kind'] in ['Picture','Figure'] and not v:
                entry['status']='raw extraction; source image retained; not separately source-reviewed'
                unreviewed.append(dict(pdf_page=n,**entry))
                pageobjects.append(dict(obj,review_status=entry['status']))
            if entry['status']=='unresolved':unresolved.append(dict(pdf_page=n,**entry))
            ledger.append(entry)
            if v:
                pageobjects.append(dict(obj,source_review=v))
                if obj['kind']=='Table':
                    write(parsed/'tables'/f'{obj["slug"]}-source-review.json',v)
                    rows=v.get('rows',[])
                    width=max((len(row) for row in rows),default=0)
                    if rows and width:
                        def mdrow(row):
                            return '| '+' | '.join(str(x).replace('|',r'\|').replace('\n','<br>') for x in row+['']*(width-len(row)))+' |'
                        tablemd=['# Source-reviewed table '+obj['id'],'',
                            f'Reviewer: {v.get("reviewer", "source-image model")}. Status: {entry["status"]}. Consult the source and retained raw span metadata.','',
                            f'[Reviewed source image](../../{v.get("image",obj["crop"])})','',mdrow(rows[0]),'| '+' | '.join(['---']*width)+' |',
                            *[mdrow(row) for row in rows[1:]]]
                        if v.get('footnotes'):
                            tablemd+=['','Table notes:','',*['- '+note for note in v['footnotes']]]
                        if v.get('source_conditions'):tablemd+=['',v['source_conditions']]
                        tablefile=f'{obj["slug"]}-source-review.md'
                        (parsed/'tables'/tablefile).write_text('\n'.join(tablemd)+'\n')
                        notes+=['',f'Table `{obj["id"]}` has a [separate source-reviewed cell transcription](../tables/{tablefile}); the original table layout above remains raw OCR.']
                else:
                    notes+=['',f'Source-image description of `{obj["id"]}`: '+v.get('description',''),
                            'Visible labels: '+', '.join(v.get('visible_labels',[]))+'.']
        # A page with pending/failed whole-text review cannot be called settled.
        for jobstate in jobstates:
            if jobstate['pdf_page']==n and jobstate['status']!='reviewed':
                if bounded and jobstate['kind'] not in required_kinds:
                    if jobstate['kind']=='text':
                        unreviewed.append(dict(pdf_page=n,id=jobstate['id'],kind='text',
                            status='complete OCR retained; no accepted whole-page source review',model_status=jobstate['status']))
                else:
                    unresolved.append(dict(pdf_page=n,id=jobstate['id'],kind=jobstate['kind'],status=jobstate['status']))
        for note in annotations[n]:
            notes+=['',f'**Separate author erratum — {note["locator"]}.** '
                f'This copy prints `{note["printed"]}`. The correction is `{note["correction"]}`. '
                f'[Authors’ correction sheet](../../annotations/author-errata.pdf) · '
                f'[Checked source image](../../{note["source_image"]}). The source transcription is retained.']
        ledgers.append(dict(pdf_page=n,printed_page=pagemap[n],edits_and_decisions=ledger))
        ledgerpath=rec/'pages';ledgerpath.mkdir(exist_ok=True)
        write(ledgerpath/f'{n:04d}.json',ledgers[-1])
        title=f'PDF page {n}'+(f' · printed {pagemap[n]}' if pagemap[n] is not None else '')
        prefix=f'# {title}\n\n[Source image](../../sources/renders/{n:04d}.jpg) · '
        prefix+=f'[Raw Marker page](../pages/{n:04d}.md) · [Decision ledger](../../reconciliation/pages/{n:04d}.json)\n\n'
        prefix+=('Reading transcription with directly source-checked math/table corrections. General prose and figure review coverage is recorded separately.\n\n'
                 if bounded else 'Reading transcription with source-image model review and explicit unresolved items. OCR agreement alone is not proof.\n\n')
        finalbody=body+'\n'+'\n'.join(notes)
        (out/f'{n:04d}.md').write_text(prefix+finalbody+'\n')
        # Adjust image links from per-page directory to the master directory.
        masterbody=finalbody.replace('](../../sources/','](../sources/').replace('](../../parsed/','](../parsed/').replace('](../tables/','](tables/').replace('](../../annotations/','](../annotations/')
        masters.append(f'## {title}\n\n[Page, source and decisions](reconciled-pages/{n:04d}.md)\n\n'+masterbody)
    compared=json.loads((rec/'summary.json').read_text())['pages_compared']
    required_states=[x for x in jobstates if not bounded or x['kind'] in required_kinds]
    complete=(coverage['completed_pages']==book['expected_pdf_pages'] and compared==book['expected_pdf_pages']
              and bool(required_states) and all(x['status']=='reviewed' for x in required_states))
    final_status=('parsing and math/table source review complete' if bounded and complete and not unresolved else
                  'core parsing complete with unresolved items' if bounded and complete else
                  'review complete with unresolved items' if complete and unresolved else
                  'review complete' if complete else 'review in progress')
    summary=dict(book=book['id'],expected_pdf_pages=book['expected_pdf_pages'],
        marker_pages=coverage['completed_pages'],compared_pages=compared,
        vision_jobs=len(jobs),vision_job_status=dict(Counter(x['status'] for x in jobstates)),
        counts=dict(counts),unresolved_records=len(unresolved),
        status=final_status,review_policy=review_scope,
        required_source_review_status=dict(Counter(x['status'] for x in required_states)),
        unreviewed_context=dict(Counter(x['kind'] for x in unreviewed)),
        scope='Full independent OCR passes; direct source review of detected display math, unmatched math and numerical tables. General prose/figures have explicitly recorded review coverage; no claim of error-free OCR or proof of the printed mathematics.' if bounded else 'Model-reviewed transcription; no claim of error-free OCR or mathematical verification of the whole book.')
    write(rec/'publication-summary.json',summary);write(rec/'unresolved.json',unresolved)
    write(rec/'job-status.json',jobstates);write(parsed/'visual-objects-reviewed.json',pageobjects)
    write(rec/'unreviewed-context.json',unreviewed);write(rec/'model-prose-proposals.json',model_proposals)
    title=f'# {book["title"]}\n\n{book["edition"]}\n\n'
    title+=f'Status: **{summary["status"]}**. {len(unresolved)} unresolved records. '
    title+='See [review summary](../reconciliation/publication-summary.json) and [unresolved inventory](../reconciliation/unresolved.json).\n\n'
    if bounded:title+='General prose/figure coverage: [unreviewed context](../reconciliation/unreviewed-context.json). Raw source images and both complete OCR passes remain available.\n\n'
    (parsed/'book-reconciled.md').write_text(title+'\n\n'.join(masters)+'\n')
    write(rec/'published-hashes.json',{str(p.relative_to(root)):sha(p) for p in [parsed/'book-reconciled.md',*sorted(out.glob('*.md'))]})
    print(json.dumps(summary),flush=True)
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--book');args=ap.parse_args()
    for book in json.loads((HERE/'books.json').read_text())['books']:
        if not args.book or args.book==book['id']:assemble(book)
