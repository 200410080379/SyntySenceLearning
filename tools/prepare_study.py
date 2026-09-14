"""Copy a portable study into an existing Unreal project, preserving local edits."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
GENERATED_DATA = {
    'CandidateGeometry.json', 'SourceGroundGeometry.json', 'SourceGroundPlacements.json',
    'SourceContext.json', 'SourceVisibility.json', 'GeometryValidation.json',
    'Validation.json', 'BuildValidation.json', 'MaterialOverride.json', 'SourceIntegrity.json',
}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_study(identifier, pack_id=None):
    matches = []
    for entry in read_json(ROOT / 'catalog.json')['packs']:
        if pack_id and entry['id'] != pack_id:
            continue
        pack_path = ROOT / entry['manifest']
        pack = read_json(pack_path)
        for study in pack['studies']:
            if identifier in (study['id'], study.get('alias')):
                manifest_path = (pack_path.parent / study['manifest']).resolve()
                if not manifest_path.is_relative_to(ROOT):
                    raise ValueError('Study manifest escapes the repository')
                matches.append((pack, read_json(manifest_path), manifest_path.parent))
    if len(matches) != 1:
        raise ValueError('Select one study using --study and, if necessary, --pack; found %d matches' % len(matches))
    return matches[0]


def prepare(project_file, identifier, pack_id=None, dry_run=False):
    project_file = project_file.resolve()
    if project_file.suffix.lower() != '.uproject' or not project_file.is_file():
        raise ValueError('--project must name an existing .uproject file')
    project_root = project_file.parent
    project = read_json(project_file)
    pack, study, source = find_study(identifier, pack_id)
    for slug in (pack['id'], study['id']):
        if not slug or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in slug):
            raise ValueError('Pack and study ids must use lowercase letters, numbers and hyphens')
    target = (project_root / 'Learning/SyntySenceLearning' / pack['id'] / study['id']).resolve()
    if not target.is_relative_to(project_root):
        raise ValueError('Resolved target escapes the selected Unreal project')
    def require_directory_chain(directory):
        current = directory
        while current != project_root:
            if current.exists() and not current.is_dir():
                raise ValueError('A target directory is occupied by a file: %s' % current)
            current = current.parent
    require_directory_chain(target)
    marker_path = target / '.prepared-study.json'
    if marker_path.is_symlink() or not marker_path.resolve().is_relative_to(target):
        raise ValueError('Preparation marker must be a regular file inside the study')
    if marker_path.exists() and not marker_path.is_file():
        raise ValueError('Preparation marker is not a file')
    previous = read_json(marker_path) if marker_path.exists() else {}
    if previous and (previous.get('pack') != pack['id'] or previous.get('study') != study['id']):
        raise ValueError('Target is owned by a different study')
    files = [source / 'study.json', source / 'README.md']
    files += sorted((source / 'Scripts').glob('*.py'))
    files += sorted(p for p in (source / 'Data').glob('*.json') if p.name not in GENERATED_DATA)
    files += sorted((source / 'Screenshots').glob('*.png'))
    operations = []
    hashes = {}
    for src in files:
        if not src.is_file() or not src.resolve().is_relative_to(source):
            raise ValueError('Missing or external study file: %s' % src)
        relative = src.relative_to(source).as_posix()
        dst = (target / relative).resolve()
        if not dst.is_relative_to(target):
            raise ValueError('Target file resolves outside the study: %s' % dst)
        require_directory_chain(dst.parent)
        new_hash = digest(src)
        hashes[relative] = new_hash
        if dst.exists():
            if not dst.is_file():
                raise ValueError('Target path is not a file: %s' % dst)
            current = digest(dst)
            if current == new_hash:
                continue
            if previous.get('files', {}).get(relative) != current:
                raise ValueError('Preserving locally edited or unmanaged file: %s' % dst)
        operations.append((src, dst))
    if not dry_run:
        # Preflight above completes for every file before the first write.
        for src, dst in operations:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        target.mkdir(parents=True, exist_ok=True)
        marker = {'schema_version': 1, 'repository': 'SyntySenceLearning',
                  'pack': pack['id'], 'study': study['id'], 'files': hashes}
        marker_path.write_text(json.dumps(marker, indent=2) + '\n', encoding='utf-8')
    enabled = {p['Name'] for p in project.get('Plugins', []) if p.get('Enabled')}
    explicit_disabled = {p['Name'] for p in project.get('Plugins', []) if p.get('Enabled') is False}
    relative_root = target.relative_to(project_root)
    return {'dry_run': dry_run, 'project': str(project_file), 'target': str(target),
            'copied_or_updated_files': len(operations), 'managed_files': len(hashes),
            'map': study['map'],
            'mcp_file_arguments': {role: (relative_root / path).as_posix()
                                   for role, path in study['scripts'].items()},
            'required_editor_plugins': pack['required_editor_plugins'],
            'plugins_not_explicitly_enabled': [p for p in pack['required_editor_plugins'] if p not in enabled],
            'plugins_explicitly_disabled': [p for p in pack['required_editor_plugins'] if p in explicit_disabled],
            'note': 'Project config and source assets were not changed. Enable required editor plugins before running UE scripts; save the current level before builders switch worlds.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--study', required=True)
    parser.add_argument('--pack')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        result = prepare(args.project, args.study, args.pack, args.dry_run)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, 'Cannot prepare study: %s\n' % exc)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
