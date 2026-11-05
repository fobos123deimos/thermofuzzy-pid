"""Stable Markdown integration for the TikZ atlas; never changes code cells."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/fobos123deimos/thermofuzzy-pid'
RAW = 'https://raw.githubusercontent.com/fobos123deimos/thermofuzzy-pid/main/'
SITE = 'https://fobos123deimos.github.io/thermofuzzy-pid/'


def atlas_context(name):
    """Return topic-specific diagram links and Colab-compatible image URLs."""
    unit = name[:2]
    plates = json.loads((ROOT/'docs/tikz/catalog.json').read_text(encoding='utf-8'))['plates']
    selected = [p for p in plates if unit in p['notebooks']]
    lines = ['## Read the model and method visually', '',
        '[Six-page vector atlas]('+SITE+'assets/thermal-control-atlas.pdf) · [Gallery and editable TikZ]('+REPO+'/blob/main/docs/DIAGRAMS.md)', '',
        'These original explanatory diagrams distinguish source-reported parameters, reconstruction assumptions and synthetic evidence. Cabinet geometry and sensor positions are illustrative.']
    for p in selected:
        lines += ['', '!['+p['title']+']('+RAW+'docs/figures/tikz/'+p['stem']+'.png)', '', p['caption']]
    return '\n'.join(lines)+'\n'


def update_existing():
    """Refresh only the dedicated Markdown cell, preserving all executable data."""
    import nbformat as nb
    for path in sorted((ROOT/'notebooks').glob('*.ipynb')):
        notebook=nb.read(path,as_version=4)
        old=[(c.source,c.get('outputs',[]),c.get('execution_count')) for c in notebook.cells if c.cell_type=='code']
        notebook.cells=[c for c in notebook.cells if c.get('id') != 'detailed-thermal-atlas']
        cell=nb.v4.new_markdown_cell(atlas_context(path.name)); cell.id='detailed-thermal-atlas'
        notebook.cells.insert(1,cell)
        assert old==[(c.source,c.get('outputs',[]),c.get('execution_count')) for c in notebook.cells if c.cell_type=='code']
        nb.validate(notebook); nb.write(notebook,path)
    print('Updated five notebooks: code cells and saved outputs unchanged.')


if __name__=='__main__':update_existing()
