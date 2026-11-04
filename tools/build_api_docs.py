"""Build and check the pdoc site without running thermal experiments.

Run from any working directory. Generated output is confined to docs/api or
build/ inside this checkout; existing research notes and validation files are not
build destinations.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from html.parser import HTMLParser
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import unquote, urlsplit, quote

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'src/burnin_pid_fuzzy'
REPOSITORY = 'https://github.com/fobos123deimos/thermofuzzy-pid'
ASSETS = sorted((ROOT / 'docs/figures').glob('*.png')) + [ROOT / 'images/synthetic_controller_comparison.png']


class Page(HTMLParser):
    """Collect rendered anchors and local assets for a static-site check."""
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids, self.links = set(), []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if key in attrs:
                self.links.append(attrs[key])


def inventory():
    """Read public definitions from source, without counting nested callbacks."""
    modules, missing = {}, []
    for source in sorted(PACKAGE.glob('*.py')):
        name = 'burnin_pid_fuzzy' + ('.' + source.stem if source.stem != '__init__' else '')
        tree = ast.parse(source.read_text(encoding='utf-8'))
        public = []
        if not ast.get_docstring(tree):
            missing.append(name)
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.ClassDef)) or node.name.startswith('_'):
                continue
            public.append(node.name)
            if not ast.get_docstring(node):
                missing.append(name + '.' + node.name)
            if isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and not method.name.startswith('_'):
                        public.append(node.name + '.' + method.name)
                        if not ast.get_docstring(method):
                            missing.append(name + '.' + node.name + '.' + method.name)
        modules[name] = {'source': source.relative_to(ROOT).as_posix(), 'public_definitions': public}
    if missing:
        raise ValueError('Missing public docstrings: ' + ', '.join(missing))
    return modules


def checked_destination(path):
    path = path.resolve()
    if path != ROOT / 'docs/api' and not path.is_relative_to(ROOT / 'build'):
        raise ValueError('Output must be docs/api or a directory under build/ in this checkout.')
    return path


def validate_site(output, modules):
    pages = {p.resolve(): Page(p.read_text(encoding='utf-8')) for p in output.rglob('*.html')}
    expected = {output / (name.replace('.', '/') + '.html') for name in modules}
    expected.add(output / 'index.html')
    if set(pages) != expected:
        raise ValueError('Generated page set differs from the source module inventory.')
    for name, info in modules.items():
        page = output / (name.replace('.', '/') + '.html')
        absent = set(info['public_definitions']) - pages[page].ids
        if absent:
            raise ValueError(f'{name}: missing public API anchors: {sorted(absent)}')
    checked = 0
    for source, parsed in pages.items():
        text = source.read_text(encoding='utf-8')
        if re.search(r'file:///|[A-Za-z]:[\\/](?:Users|home|runner)[\\/]', text):
            raise ValueError(f'Machine-specific path leaked into {source.name}')
        for value in parsed.links:
            target = urlsplit(value)
            if target.scheme or target.netloc:
                continue
            destination = (source.parent / unquote(target.path)).resolve() if target.path else source
            if not destination.is_relative_to(output) or not destination.is_file():
                raise ValueError(f'Broken local link in {source.name}: {value}')
            if target.fragment and destination in pages and unquote(target.fragment) not in pages[destination].ids:
                raise ValueError(f'Broken anchor in {source.name}: {value}')
            checked += 1
    search = output / 'search.js'
    if not search.is_file() or search.stat().st_size < 100:
        raise ValueError('pdoc search index is missing or empty.')
    return {'html_pages': len(pages), 'modules': len(modules),
            'public_definitions': sum(len(m['public_definitions']) for m in modules.values()),
            'local_links_checked': checked, 'illustration_files': len(ASSETS), 'status': 'passed'}


def source_hashes():
    sources = sorted(PACKAGE.glob('*.py')) + sorted((ROOT / 'docs/pdoc-template').glob('*'))
    sources += [ROOT / 'tools/build_api_docs.py', ROOT / 'requirements-docs.txt',
                ROOT / 'pyproject.toml', ROOT / 'scripts/build_documentation_figures.py']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            for p in sources if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/api')
    parser.add_argument('--check', action='store_true', help='Verify existing output and hashes without rebuilding.')
    args = parser.parse_args()
    output = checked_destination(args.output if args.output.is_absolute() else ROOT / args.output)
    modules = inventory()
    if args.check:
        record = json.loads((output / 'build.json').read_text(encoding='utf-8'))
        if record['source_sha256_lf'] != source_hashes():
            raise ValueError('Documentation is stale: source/template hashes changed. Rebuild first.')
        if record['image_source_sha256'] != {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in ASSETS}:
            raise ValueError('Documentation images changed. Rebuild first.')
        actual_artifacts = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file() and p.name != 'build.json'}
        if actual_artifacts != set(record['artifact_sha256']):
            raise ValueError('Generated artifact inventory changed. Rebuild first.')
        for name, digest in record['artifact_sha256'].items():
            if hashlib.sha256((output / name).read_bytes()).hexdigest() != digest:
                raise ValueError('Generated artifact changed: ' + name)
        checks = validate_site(output, modules)
    else:
        os.environ.setdefault('MPLBACKEND', 'Agg')
        sys.path.insert(0, str(ROOT / 'src'))
        import pdoc
        if pdoc.__version__ != '16.0.0':
            raise RuntimeError('Install requirements-docs.txt; this build expects pdoc 16.0.0.')
        favicon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#185a69"/><text x="32" y="43" fill="white" text-anchor="middle" font-size="34" font-family="sans-serif">TF</text></svg>'
        pdoc.render.configure(docformat='numpy', math=True, search=True, show_source=True,
            template_directory=ROOT / 'docs/pdoc-template',
            edit_url_map={'burnin_pid_fuzzy': REPOSITORY + '/blob/main/src/burnin_pid_fuzzy/'},
            favicon='data:image/svg+xml,' + quote(favicon),
            footer_text='Synthetic thermal experiments; see source traceability and limitations.')
        output.mkdir(parents=True, exist_ok=True)
        (output / 'assets').mkdir(exist_ok=True)
        for source in ASSETS:
            shutil.copyfile(source, output / 'assets' / source.name)
        # Only remove obsolete module pages within this generator's own namespace.
        expected = {output / (name.replace('.', '/') + '.html') for name in modules}
        for stale in (output / 'burnin_pid_fuzzy').glob('*.html'):
            if stale not in expected:
                stale.unlink()
        # The package's __all__ exports convenience objects, not submodules.
        # Supply the complete inventory explicitly so no module is omitted.
        pdoc.pdoc(*modules, output_directory=output)
        (output / '.nojekyll').write_bytes(b'')
        checks = validate_site(output, modules)
        artifacts = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'build.json'}
        record = {'generator': 'pdoc', 'pdoc_version': pdoc.__version__,
                  'render_dependencies': {name: version(name) for name in ('Jinja2', 'MarkupSafe', 'markdown2', 'Pygments')},
                  'image_source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in ASSETS},
                  'source_sha256_lf': source_hashes(), 'artifact_sha256': artifacts,
                  'coverage': modules, 'validation': checks}
        (output / 'build.json').write_bytes((json.dumps(record, indent=2) + '\n').encode('utf-8'))
    print(json.dumps(checks, indent=2))
    print('Documentation: ' + str(output / 'index.html'))


if __name__ == '__main__':
    main()
