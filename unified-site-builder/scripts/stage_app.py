#!/usr/bin/env python3
"""Mirror a project's app tree into a staging directory without wiping it first.

Why this exists
---------------
Both projects used to restage `dist/<runtime>/` with `shutil.rmtree` on every build.
On Windows this machine runs a workspace bulk-delete guard: a single call that removes
~100 entries returns `SAFE_DELETE_BULK_CONFIRM_REQUIRED` and exits non-zero, because a
non-interactive build has nobody to answer the confirmation prompt. The build then dies
half-way and leaves a partially erased staging directory.

That failure mode is not cosmetic. It is how round 3 produced a site archive whose
`workflow.json` still recorded `skillVersion: 1.7.1`: the staging step aborted, the
packaging step was re-run over whatever survived, and the mismatch was invisible from
the archive's name.

An incremental mirror only has to delete the files that actually disappeared between
two builds — normally zero — so the guard never fires, unchanged files keep their
timestamps, and a crash can no longer leave a half-erased directory behind.

Rules encoded here (they are the delivery contract, not a convenience):

* `exclude` names are skipped at the top level only — that is where `data/`, `uploads/`,
  `tools/`, `dist/` and `node_modules/` live, and none of them belong in a package.
* `ignore` patterns are skipped at every depth. Windows reserved device names
  (`aux`, `con`, `prn`, `nul`) must never appear in an archive entry; the style-guide
  screenshots that start with `_` are review artefacts, not deliverables.
* Anything present in the target but absent from the source is removed, so a renamed
  or deleted source file cannot survive as a stale entry in the package.

Usage as a library:

    report = mirror(source_dir, target_dir, exclude=(...), ignore=(...))

Usage from the shell (for checking what a mirror would do):

    python stage_app.py <source> <target> [--exclude a,b] [--ignore '_*'] [--dry-run]
"""
import argparse
import fnmatch
import json
import shutil
import sys
from pathlib import Path


def wanted(source, exclude=(), ignore=()):
    """Return {relative posix path: absolute source path} for everything shippable."""
    found = {}
    for entry in sorted(source.iterdir()):
        if entry.name in exclude:
            continue
        if any(fnmatch.fnmatch(entry.name, pattern) for pattern in ignore):
            continue
        if entry.is_dir():
            found.update(_walk_dir(entry, entry.name, ignore))
        else:
            found[entry.name] = entry
    return found


def _walk_dir(directory, prefix, ignore):
    found = {}
    for entry in sorted(directory.iterdir()):
        if any(fnmatch.fnmatch(entry.name, pattern) for pattern in ignore):
            continue
        relative = '%s/%s' % (prefix, entry.name)
        if entry.is_dir():
            found.update(_walk_dir(entry, relative, ignore))
        else:
            found[relative] = entry
    return found


def mirror(source, target, exclude=(), ignore=(), dry_run=False):
    """Copy `source` over `target`, then drop anything in `target` that is not shippable."""
    source, target = Path(source).resolve(), Path(target).resolve()
    if not source.is_dir():
        raise SystemExit('source directory not found: %s' % source)
    if source == target or source in target.parents or target in source.parents:
        raise ValueError('source and staging target must be disjoint dedicated directories')
    if any(p.is_symlink() for p in source.rglob('*')) or (target.exists() and any(p.is_symlink() for p in target.rglob('*'))):
        raise ValueError('symbolic links are not permitted in staging trees')
    keep = wanted(source, exclude, ignore)
    if not keep:
        raise SystemExit('refusing to mirror: %s produced no shippable files' % source)

    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)

    copied, unchanged = 0, 0
    for relative, path in sorted(keep.items()):
        destination = target / relative
        if destination.is_file() and destination.stat().st_size == path.stat().st_size \
                and destination.read_bytes() == path.read_bytes():
            unchanged += 1
            continue
        copied += 1
        if dry_run:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)

    removed = 0
    if target.is_dir() and not dry_run:
        for path in sorted((p for p in target.rglob('*') if p.is_file()), reverse=True):
            if path.relative_to(target).as_posix() not in keep:
                path.unlink()
                removed += 1
        # Prune directories that the cleanup above emptied, deepest first.
        for path in sorted((p for p in target.rglob('*') if p.is_dir()), reverse=True):
            try:
                path.rmdir()
            except OSError:
                pass
    return {'source': str(source), 'target': str(target), 'shipped': len(keep),
            'copied': copied, 'unchanged': unchanged, 'removed': removed,
            'bytes': sum(path.stat().st_size for path in keep.values()), 'dryRun': dry_run}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    parser.add_argument('--exclude', default='', help='comma separated, top level only')
    parser.add_argument('--ignore', default='', help='comma separated glob, every depth')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    split = lambda text: tuple(part for part in (item.strip() for item in text.split(',')) if part)
    report = mirror(args.source, args.target, split(args.exclude), split(args.ignore),
                    args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
