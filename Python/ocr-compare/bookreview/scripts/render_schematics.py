#!/usr/bin/env python3
"""Render the deliberately small Mermaid subset used by reviewed schematics.

Graphviz creates standalone SVG/PNG for reading. Mermaid stays the editable
source. Unsupported syntax raises an error, rather than dropping connections.
"""
import argparse,json,re,subprocess
from pathlib import Path


def render(path):
    lines=['digraph G {','graph [rankdir=TB,bgcolor="white",fontname="Helvetica"];',
           'node [shape=box,fontname="Helvetica",fontsize=11,style="rounded,filled",fillcolor="#f2f6fa",margin="0.12,0.08"];',
           'edge [color="#263445",arrowsize=0.65];']
    nodes={};edges=[];depth=0
    for raw in path.read_text().splitlines():
        s=raw.strip()
        if not s or s.startswith(('%%','style ')):continue
        if s.startswith('flowchart '):
            direction=s.split()[1];assert direction in ['TD','TB','LR','RL','BT'],s
            lines.append('graph [rankdir='+('TB' if direction=='TD' else direction)+'];');continue
        if s.startswith('subgraph '):
            m=re.fullmatch(r'subgraph (\w+)\["([^"]+)"\]',s);assert m,s
            lines.append(f'subgraph cluster_{m[1]} {{ label={json.dumps(m[2],ensure_ascii=False)}; color="#9aa9bb";');depth+=1;continue
        if s=='end':assert depth>0;lines.append('}');depth-=1;continue
        def box(m):
            name,label=m.groups();nodes[name]=label
            lines.append(f'{name} [label={json.dumps(label,ensure_ascii=False)}];');return name
        s=re.sub(r'(\w+)\["([^"]*)"\]',box,s)
        def point(m):
            name=m[1];nodes[name]='routing junction';lines.append(f'{name} [shape=point,label="",width=0.05];');return name
        s=re.sub(r'(\w+)\(\(" "\)\)',point,s)
        # Optional edge label:  a -->|"label"| b   (Mermaid syntax; rendered as a Graphviz edge label)
        parts=re.split(r'\s*(<-->|-->|-\.-)(?:\|"([^"]*)"\|)?\s*',s)
        assert len(parts)>=4 and len(parts)%3==1,s
        for i in range(0,len(parts)-3,3):
            a,edge,label,b=parts[i:i+4];assert re.fullmatch(r'\w+',a) and re.fullmatch(r'\w+',b),s
            attrs={'-->':[],'<-->':['dir=both'],'-.-':['style=dashed','dir=none','constraint=false']}[edge]
            if label:attrs.append('label='+json.dumps(label,ensure_ascii=False)+',fontsize=9,fontname="Helvetica"')
            attr=(' ['+','.join(attrs)+']') if attrs else ''
            lines.append(f'{a} -> {b}{attr};');edges.append([a,edge,b]+([label] if label else []))
    assert depth==0
    assert all(e[0] in nodes and e[2] in nodes for e in edges),'Undefined node'
    lines.append('}')
    dot=path.with_suffix('.dot');dot.write_text('\n'.join(lines)+'\n')
    for fmt in ['svg','png']:
        subprocess.run(['dot',f'-T{fmt}',str(dot),'-o',str(path.with_suffix('.'+fmt))],check=True)
    path.with_suffix('.render-audit.json').write_text(json.dumps({'nodes':nodes,'edges':edges,'render_engine':'Graphviz','editable_source':path.name},indent=2)+'\n')
    print(path.name,len(nodes),'nodes',len(edges),'edges; SVG and PNG rendered')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path)
    for path in sorted(ap.parse_args().directory.glob('*.mmd')):render(path)
