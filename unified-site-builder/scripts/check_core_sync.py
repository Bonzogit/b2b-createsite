#!/usr/bin/env python3
"""Report drift between a project's shared runtime and the Skill's runtime.

The shared core (entry points, business app, render layer, translation modules and
the Chinese admin UI) is owned by the Skill and must stay byte-identical in every
project; only lib/theme.mjs and the project content directories are project-owned.
Run this before packaging so a project cannot ship a stale or hand-edited core and
still be described as "reusing the same common base".

Usage:
    python check_core_sync.py <project-dir> [--json]

Exit codes: 0 = in sync, 1 = drift or missing core file, 2 = skill runtime not found.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
RUNTIME = SKILL / 'assets' / 'runtime'
TRANSLATION = SKILL / 'assets' / 'translation'
# (source relative to assets/, destination relative to the project). Files and
# directories owned by the Skill. Everything else in a project is either project
# content or the project theme, and is expected to differ.
CORE_FILES = [
    ('runtime/public/assets/inquiry-adapter.js', 'public/assets/inquiry-adapter.js'),
    ('runtime/server.mjs', 'server.mjs'),
    ('runtime/worker.mjs', 'worker.mjs'),
    ('runtime/lib/app.mjs', 'lib/app.mjs'),
    ('runtime/lib/modules.mjs', 'lib/modules.mjs'),
    ('runtime/lib/public-ui.mjs', 'lib/public-ui.mjs'),
    ('runtime/lib/translation-jobs.mjs', 'lib/translation-jobs.mjs'),
    ('runtime/public/assets/admin.js', 'public/assets/admin.js'),
    ('runtime/public/assets/site.js', 'public/assets/site.js'),
    ('runtime/lib/render.mjs', 'lib/render.mjs'),
    ('translation/engine.mjs', 'lib/translation/engine.mjs'),
    ('translation/resolver.mjs', 'lib/translation/resolver.mjs'),
    ('translation/quality.mjs', 'lib/translation/quality.mjs'),
    ('translation/seed.mjs', 'lib/translation/seed.mjs'),
]
CORE_DIRS = [('runtime/public/admin', 'public/admin')]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def core_paths():
    """Return [(source_path, project_relative_path)] for every shared core file."""
    found = []
    assets = SKILL / 'assets'
    for source_rel, project_rel in CORE_FILES:
        source = assets / source_rel
        if source.is_file():
            found.append((source, project_rel))
    for source_rel, project_rel in CORE_DIRS:
        source = assets / source_rel
        if source.is_dir():
            for item in sorted(source.rglob('*')):
                if item.is_file():
                    found.append((item, (Path(project_rel) / item.relative_to(source)).as_posix()))
    return sorted(found, key=lambda pair: pair[1])


def skill_version():
    text = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('version:'):
            return stripped.split(':', 1)[1].strip().strip('"').strip("'")
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--json', action='store_true', help='machine readable report')
    parser.add_argument('--fix', action='store_true',
                        help='copy the Skill copy over drifted/missing core files; never touches content or the theme')
    args = parser.parse_args()

    if not RUNTIME.is_dir():
        print('skill runtime not found: ' + str(RUNTIME))
        return 2
    project = args.project.resolve()
    if not project.is_dir():
        print('project directory not found: ' + str(project))
        return 1

    contract=json.loads((project/'site.contract.json').read_text(encoding='utf-8'))
    excluded='worker.mjs' if contract.get('runtime')=='node' else 'server.mjs' if contract.get('runtime')=='cloudflare-workers' else None
    pairs = [(src,rel) for src,rel in core_paths() if rel!=excluded]
    repaired = []
    if args.fix:
        for source, rel in pairs:
            target = project / rel
            if not target.is_file() or digest(source) != digest(target):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
                repaired.append(rel)

    in_sync, drifted, missing = [], [], []
    for source, rel in pairs:
        target = project / rel
        if not target.is_file():
            missing.append(rel)
        elif digest(source) != digest(target):
            drifted.append({'file': rel, 'skill': digest(source)[:12], 'project': digest(target)[:12]})
        else:
            in_sync.append(rel)

    theme = project / 'lib' / 'theme.mjs'
    report = {
        'project': str(project),
        'skillVersion': skill_version(),
        'coreFiles': len(pairs),
        'inSync': len(in_sync),
        'drifted': drifted,
        'missing': missing,
        'repaired': repaired,
        'projectOwned': {
            'theme': 'present (project-owned, expected to differ)' if theme.is_file() else 'absent (default renderer in use)',
        },
        'passed': not drifted and not missing,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print('project   : ' + report['project'])
        print('skill     : ' + str(report['skillVersion']))
        print('core files: %d, in sync %d, drifted %d, missing %d'
              % (report['coreFiles'], report['inSync'], len(drifted), len(missing)))
        for rel in repaired:
            print('  REPAIRED ' + rel)
        for row in drifted:
            print('  DRIFT %s  skill=%s project=%s' % (row['file'], row['skill'], row['project']))
        for rel in missing:
            print('  MISSING ' + rel)
        print('theme     : ' + report['projectOwned']['theme'])
        print('result    : ' + ('pass' if report['passed'] else 'fail'))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
