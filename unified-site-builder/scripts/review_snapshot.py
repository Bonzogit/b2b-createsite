#!/usr/bin/env python3
"""Snapshot rendered pages for Impeccable detect, with the stylesheet inlined.

Why: the impeccable detector cannot fetch linked stylesheets from a file:// copy,
so color/contrast/custom-property rules silently degrade and report false
positives (e.g. flat-type-hierarchy against an unresolved clamp()). This script
fetches the pages from a RUNNING site, inlines /assets/theme.css into a <style>
block, and writes self-contained HTML files that detect can analyse faithfully.

Usage:
  python review_snapshot.py --base http://127.0.0.1:4310 \
      --project projects/sofa/app \
      --page home=/ --page listing=/products/ --page detail=/products/lumen-three-seat-sofa/

Writes <project>/docs/review/inlined/<name>.html and a manifest JSON next to it.
Exit codes: 0 ok, 2 nothing fetched, 3 a page or the stylesheet could not be loaded.
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # ignore env proxies: the target is a local dev server


def fetch(base, path, timeout=30):
    url = base.rstrip('/') + path
    try:
        with _OPENER.open(url, timeout=timeout) as resp:
            if resp.status != 200:
                raise SystemExit('GET %s -> HTTP %s' % (url, resp.status))
            return resp.read().decode('utf-8', 'replace')
    except urllib.error.URLError as err:
        raise SystemExit('GET %s failed: %r (if this is a proxy error, note the script bypasses env proxies by design)' % (url, err))


def inline_css(html, base):
    """Replace every local stylesheet link with an inline <style> block."""
    def repl(match):
        href = match.group(1)
        if not href.startswith('/assets/'):
            return match.group(0)
        css = fetch(base, href)
        return '<style>\n/* inlined from %s for offline design review */\n%s\n</style>' % (href, css)

    return re.sub(r'<link\s+rel="stylesheet"\s+href="([^"]+)">', repl, html)


def main():
    ap = argparse.ArgumentParser(description='Snapshot rendered pages with inlined CSS for design review')
    ap.add_argument('--base', required=True, help='running site origin, e.g. http://127.0.0.1:4310')
    ap.add_argument('--project', required=True, help='project root (app root for created sites)')
    ap.add_argument('--page', action='append', required=True, metavar='NAME=PATH',
                    help='repeatable: home=/ listing=/products/ detail=/products/<slug>/')
    ap.add_argument('--out', default=None, help='manifest JSON path')
    args = ap.parse_args()

    root = Path(args.project).resolve()
    outdir = root / 'docs' / 'review' / 'inlined'
    outdir.mkdir(parents=True, exist_ok=True)

    written = []
    for spec in args.page:
        name, _, path = spec.partition('=')
        if not name or not path:
            raise SystemExit('bad --page spec %r, expected NAME=PATH' % spec)
        html = fetch(args.base, path)
        inlined = inline_css(html, args.base)
        if '<style>' not in inlined:
            raise SystemExit('%s: no stylesheet was inlined; check the <link rel="stylesheet"> markup' % path)
        target = outdir / ('%s.html' % name)
        target.write_text(inlined, encoding='utf-8', newline='\n')
        written.append({'name': name, 'path': path, 'file': 'docs/review/inlined/%s.html' % name, 'bytes': target.stat().st_size})

    if not written:
        print(json.dumps({'ok': False, 'reason': 'no_pages'}))
        return 2

    manifest = Path(args.out).resolve() if args.out else (outdir / 'manifest.json')
    manifest.write_text(json.dumps({'ok': True, 'base': args.base, 'pages': written}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'ok': True, 'pages': [w['name'] for w in written], 'manifest': str(manifest)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
