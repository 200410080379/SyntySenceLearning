"""Check the files selected for Git, study links, and portable layouts."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_NAMES = {'CandidateGeometry.json', 'SourceGroundGeometry.json',
                 'SourceGroundPlacements.json', 'SourceContext.json', 'SourceVisibility.json',
                 'RoadTexture.png', 'StartupRecovery.log'}
PRIVATE_SUFFIXES = {'.uasset', '.umap', '.ubulk', '.uexp', '.pak', '.utoc', '.ucas', '.dmp', '.log', '.pyc'}


def main():
    errors = []
    output = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT)
    files = sorted(set(p.decode('utf-8') for p in output.split(b'\0') if p))
    for relative in files:
        p = ROOT / relative
        if p.name.lower() in {n.lower() for n in PRIVATE_NAMES} or p.stem.lower() == 'roadtexture' or p.suffix.lower() in PRIVATE_SUFFIXES:
            errors.append('Local-only file selected for Git: ' + relative)
        if p.suffix.lower() not in {'.py', '.md', '.json', '.gitignore', '.gitattributes'}:
            continue
        text = p.read_text(encoding='utf-8-sig')
        if 'F:/UnrealProjects/JSQS' in text or 'F:\\UnrealProjects\\JSQS' in text or 'C:/Users/Administrator' in text:
            # This checker necessarily contains the forbidden literals itself.
            if p.resolve() != Path(__file__).resolve():
                errors.append('Machine-specific path: ' + relative)
        if p.suffix == '.py':
            try:
                ast.parse(text, filename=relative)
            except SyntaxError as exc:
                errors.append(str(exc))
        if p.suffix == '.json':
            try:
                value = json.loads(text)
                if isinstance(value, dict) and any(isinstance(v, dict) and 'sections' in v and 'min' in v for v in value.values()):
                    errors.append('Possible full source geometry export: ' + relative)
            except ValueError as exc:
                errors.append(relative + ': ' + str(exc))
        if p.suffix == '.md':
            prose = re.sub(r'```[\s\S]*?```', '', text)
            prose = re.sub(r'`[^`]*`', '', prose)
            for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', prose):
                target = target.split('#')[0].strip('<>')
                if not target or '://' in target or target.startswith('mailto:'):
                    continue
                if not (p.parent / target).exists():
                    errors.append('Missing Markdown target: %s -> %s' % (relative, target))
    catalog = json.loads((ROOT / 'catalog.json').read_text())
    study_count = 0
    for entry in catalog['packs']:
        pack_path = ROOT / entry['manifest']
        pack = json.loads(pack_path.read_text())
        assert entry['id'] == pack['id']
        for entry in pack['studies']:
            path = pack_path.parent / entry['manifest']
            study = json.loads(path.read_text(encoding='utf-8'))
            study_count += 1
            references = [study['readme'], study['layout'], study['historical_evidence'], *study['scripts'].values()]
            if study.get('reproduction_evidence'):
                references.append(study['reproduction_evidence'])
            for value in references:
                if not (path.parent / value).is_file():
                    errors.append('Missing registered file: ' + str(path.parent / value))
            layout = json.loads((path.parent / study['layout']).read_text())
            count = len(layout if isinstance(layout, list) else layout['tiles'])
            if count != study['expected_mesh_instances']:
                errors.append('Layout instance count differs from manifest: ' + str(path))
            if isinstance(layout, dict) and layout['map'] != study['map']:
                errors.append('Map namespace differs from manifest: ' + str(path))
            if study.get('reproduction_evidence'):
                evidence = json.loads((path.parent / study['reproduction_evidence']).read_text())
                actual = hashlib.sha256((path.parent / study['layout']).read_bytes()).hexdigest()
                check = evidence['instance_validation']
                if check.get('manifest_sha256', check.get('layout_sha256')) != actual:
                    errors.append('Reproduction evidence references a different layout: ' + str(path))
    print(json.dumps({'files_checked': len(files), 'studies': study_count, 'errors': errors}, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
