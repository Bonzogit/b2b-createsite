#!/usr/bin/env python3
"""Emit SHA256SUMS.txt and a manifest table for a delivery directory.

Usage:
    python delivery_manifest.py <delivery-dir> [--glob '*.zip']

Behaviour:
  * discovers every archive in the delivery directory
  * refuses to proceed if any archive contains a Windows reserved device name
    anywhere in its path (such an entry is silently dropped by Expand-Archive)
  * writes <delivery-dir>/SHA256SUMS.txt  ("<sha256>  <filename>")
  * prints a markdown table to stdout

It never mutates the archives, so it is safe to re-run after every repack.
"""
import argparse
import hashlib
import re
import sys
import zipfile
from pathlib import Path

RESERVED = re.compile(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$')


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def reserved_entries(path):
    with zipfile.ZipFile(path) as archive:
        return [n for n in archive.namelist()
                if any(RESERVED.fullmatch(part) for part in n.split('/'))]


def entry_count(path):
    with zipfile.ZipFile(path) as archive:
        return len([n for n in archive.namelist() if not n.endswith('/')])


def human(size):
    return '%.1f MB' % (size / 1048576) if size > 1048576 else '%.0f KB' % (size / 1024)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('delivery', type=Path)
    parser.add_argument('--glob', default='*.zip')
    args = parser.parse_args(argv)
    folder = args.delivery.resolve()
    if not folder.is_dir():
        raise SystemExit('not a directory: %s' % folder)

    archives = sorted(folder.glob(args.glob))
    if not archives:
        raise SystemExit('no archives matched in %s' % folder)

    rows, bad = [], []
    for path in archives:
        offenders = reserved_entries(path)
        if offenders:
            bad.append((path.name, offenders))
            continue
        rows.append({'file': path.name, 'bytes': path.stat().st_size,
                     'entries': entry_count(path), 'sha256': sha256(path)})

    if bad:
        for name, offenders in bad:
            print('RESERVED-NAME VIOLATION in %s:' % name, file=sys.stderr)
            for item in offenders[:10]:
                print('   ', item, file=sys.stderr)
        raise SystemExit('refusing to emit manifest: %d archive(s) would drop files on Windows' % len(bad))

    (folder / 'SHA256SUMS.txt').write_text(
        ''.join('%s  %s\n' % (r['sha256'], r['file']) for r in rows),
        encoding='ascii', newline='\n')

    print('| # | 文件 | 大小 | 条目 | SHA-256 |')
    print('|---|---|---|---|---|')
    for i, r in enumerate(rows, 1):
        print('| %d | `%s` | %s | %d | `%s` |' % (i, r['file'], human(r['bytes']), r['entries'], r['sha256']))
    print()
    print('SHA256SUMS.txt written with %d entries; verify with: sha256sum -c SHA256SUMS.txt' % len(rows))
    return 0


if __name__ == '__main__':
    sys.exit(main())
