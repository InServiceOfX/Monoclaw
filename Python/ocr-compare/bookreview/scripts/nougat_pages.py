#!/usr/bin/env python3
"""Run the installed Nougat model with durable output for EVERY input page.

Unlike the stock CLI, this preserves page identity, unprocessed decoded tokens,
postprocessed Markdown, token IDs, length-limit flags and resumable sentinels.
No page-skipping heuristic. Run only after other GPU models have exited.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
import time
import copy
import re
from collections import Counter
from pathlib import Path

import pypdfium2 as pdfium
import torch
from nougat import NougatModel
from nougat.utils.device import move_to_device
from nougat.postprocessing import markdown_compatible


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()


def atomic_write(path,content):
    temporary=path.with_name(path.name+'.partial')
    temporary.write_text(content)
    temporary.replace(path)


def run(args):
    args.out.mkdir(parents=True,exist_ok=True)
    for sub in ['raw','pages','metadata','done']:(args.out/sub).mkdir(exist_ok=True)
    signature={'input_pdf':str(args.pdf.resolve()),'sha256':sha(args.pdf),
               'checkpoint':str(args.checkpoint.resolve()),
               'nougat_version':importlib.metadata.version('nougat-ocr'),
               'early_stopping':False,'random_padding':False,'render_dpi':144,
               'torch_version':torch.__version__,'wrapper_schema':3,
               'wrapper_sha256':sha(Path(__file__)),
               'device':args.device,'selected_pages':args.pages,
               'checkpoint_files':{p.name:sha(p) for p in sorted(args.checkpoint.iterdir()) if p.is_file() and p.suffix in ['.json','.bin','.safetensors']},
               'reuse_policy':'Only byte-identical prepared model input tensors; preserve per-page provenance'}
    manifest=args.out/'run.json'
    if manifest.exists():assert json.loads(manifest.read_text())==signature,'Run signature changed'
    else:
        atomic_write(args.out/'run-wrapper.py',Path(__file__).read_text())
        atomic_write(manifest,json.dumps(signature,indent=2)+'\n')
    doc=pdfium.PdfDocument(args.pdf)
    expected=set(range(len(doc))) if not args.pages else {p-1 for p in args.pages}
    assert expected and min(expected)>=0 and max(expected)<len(doc),'Selected page outside PDF'
    pending=[];input_cache={}
    for i in sorted(expected):
        name=f'{i+1:04d}'
        done=args.out/'done'/f'{name}.json'
        if done.exists():
            checks=json.loads(done.read_text())
            assert all(sha(args.out/p)==v for p,v in checks.items()),'Corrupt completed output'
            oldmeta=json.loads((args.out/'metadata'/f'{name}.json').read_text())
            if oldmeta.get('input_tensor_sha256'):input_cache.setdefault(oldmeta['input_tensor_sha256'],i)
        else:pending.append(i)
    # Inference is independent for each page. Similar-length batches avoid
    # padding a short title page to the length of a dense page of calculations.
    coverage=args.out.parent/'extracted/coverage.json'
    if coverage.exists():
        chars={r['ocr_pdf_page']-1:r['characters'] for r in json.loads(coverage.read_text())['pages']}
        pending.sort(key=lambda i:(chars.get(i,0)//1000,chars.get(i,0),i))
    print(f'Nougat {args.pdf.name}: {len(pending)}/{len(expected)} selected pages pending (PDF has {len(doc)})',flush=True)
    if not pending:return
    if args.device=='cuda':assert torch.cuda.is_available(),'GPU required; run with host CUDA access'
    model=NougatModel.from_pretrained(args.checkpoint)
    model=move_to_device(model,bf16=args.device=='cuda',cuda=args.device=='cuda')
    model.eval()
    print(f'Loaded {args.checkpoint}, max_length={model.config.max_length}, batch={args.batch}',flush=True)
    started=time.time()
    batch_size=args.batch
    cursor=0
    def save(i,raw,text,meta):
        name=f'{i+1:04d}'
        paths=[f'raw/{name}.txt',f'pages/{name}.mmd',f'metadata/{name}.json']
        for rel,content in zip(paths,[raw,text,json.dumps(meta,indent=2)+'\n']):
            atomic_write(args.out/rel,content)
        atomic_write(args.out/'done'/f'{name}.json',json.dumps({p:sha(args.out/p) for p in paths},indent=2)+'\n')
    while cursor<len(pending):
        indices=pending[cursor:cursor+batch_size]
        tensors=[];unique_indices=[];hashes={};in_batch={};reused={}
        for i in indices:
            page=doc[i];bitmap=page.render(scale=2)
            pil=bitmap.to_pil().convert('RGB')
            tensor=model.encoder.prepare_input(pil,random_padding=False)
            assert tensor is not None,f'Cannot prepare page {i+1}'
            digest=hashlib.sha256(tensor.contiguous().numpy().tobytes()).hexdigest()
            hashes[i]=digest
            if digest in input_cache:reused[i]=input_cache[digest]
            elif digest in in_batch:reused[i]=in_batch[digest]
            else:
                tensors.append(tensor);unique_indices.append(i);in_batch[digest]=i
            bitmap.close();page.close()
        t=time.time()
        try:
            if tensors:
                with torch.inference_mode():
                    output=model.inference(image_tensors=torch.stack(tensors),early_stopping=False)
            else:output={'predictions':[]}
        except torch.cuda.OutOfMemoryError:
            if batch_size==1:raise
            batch_size=max(1,batch_size//2);torch.cuda.empty_cache()
            print(f'OOM: retrying pending batch with {batch_size} pages; no finished page repeated',flush=True)
            continue
        assert len(output['predictions'])==len(unique_indices),'Model dropped page'
        for j,i in enumerate(unique_indices):
            name=f'{i+1:04d}'
            ids=output['sequences'][j].detach().cpu().tolist()
            raw=model.decoder.tokenizer.decode(ids,skip_special_tokens=True)
            prediction=output['predictions'][j]
            text=markdown_compatible(prediction)
            active=sum(x!=model.decoder.tokenizer.pad_token_id for x in ids)
            hit_limit=active>=model.config.max_length
            # Transformers may force EOS at max_length. This is not evidence
            # that the page ended naturally or that all source content survived.
            eos_positions=[k for k,x in enumerate(ids[1:],1) if x==model.decoder.tokenizer.eos_token_id]
            tokens=re.findall(r'\w+',raw.lower());grams=Counter(tuple(tokens[k:k+4]) for k in range(max(0,len(tokens)-3)))
            repetition=max(grams.values(),default=0)
            flags=[]
            if hit_limit:flags.append('generation reached configured length limit; terminal EOS may be forced')
            if repetition>=8 and repetition*4/max(1,len(tokens))>.2:flags.append('repetitive raw generation')
            if len(raw)>500 and len(prediction)<len(raw)*.5:flags.append('postprocessing removed more than half of raw decoded text')
            marker_page=args.out.parent/'extracted/pages'/f'{i+1:04d}.md'
            if re.search(r'^#+\s*Abstract\b',prediction,re.M) and marker_page.exists() and not re.search(r'^#+\s*\**Abstract\b',marker_page.read_text(),re.M):
                flags.append('Abstract heading unsupported by Marker counterpart; inspect for hallucination')
            parameter=next(model.parameters())
            meta=dict(pdf_page=i+1,raw_token_ids=ids,model_device=str(parameter.device),model_dtype=str(parameter.dtype),
                      generated_tokens=active,hit_length_limit=hit_limit,
                      reached_eos=bool(eos_positions),natural_eos=bool(eos_positions) and not hit_limit,
                      quality_flags=flags,raw_decoded_characters=len(raw),
                      max_length=model.config.max_length,
                      missing_page_marker='[MISSING_PAGE' in prediction,
                      repeats=output['repeats'][j],batch_seconds=time.time()-t,
                      prediction_before_markdown=prediction,input_tensor_sha256=hashes[i])
            save(i,raw,text,meta);input_cache[hashes[i]]=i
        for i,original in reused.items():
            name=f'{original+1:04d}'
            meta=json.loads((args.out/'metadata'/f'{name}.json').read_text())
            meta.update(pdf_page=i+1,reused_from_pdf_page=original+1,input_tensor_sha256=hashes[i],
                        reuse_evidence='Byte-identical prepared image tensor SHA256')
            save(i,(args.out/'raw'/f'{name}.txt').read_text(),(args.out/'pages'/f'{name}.mmd').read_text(),meta)
            input_cache[hashes[i]]=original
        cursor+=len(indices)
        del output,tensors
        elapsed=time.time()-started
        print(f'Nougat saved {cursor}/{len(pending)} pending pages; latest PDF page {indices[-1]+1}; exact-input reuses {len(reused)}; batch {time.time()-t:.1f}s; ETA {(len(pending)-cursor)*elapsed/cursor/60:.1f} min',flush=True)
    assert {int(p.stem)-1 for p in (args.out/'done').glob('*.json')}==expected,'Boundary coverage failure'
    print('Nougat complete: every selected PDF page has raw, Markdown, token metadata and checksums.',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('pdf',type=Path);ap.add_argument('out',type=Path)
    ap.add_argument('--checkpoint',type=Path,default=Path(os.environ['NOUGAT_CHECKPOINT']))
    ap.add_argument('--batch',type=int,default=4)
    ap.add_argument('--device',choices=['cuda','cpu'],default='cuda')
    ap.add_argument('--pages',type=int,nargs='+',help='Optional one-based subset, recorded in manifest; omit for the full book')
    run(ap.parse_args())
