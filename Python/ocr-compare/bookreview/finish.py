#!/usr/bin/env python3
"""Bounded source review (math, tables, unmatched math, figures) with a local
VLM, then assemble + publish. Generalized from humble-work/finish.py: the book
identity comes from scripts/books.json; prose (text) jobs are NOT model-reviewed
(policy inherited from the Humble run, where automatic prose edits failed
source-fidelity checks)."""
import fcntl,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'scripts'))
import vision_review,assemble as assembly_module
BOOK=json.loads((HERE/'scripts/books.json').read_text())['books'][0]
ROOT=Path(BOOK['root'])
MODEL_SPEC=vision_review.MODEL_SPEC;MODEL=Path(MODEL_SPEC['directory'])
CONTAINER=f'{BOOK["id"]}-source-review'
LABEL=f'{BOOK["id"]}-book-'+time.strftime('%Y-%m-%d')
PORT=8878
KINDS=['math','table','unmatched_math','figure']   # no 'text'
history=[];logproc=None;restart_count=0
def save(**fields):
    target=HERE/'finish-state.json';tmp=target.with_suffix('.partial')
    tmp.write_text(json.dumps(dict(pid=os.getpid(),updated=time.time(),history=history,**fields),indent=2)+'\n');tmp.replace(target)
def healthy():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health',timeout=5) as r:return r.status==200
    except Exception:return False
def stop_owned():
    p=subprocess.run(['docker','inspect',CONTAINER],capture_output=True,text=True)
    if p.returncode==0:
        obj=json.loads(p.stdout)[0]
        assert obj['Config']['Labels'].get('org.propulsion.task')==LABEL,'Unrelated container'
        subprocess.run(['docker','stop','-t','20',CONTAINER],capture_output=True,check=True)
        subprocess.run(['docker','rm',CONTAINER],capture_output=True,check=True)
def start_model():
    global restart_count,logproc
    if healthy():
        check=subprocess.run(['docker','inspect',CONTAINER],capture_output=True,text=True)
        if check.returncode or json.loads(check.stdout)[0]['Config']['Labels'].get('org.propulsion.task')!=LABEL:
            raise RuntimeError('Review port is occupied by another service')
        return
    restart_count+=1
    if restart_count>8:raise RuntimeError('Vision service repeatedly failed; stop instead of recording hundreds of connection errors')
    stop_owned()
    cmd=['docker','run','-d','--pull','never','--name',CONTAINER,
         '--label','org.propulsion.task='+LABEL,'--network','host','--gpus','device=1',
         '--mount',f'type=bind,src={MODEL},dst=/models,readonly',
         'ghcr.io/ggml-org/llama.cpp:server-cuda',
         '--model','/models/'+MODEL_SPEC['weights'],'--mmproj','/models/'+MODEL_SPEC['projector'],
         '--alias','book-vision','--host','127.0.0.1','--port',str(PORT),
         '--ctx-size','16384','--parallel','1','--n-gpu-layers','all',
         '--flash-attn','on','--batch-size','256','--ubatch-size','64',
         '--threads','4','--threads-batch','4','--reasoning','off','--reasoning-budget','0',
         '--chat-template-kwargs','{"enable_thinking":false}','--image-min-tokens','1024','--image-max-tokens','4096']
    proc=subprocess.run(cmd,capture_output=True,text=True,check=True)
    logfile=ROOT/'logs'/f'vision-server-{os.getpid()}-{restart_count}.log'
    with logfile.open('w') as log:logproc=subprocess.Popen(['docker','logs','-f',CONTAINER],stdout=log,stderr=subprocess.STDOUT)
    history.append(dict(stage='start vision service',command=cmd,container=proc.stdout.strip(),log=str(logfile)))
    deadline=time.time()+420
    while not healthy():
        inspect=subprocess.run(['docker','inspect','--format','{{.State.Running}}',CONTAINER],capture_output=True,text=True)
        if inspect.stdout.strip()=='false':raise RuntimeError('Vision container failed to start; inspect '+str(logfile))
        if time.time()>deadline:raise RuntimeError('Vision model startup timeout')
        time.sleep(5)
def command(script,*args):
    save(stage=script,status='running')
    with (ROOT/'logs'/(script+'.log')).open('a') as out:
        subprocess.run([sys.executable,'-B',str(HERE/'scripts'/script),*args],stdout=out,stderr=subprocess.STDOUT,check=True)
def main():
    lock=(HERE/'finish.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    status=(HERE/'OCR-STATE.txt').read_text().strip()
    assert status.startswith('OCR and comparison complete'),'OCR not finished: '+status
    (ROOT/'curated').mkdir(exist_ok=True)
    scope=ROOT/'curated/review-scope.json'
    if not scope.exists():
        scope.write_text(json.dumps(dict(automatic_prose_edits=False,required_review_kinds=['math','table','unmatched_math'],
            model_reviewed_kinds=KINDS,
            policy='Local VLM reviews display math (blind transcription), tables (guarded full-page), Nougat-only fragments and figure crops. '
                   'Whole-page prose is not model-edited; that reviewer failed source-fidelity checks on the Humble corpus. '
                   'Direct source-image inspection records in curated/manual-review.json override model verdicts.',
            triage='Model verdicts are triage only (scripts/triage_math.py): a transcription is placed automatically only when two independent readings agree after stylistic normalisation (Marker = Nougat, or model = Marker/Nougat; recorded in curated/agreement-review.json); every remaining display object is inspected directly on the source crop by the Claude session and recorded with the crop image hash in curated/manual-review.json (the authority). Corrected transcriptions carry the printed equation label as \\tag{}; annotated balances are set with \\underbrace; multi-line displays as aligned/gathered.',
            verdict_precedence=['curated/manual-review.json (direct inspection)','curated/agreement-review.json (two independent readings)','reconciliation/vision/*.json (model, triage only)','parsed/objects.json (Marker)']),indent=2)+'\n')
    gate=json.loads((HERE/'calibration-acceptance.json').read_text())
    assert gate['approved_for_bounded_model_review']
    assert gate.get('review_protocol')==vision_review.REVIEW_PROTOCOL
    assert gate.get('model_signature')==vision_review.MODEL_SIGNATURE
    if (HERE/'scripts/catalog_book.py').exists():command('catalog_book.py')
    command('augment_tables.py')
    command('reconcile.py')
    jobs=json.loads((ROOT/'reconciliation/jobs.json').read_text())
    rank={'math':0,'table':1,'unmatched_math':2,'figure':3}
    jobs=[j for j in jobs if j['kind'] in KINDS]
    jobs.sort(key=lambda j:(rank[j['kind']],j['pdf_page'],j['id']))
    manual_path=ROOT/'curated/manual-review.json'
    start_model()
    counts={};consecutive_failures=0
    try:
        for i,job in enumerate(jobs):
            manual_ids={r['id'] for r in json.loads(manual_path.read_text())['items']} if manual_path.exists() else set()
            agree_path=ROOT/'curated/agreement-review.json'
            if agree_path.exists():manual_ids|={r['id'] for r in json.loads(agree_path.read_text())['items']}
            if all(item['id'] in manual_ids for item in job['items']):
                counts['direct_source_review']=counts.get('direct_source_review',0)+1;continue
            if not healthy():start_model()
            save(stage='source-image review',status='running',completed=i,total=len(jobs),kind=job['kind'],job=job['id'],counts=counts)
            result=vision_review.run_job(ROOT,job,limit=7000 if job['kind']=='table' else 2200)
            # A length-limited reply is a runaway generation; retrying with a bigger budget only burns GPU time.
            if result['status']=='failed' and 'length' not in str(result.get('error','')):
                if not healthy():start_model()
                result=vision_review.run_job(ROOT,job,limit=10000 if job['kind']=='table' else 3000)
            counts[result['status']]=counts.get(result['status'],0)+1
            consecutive_failures=consecutive_failures+1 if result['status']=='failed' else 0
            if consecutive_failures>=25 and not healthy():raise RuntimeError('Repeated review failures with an unhealthy server; inspect raw replies before continuing')
            if (i+1)%100==0:assembly_module.assemble(BOOK)
        command('augment_tables.py')
        found=json.loads((ROOT/'parsed/table-caption-census.json').read_text())['augmented']
        if found:
            command('reconcile.py')
            seen={job['fingerprint'] for job in jobs}
            recovered=[job for job in json.loads((ROOT/'reconciliation/jobs.json').read_text()) if job['kind']=='table' and job['fingerprint'] not in seen]
            for index,job in enumerate(recovered):
                save(stage='recovered table review',status='running',completed=index,total=len(recovered),job=job['id'])
                if not healthy():start_model()
                result=vision_review.run_job(ROOT,job,limit=7000)
                if result['status']=='failed':result=vision_review.run_job(ROOT,job,limit=10000)
    finally:stop_owned()
    command('triage_math.py')
    summary=assembly_module.assemble(BOOK)
    if (HERE/'scripts/publish_book.py').exists():command('publish_book.py')
    save(stage='review, assembly and publication finished',status='complete; inspect review coverage',summary=summary)
if __name__=='__main__':
    try:main()
    except Exception as e:
        save(stage='needs attention',status='failed',error=str(e));raise
