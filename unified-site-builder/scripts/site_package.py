#!/usr/bin/env python3
"""Offline contract/package checks. Never executes website code or contacts services."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

MAX_BYTES = 600 * 1024 * 1024
MAX_ZIP = 120 * 1024 * 1024
MAX_FILES = 20000
SKIP_DIRS = {'.git', '.svn', '.hg', 'node_modules', '.wrangler', '.cache',
             '.codex', '.agents', '__pycache__', '__macosx', 'coverage'}
RUNTIME_DIRS = {'data', 'uploads', 'attachments', 'backups', 'logs', 'sessions'}
SECRET_NAMES = {'credentials.json', 'secrets.json', 'id_rsa', 'id_ed25519', '.npmrc'}
DOCS = ['README.zh-CN.md', 'CONFIGURATION.md', 'BACKUP-RESTORE.md',
        'HANDOFF.md', 'TEST-REPORT.md']


def path_text(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Expected a nonempty relative POSIX path')
    if value.startswith('/') or ':' in value or any(ord(c) < 32 for c in value):
        raise ValueError('Absolute/control-character paths are forbidden')
    parts = value.split('/')
    if any(p in ('', '.', '..') or p.endswith((' ', '.')) for p in parts):
        raise ValueError('Unsafe path components')
    if any(re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', p) for p in parts):
        raise ValueError('Reserved filename')
    return value


def excluded(rel):
    parts = [p.lower() for p in rel.parts]
    name = parts[-1]
    return (any(p in SKIP_DIRS for p in parts)
            or any(p in RUNTIME_DIRS for p in parts[:-1])
            or name.startswith('.env') or name in SECRET_NAMES
            or name.endswith(('.db', '.sqlite', '.sqlite3', '.db-wal', '.db-shm',
                              '.sqlite-wal', '.sqlite-shm', '.pem', '.key', '.p12',
                              '.pfx', '.log', '.pyc', '.zip', '.tar', '.gz', '.bak')))


def inspect(root):
    root = Path(root).resolve()
    errors, warnings, selected, omitted = [], [], [], []
    if not root.is_dir():
        return {'structurePassed': False, 'errors': ['Project directory not found'],
                'warnings': [], 'files': 0, 'bytes': 0, 'runtimeVerified': False}, []

    def problem(message):
        errors.append(message)

    def project_path(value):
        rel = path_text(value)
        target = root / rel
        if not target.resolve().is_relative_to(root):
            raise ValueError('Path escapes project')
        return target

    def read_json(name):
        try:
            path = project_path(name)
            if path.stat().st_size > 1024 * 1024:
                raise ValueError('JSON file exceeds 1 MiB')
            value = json.loads(path.read_text(encoding='utf-8-sig'))
            if not isinstance(value, dict):
                raise ValueError('JSON root must be an object')
            return value
        except (OSError, ValueError) as exc:
            problem(f'{name}: {type(exc).__name__}; missing or invalid JSON')
            return {}

    def require_file(name):
        try:
            target = project_path(name)
            if not target.is_file() or target.stat().st_size == 0:
                raise ValueError('Missing or empty file')
            if excluded(PurePosixPath(name)):
                raise ValueError('Required file is excluded from package')
        except (OSError, ValueError):
            problem(f'Missing, unsafe or excluded required file: {name}')

    contract = read_json('site.contract.json')
    if contract.get('contractVersion') != '1.0':
        problem('Unsupported or missing contractVersion (expected 1.0)')
    runtime = contract.get('runtime')
    if runtime not in ('node', 'cloudflare-workers'):
        problem('This checker supports node and cloudflare-workers only')
    languages = contract.get('languages')
    if (not isinstance(languages, list) or not languages
            or not all(isinstance(x, str) and re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*', x) for x in languages)):
        problem('languages must contain nonempty language codes')
    elif len(set(languages)) != len(languages) or contract.get('sourceLanguage') not in languages:
        problem('languages must be unique and include sourceLanguage')
    for key, expected in [('adminPath', '/admin/'), ('healthPath', '/healthz')]:
        if contract.get(key) != expected:
            problem(f'{key} must be {expected} for this contract')
    features = contract.get('features')
    if not isinstance(features, dict):
        problem('features must be an object')
    else:
        for key in ('cms', 'articles', 'inquiries'):
            if features.get(key) is not True:
                problem(f'Full-site contract requires features.{key}=true')
        if features.get('translation') != 'on-demand':
            problem('This contract uses on-demand translation')
    integrations = contract.get('integrations')
    if not isinstance(integrations, dict):
        problem('integrations must record actual service states')
    else:
        for key in ('email', 'whatsapp', 'translation'):
            state = integrations.get(key)
            if state not in ('unconfigured', 'configured', 'verified', 'disabled'):
                problem(f'integrations.{key}: unsupported status')
            elif state != 'verified':
                warnings.append(f'{key}: {state}; service behavior is not verified by this tool')

    entry = contract.get('entry')
    public = contract.get('publicDir')
    if isinstance(entry, str):
        require_file(entry)
    else:
        problem('entry must be a project-relative file')
    public_path = None
    try:
        public_path = project_path(public)
        if not public_path.is_dir():
            raise ValueError('Missing public directory')
        require_file(public + '/index.html')
    except (ValueError, TypeError):
        problem('publicDir must be a safe existing directory with index.html')
    for doc in DOCS:
        require_file('docs/' + doc)
    package = read_json('package.json')
    lock = read_json('package-lock.json')
    if package.get('type') != 'module':
        problem('package.json type must be module')
    scripts = package.get('scripts', {})
    if not isinstance(scripts, dict):
        scripts = {}
        problem('package.json scripts must be an object')
    locked_packages = lock.get('packages', {})
    locked = locked_packages.get('') if isinstance(locked_packages, dict) else None
    if not isinstance(locked, dict):
        problem('package-lock.json must contain packages root (npm lock v2/v3)')
    else:
        for key in ('dependencies', 'devDependencies', 'optionalDependencies'):
            if package.get(key, {}) != locked.get(key, {}):
                problem(f'Lockfile does not match {key}')

    if runtime == 'node':
        config = read_json('deploy.json')
        if entry != 'server.mjs' or scripts.get('start') != 'node server.mjs':
            problem('Node profile expects server.mjs and start=node server.mjs')
        expected = {'type': 'node', 'build': False, 'start': ['node', 'server.mjs'],
                    'containerPort': 3000, 'healthPath': '/healthz', 'spa': False,
                    'originEnv': ['SITE_ORIGIN', 'SITE_URL', 'PUBLIC_SITE_URL']}
        for key, value in expected.items():
            if type(config.get(key)) is not type(value) or config.get(key) != value:
                problem(f'deploy.json {key} does not match Node workbench profile')
        extra = set(config) - set(expected)
        if extra:
            problem('Unexpected deploy.json fields: ' + ', '.join(sorted(extra)))
    elif runtime == 'cloudflare-workers':
        config = read_json('wrangler.json')
        assets = config.get('assets')
        if config.get('main') != entry or not isinstance(assets, dict) or assets.get('directory') != public:
            problem('wrangler.json main/assets.directory must match contract')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(config.get('compatibility_date', ''))):
            problem('wrangler.json requires compatibility_date')
        warnings.append('Cloudflare bindings, permissions and workbench adapter are NOT verified')

    seen, size = set(), 0
    for current, dirs, files in os.walk(root, followlinks=False):
        for name in list(dirs):
            path = Path(current) / name
            rel = path.relative_to(root)
            if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                problem('Symlink/junction directory: ' + rel.as_posix())
                dirs.remove(name)
            elif name.lower() in SKIP_DIRS or name.lower() in RUNTIME_DIRS:
                omitted.append(rel.as_posix() + '/')
                if public_path is not None and path.is_relative_to(public_path) and name.lower() in RUNTIME_DIRS:
                    problem('Runtime data directory inside public directory: ' + rel.as_posix())
                dirs.remove(name)
        for name in files:
            path = Path(current) / name
            rel = path.relative_to(root)
            public_file = public_path is not None and path.is_relative_to(public_path)
            if path.is_symlink():
                problem('Symlink file: ' + rel.as_posix())
                continue
            if excluded(rel):
                omitted.append(rel.as_posix())
                if public_file:
                    problem('Excluded/runtime/secret file inside public directory: ' + rel.as_posix())
                continue
            try:
                name_safe = path_text(rel.as_posix())
                folded = name_safe.casefold()
                if folded in seen:
                    raise ValueError('Case-insensitive filename collision')
                seen.add(folded)
                size += path.stat().st_size
                if public_file and name.lower() in ('package.json', 'package-lock.json', 'wrangler.json', 'deploy.json', '_worker.js'):
                    raise ValueError('Server configuration or Worker code in public directory')
                selected.append(path)
            except (OSError, ValueError):
                problem('Unsafe/conflicting public or package file: ' + rel.as_posix())
    if size > MAX_BYTES or len(selected) > MAX_FILES:
        problem('Package exceeds 600 MiB expanded or 20,000 files')
    if omitted:
        warnings.append(f'{len(omitted)} runtime/dependency/private/archive paths excluded from package')
    warnings.append('Declarations and file structure only; runtime, secrets in code, security and external services require separate tests')
    return {'structurePassed': not errors, 'runtimeVerified': False, 'runtime': runtime,
            'files': len(selected), 'bytes': size, 'excludedPaths': omitted,
            'errors': errors, 'warnings': warnings}, sorted(selected)


def pack(root, target, files):
    root, target = Path(root).resolve(), Path(target).resolve()
    if target.is_relative_to(root):
        raise ValueError('Output must be outside the project')
    if target.suffix.lower() != '.zip':
        raise ValueError('Output must have .zip suffix')
    # Exclusive creation prevents silent overwrite, including a racing writer.
    with target.open('xb') as output:
        try:
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
                for path in files:
                    if path.is_symlink() or not path.resolve().is_relative_to(root):
                        raise ValueError('Source changed to unsafe path during packaging')
                    archive.write(path, path.relative_to(root).as_posix())
            if output.tell() > MAX_ZIP:
                raise ValueError('Compressed package exceeds 120 MiB')
        except BaseException:
            output.close()
            target.unlink(missing_ok=True)
            raise
    digest = hashlib.sha256()
    with target.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'zip': str(target), 'bytes': target.stat().st_size, 'sha256': digest.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'pack'])
    parser.add_argument('project', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report, files = inspect(args.project)
    if report['structurePassed'] and args.action == 'pack':
        try:
            if args.output is None:
                raise ValueError('--output is required')
            report['package'] = pack(args.project, args.output, files)
        except (OSError, ValueError) as exc:
            report['errors'].append(str(exc))
            report['structurePassed'] = False
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report['structurePassed'] else 1


if __name__ == '__main__':
    sys.exit(main())
