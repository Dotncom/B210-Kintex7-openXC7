#!/usr/bin/env python3
"""Materialize editable projects and overlay their source changes on a fresh build tree."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile


MARKER = '.obrii-b210.json'
PART = 'xc7k325tffg676-2'
VARIANTS = ('b210-dual-fabric', 'b210-siso-strobe')
BASE_SUFFIXES = ('.v', '.vh', '.xdc', '.sdc')
USER_SUFFIXES = ('.v', '.sv', '.vh', '.svh')


def checked_file(root, name):
    parts = PurePosixPath(name).parts
    if not parts or '/'.join(parts) != name or any(
            part in ('.', '..') or re.fullmatch(r'[A-Za-z0-9_.-]+', part) is None for part in parts):
        raise ValueError(f'Invalid project source path: {name}')
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f'Project source uses a symbolic link: {name}')
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Missing or external project source: {name}')
    return path


def source_hash(path):
    # Qt's source editor may preserve CRLF. Build and compare in LF.
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def inventory(stage):
    return {path.relative_to(stage).as_posix(): source_hash(path)
            for path in sorted(stage.rglob('*'))
            if path.is_file() and path.suffix in BASE_SUFFIXES}


def load_project(project):
    marker = checked_file(project, MARKER)
    manifest = json.loads(marker.read_text(encoding='utf-8'))
    if not isinstance(manifest, dict) or manifest.get('schema') != 1 or \
            manifest.get('part') != PART or manifest.get('variant') not in VARIANTS or \
            manifest.get('sourceRoot') != 'src':
        raise ValueError('Unsupported Obrii B210 project format')
    root = project / 'src'
    if root.is_symlink() or not root.is_dir() or not root.resolve().is_relative_to(project.resolve()):
        raise ValueError('Missing or external project source folder')
    baseline = manifest.get('baselineSha256')
    if not isinstance(baseline, dict) or not baseline or sorted(baseline) != manifest.get('sources') or any(
            not isinstance(digest, str) or re.fullmatch(r'[0-9a-f]{64}', digest) is None
            for digest in baseline.values()):
        raise ValueError('Invalid B210 baseline manifest')
    return manifest, root


def project_changes(manifest, root):
    baseline = manifest['baselineSha256']
    changed = {name: source_hash(checked_file(root, name)) for name in baseline}
    changed = {name: digest for name, digest in changed.items() if digest != baseline[name]}
    added = {}
    user_root = root / 'user'
    if user_root.is_symlink():
        raise ValueError('Project user folder uses a symbolic link')
    for path in sorted(user_root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Project user source uses a symbolic link: {path.name}')
        if path.is_file() and path.suffix in USER_SUFFIXES:
            name = path.relative_to(root).as_posix()
            added[name] = source_hash(checked_file(root, name))
    return changed, added


def apply_project(project, stage, variant):
    manifest, root = load_project(project)
    if manifest['variant'] != variant:
        raise ValueError(f"Project uses {manifest['variant']}; requested {variant}")
    if manifest['baselineSha256'] != inventory(stage):
        raise ValueError('Project baseline differs from the staged recipe; recreate it with the matching recipe')
    changed, added = project_changes(manifest, root)
    for name, digest in (changed | added).items():
        destination = stage / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = checked_file(root, name).read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f'Project changed during staging: {name}')
        destination.write_bytes(data)
    provenance = dict(schema=1, part=PART, variant=variant,
                      baselineSha256=manifest['baselineSha256'], changedSha256=changed, addedSha256=added)
    (stage.parent / 'project-sources.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(f'Applied {len(changed)} edited and {len(added)} new B210 source files')
    return [name for name in added if PurePosixPath(name).suffix in ('.v', '.sv')]


def create_project(vendor, variant, project):
    # Import here so prepare.py can use the overlay functions above.
    from prepare import stage_sources

    if project.exists() or project.is_symlink():
        raise ValueError(f'The project folder already exists: {project}')
    with tempfile.TemporaryDirectory(prefix='obrii-b210-') as temp:
        stage = Path(temp) / 'src'
        stage_sources(vendor, variant, stage)
        baseline = inventory(stage)
        project.mkdir()
        root = project / 'src'
        for name in baseline:
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(stage / name, destination)
        (root / 'user').mkdir()
        manifest = dict(schema=1, variant=variant, part=PART, sourceRoot='src',
                        sources=sorted(baseline), baselineSha256=baseline)
        (project / MARKER).write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return project / MARKER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('create')
    create.add_argument('vendor', type=Path)
    create.add_argument('variant', choices=VARIANTS)
    create.add_argument('project', type=Path)
    inspect = commands.add_parser('inspect')
    inspect.add_argument('project', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'create':
            print(create_project(args.vendor, args.variant, args.project).resolve())
        else:
            manifest, root = load_project(args.project)
            changed, added = project_changes(manifest, root)
            print(json.dumps(dict(manifest, changedSources=sorted(changed), addedSources=sorted(added)), indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
