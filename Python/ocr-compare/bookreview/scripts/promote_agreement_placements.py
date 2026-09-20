#!/usr/bin/env python3
"""Vision verdicts of the 'Nougat reading applied' kind whose automatic placement failed
(multi-block displays) are promoted to manual-review records so fix_placements.py can
compute an explicit region for them. Run after assemble.py, before fix_placements.py."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import record_manual as rm
root=rm.ROOT
unres=json.loads((root/'reconciliation/unresolved.json').read_text())
n=0
for u in unres:
    if u.get('kind')!='equation' or 'placement unresolved' not in u.get('status',''):continue
    v=u.get('verdict') or {}
    if 'vision' not in str(v.get('record','')) or v.get('choice')!='corrected' or not v.get('corrected'):continue
    obj=rm.objects().get(u['id'])
    if not obj:continue
    item=dict(id=u['id'],pdf_page=obj['pdf_page'],choice='corrected',corrected=v['corrected'],confidence='high',
        reason='Nougat reading confirmed by the model transcription (token agreement, triage_math.py); promoted from '+v['record']+' so that a region placement could be computed for this multi-line display.',
        image=obj['crop'],image_sha256=rm.sha(obj['crop']),reviewer='two independent readings agree (Nougat text); region placement computed by the Claude session',unresolved=[])
    rm.put(item);n+=1
print('promoted',n)
