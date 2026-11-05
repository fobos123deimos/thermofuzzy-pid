"""Compile and verify the six-plate thermal-control TikZ atlas.

Fresh builds require Tectonic 0.17.0, Poppler pdftoppm and pypdf. Verification
uses the standard library and checks the sources, semantic rule-table export,
artifact hashes and PNG dimensions without importing the numerical package.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/tikz'
OUT = ROOT / 'docs/figures/tikz'
ATLAS = 'thermal-control-atlas.pdf'


def sha(path, text=False):
    data = path.read_bytes()
    return hashlib.sha256(data.replace(b'\r\n', b'\n') if text else data).hexdigest()


def rule_tables():
    """Export exact categorical consequents without executing numerical code."""
    tree = ast.parse((ROOT/'src/burnin_pid_fuzzy/fuzzy.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'EXACT_SPARSE_RULES' for t in n.targets))
    rules = ast.literal_eval(node.value)
    assert len(rules) == 7 and all(len(row) == 7 for row in rules)
    lines = ['% Generated from EXACT_SPARSE_RULES; do not edit this table manually.']
    for k, (x, title) in enumerate([(1.0, r'Proportional output $K_p^{\prime}$'), (9.6, r'Integral output $K_i^{\prime}$'), (18.2, r'Derivative output $K_d^{\prime}$')]):
        cells = [triple[k] if triple is not None and triple[k] is not None else '--' for row in rules for triple in row]
        lines.append(r'\rulegrid{' + str(x) + '}{' + title + '}{' + ','.join(cells) + '}')
    return '\n'.join(lines)+'\n'


def sources():
    files = sorted(SOURCE.glob('*.tex')) + [SOURCE/'catalog.json', Path(__file__), ROOT/'src/burnin_pid_fuzzy/fuzzy.py']
    return {p.relative_to(ROOT).as_posix(): sha(p, True) for p in files}


def gallery(catalog):
    lines = ['# Detailed thermal-control atlas', '',
        'Six original TikZ plates connect the chamber picture, mathematical model, implemented control paths and experimental evidence. The cabinet geometry and sensor positions are illustrative. The original thesis, private source files and measured time series are not redistributed.', '',
        '[Complete vector atlas](figures/tikz/'+ATLAS+') · [Editable TikZ sources](tikz/) · [Source and artifact verification](figures/tikz/build.json)', '',
        'The existing model-response, membership-surface and fixed-loop plots are retained as computed figures. The new plates explain their model boundaries and evaluation protocols; they do not introduce new performance measurements.', '',
        '| Plate | Meaning |', '|---|---|']
    for p in catalog['plates']:
        lines.append('| ['+p['title']+'](figures/tikz/'+p['stem']+'.pdf) | '+p['caption']+' |')
    for p in catalog['plates']:
        lines += ['', '## '+p['title'], '', p['caption'], '',
            '!['+p['title']+'](figures/tikz/'+p['stem']+'.png)', '',
            '[Vector PDF](figures/tikz/'+p['stem']+'.pdf) · [TikZ source](tikz/'+p['stem']+'.tex)']
    lines += ['', '## Reproduce and interpret', '',
        'Install Tectonic 0.17.0 and Poppler; install `pypdf` for assembling the PDF. From the repository root:', '',
        '```bash', 'python tools/build_tikz_atlas.py', 'python tools/build_tikz_atlas.py --check', 'python tools/build_api_docs.py', '```', '',
        'Use `--tectonic /path/to/tectonic --pdftoppm /path/to/pdftoppm` when the executables are not on PATH. `--only-cached` avoids TeX-bundle downloads. `--assemble-only` accepts previously verified plates only when their source and artifact hashes still match the last complete build. Inspect each final rendering after editing a figure.', '',
        'The fuzzy matrices are exported directly from `EXACT_SPARSE_RULES`, without importing or modifying the numerical implementation. All six source/PDF/PNG sets and the combined PDF are hashed in the build record.', '',
        'See [source traceability](source_traceability.md), [theory](theoretical_foundations.md) and [the experimental protocol](experimental_protocol.md). The primary parameter source remains Cordeiro, *Projeto de um Controlador PID-Fuzzy para a Câmara de Burn-in*, UFC, 2021. The historical 22%/3% observations are source-reported results, not reproduced outcomes of these drawings.']
    (ROOT/'docs/DIAGRAMS.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tectonic', default='tectonic')
    parser.add_argument('--pdftoppm', default='pdftoppm')
    parser.add_argument('--only-cached', action='store_true')
    parser.add_argument('--assemble-only', action='store_true')
    parser.add_argument('--check', action='store_true')
    args=parser.parse_args()
    catalog=json.loads((SOURCE/'catalog.json').read_text(encoding='utf-8'))
    names=[p['stem'] for p in catalog['plates']]
    assert len(names) == len(set(names)) == 6
    rule_file=SOURCE/'rule-tables.tex'
    expected_rules=rule_tables()
    if args.check:
        if rule_file.read_text(encoding='utf-8') != expected_rules:
            raise ValueError('Sparse consequent export is stale.')
        record=json.loads((OUT/'build.json').read_text(encoding='utf-8'))
        if record['source_sha256_lf'] != sources():
            raise ValueError('Atlas sources changed; rebuild and visually inspect.')
        expected={n+ext for n in names for ext in ('.pdf','.png')} | {ATLAS}
        if set(record['artifact_sha256']) != expected:
            raise ValueError('Incomplete artifact inventory.')
        for name, value in record['artifact_sha256'].items():
            path=OUT/name
            if sha(path) != value: raise ValueError('Changed atlas artifact: '+name)
            if path.suffix == '.png':
                raw=path.read_bytes()
                if raw[:8] != b'\x89PNG\r\n\x1a\n' or max(struct.unpack('>II',raw[16:24])) < 2600:
                    raise ValueError('Invalid or undersized image: '+name)
        print(json.dumps({'status':'passed','plates':6,'artifacts':13,'rule_matrices':3}))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    if not rule_file.exists() or rule_file.read_text(encoding='utf-8') != expected_rules:
        rule_file.write_text(expected_rules, encoding='utf-8')
    def required_hashes(name):
        files=[SOURCE/(name+'.tex'), SOURCE/'common.tex']
        if name=='04-fuzzy-inference':files.append(rule_file)
        return {p.relative_to(ROOT).as_posix():sha(p,True) for p in files}
    compiled={}
    if args.assemble_only:
        previous=json.loads((OUT/'build.json').read_text(encoding='utf-8'))
        for name in names:
            compiled[name]=required_hashes(name)
            if any(previous['source_sha256_lf'].get(p)!=h for p,h in compiled[name].items()):
                raise ValueError('Sources differ from the verified compilation: '+name)
            for ext in ('.pdf','.png'):
                if previous['artifact_sha256'].get(name+ext)!=sha(OUT/(name+ext)):
                    raise ValueError('Artifact differs from the verified compilation: '+name+ext)
    else:
        for name in names:
            compiled[name]=required_hashes(name)
            command=[args.tectonic,'--keep-logs','--outdir',str(OUT)]
            if args.only_cached:command+=['--only-cached']
            subprocess.run(command+[name+'.tex'],cwd=SOURCE,check=True)
            subprocess.run([args.pdftoppm,'-singlefile','-scale-to','2800','-png',str(OUT/(name+'.pdf')),str(OUT/name)],check=True)
    from pypdf import PdfReader, PdfWriter
    writer=PdfWriter()
    for p in catalog['plates']:
        name=p['stem']; pdf=OUT/(name+'.pdf'); png=OUT/(name+'.png')
        if compiled[name]!=required_hashes(name):
            raise ValueError('Atlas source changed during compilation: '+name)
        log=(OUT/(name+'.log')).read_text(encoding='utf-8',errors='replace')
        if any(t in log for t in ('Overfull \\', 'Missing character:', '! LaTeX Error')):
            raise ValueError('Unresolved typesetting warning: '+name)
        reader=PdfReader(pdf)
        if len(reader.pages)!=1:raise ValueError('Expected a one-page plate: '+name)
        writer.add_page(reader.pages[0]); writer.add_outline_item(p['title'],len(writer.pages)-1)
    writer.add_metadata({'/Title':catalog['title'],'/Author':'ThermoFuzzy-PID','/Subject':'Source-traceable thermal control and synthetic experimental design'})
    writer.write(OUT/ATLAS)
    record={'generator':'Tectonic 0.17.0 / TikZ + Poppler + pypdf','plates':6,'png_long_edge':2800,
        'source_sha256_lf':sources(),'artifact_sha256':{n+ext:sha(OUT/(n+ext)) for n in names for ext in ('.pdf','.png')},
        'scope':catalog['scope']}
    record['artifact_sha256'][ATLAS]=sha(OUT/ATLAS)
    (OUT/'build.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    gallery(catalog)
    print(json.dumps({'status':'built','plates':6,'atlas':'docs/figures/tikz/'+ATLAS}))


if __name__=='__main__':main()
