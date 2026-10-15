#!/usr/bin/env python3
"""Capture a real reference page at desktop and mobile viewports.

Stage 2 (reference-selection) uses this so that "we looked at a reference" is a
recorded fact instead of a claim. For every <id> it writes:

  docs/references/<id>-desktop.png   full-page screenshot at 1440x900
  docs/references/<id>-mobile.png    screenshot at 390x844
  docs/references/<id>.json          structural metrics for both viewports

Nothing from the reference is copied into the project: only layout, module order,
image composition and information density are read, and only method-level aspects
are reused (see docs/design-record.json > sectionReferences).

Requires the agent-browser CLI. Resolve order: --browser, AGENT_BROWSER env,
managed node workspace, then PATH.
Exit codes: 0 ok, 2 browser/record missing, 3 page load failed.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXTRACT = r"""(() => {
  const q = s => Array.from(document.querySelectorAll(s));
  const imgs = Array.from(document.images).filter(i => i.clientWidth > 4);
  const rect = el => { const r = el.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; };
  const firstCard = q('main a[href], [class*="product"] a[href], [class*="card"] a[href]')[0];
  return {
    url: location.href,
    title: document.title,
    scrollHeight: document.documentElement.scrollHeight,
    headingCounts: ['h1','h2','h3'].reduce((a,t)=>{a[t]=q(t).length;return a;},{}),
    sectionCount: q('section').length,
    linkCount: q('a').length,
    navLinkCount: q('nav a, header nav a').length,
    imageTotal: document.images.length,
    imageVisible: imgs.length,
    imageAspects: imgs.slice(0, 8).map(i => Math.round(i.clientWidth / i.clientHeight * 100) / 100),
    textChars: (document.body.innerText || '').replace(/\s+/g, ' ').trim().length,
    firstNameCardRect: firstCard ? rect(firstCard) : null,
    lazyHints: q('img[loading="lazy"]').length,
    hasStickyHeader: !!document.querySelector('header[class*="sticky"], .site-header[class*="sticky"]') ||
      (() => { const h = document.querySelector('header'); if (!h) return false; return getComputedStyle(h).position === 'fixed' || getComputedStyle(h).position === 'sticky'; })()
  };
})()"""


def resolve_browser(explicit=None):
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    envv = os.environ.get('AGENT_BROWSER')
    if envv:
        candidates.append(Path(envv))
    # The .bin/ shim is a POSIX shell script on this install, so prefer the
    # platform binary shipped inside the package.
    for base in candidates_from_home():
        for exe in ('agent-browser-win32-x64.exe', 'agent-browser.exe', 'agent-browser'):
            candidates.append(base / 'bin' / exe)
    found = shutil.which('agent-browser')
    if found:
        candidates.append(Path(found))
    for c in candidates:
        if c.exists() and os.access(str(c), os.X_OK):
            return str(c)
    return None


def candidates_from_home():
    roots = [
        Path.home() / '.workbuddy' / 'binaries' / 'node' / 'workspace' / 'node_modules' / 'agent-browser',
        Path.home() / '.workbuddy' / 'binaries' / 'node' / 'workspace' / 'node_modules' / '.bin',
    ]
    return [r for r in roots if r.exists()]


def run(browser, *args, timeout=90):
    proc = subprocess.run([browser] + list(args), capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise SystemExit('browser command failed (%s): %s' % (' '.join(args[:3]), (proc.stderr or proc.stdout).strip()[:300]))
    return proc.stdout


def extract_json(browser, timeout=90):
    out = run(browser, 'eval', EXTRACT, timeout=timeout)
    start, end = out.find('{'), out.rfind('}')
    if start < 0 or end < 0:
        raise SystemExit('could not parse eval output: %s' % out[:200])
    return json.loads(out[start:end + 1])


def main():
    ap = argparse.ArgumentParser(description='Capture a reference page at desktop and mobile viewports')
    ap.add_argument('--url', required=True)
    ap.add_argument('--project', required=True, help='project root; references go to <project>/docs/references')
    ap.add_argument('--id', required=True, help='stable reference id, e.g. ref-contract-seating-listing')
    ap.add_argument('--browser', default=None)
    ap.add_argument('--desktop', default='1440,900')
    ap.add_argument('--mobile', default='390,844')
    ap.add_argument('--out', default=None, help='JSON summary path (default <project>/docs/references/<id>.json)')
    args = ap.parse_args()

    browser = resolve_browser(args.browser)
    if not browser:
        print(json.dumps({'ok': False, 'capability': 'reference-capture', 'reason': 'browser_missing',
                          'detail': 'agent-browser CLI not found; set --browser or AGENT_BROWSER'}, ensure_ascii=False))
        return 2

    root = Path(args.project).resolve()
    outdir = root / 'docs' / 'references'
    outdir.mkdir(parents=True, exist_ok=True)
    desktop_shot = outdir / ('%s-desktop.png' % args.id)
    mobile_shot = outdir / ('%s-mobile.png' % args.id)

    w, h = args.desktop.split(',')
    run(browser, 'set', 'viewport', w, h)
    run(browser, 'open', args.url)
    desktop = extract_json(browser)
    run(browser, 'screenshot', str(desktop_shot))

    w, h = args.mobile.split(',')
    run(browser, 'set', 'viewport', w, h)
    run(browser, 'open', args.url)
    mobile = extract_json(browser)
    run(browser, 'screenshot', str(mobile_shot))

    record = {
        'ok': True,
        'capability': 'reference-capture',
        'referenceId': args.id,
        'url': args.url,
        'browser': browser,
        'viewports': {'desktop': args.desktop, 'mobile': args.mobile},
        'desktop': desktop,
        'mobile': mobile,
        'evidence': [
            'docs/references/%s-desktop.png' % args.id,
            'docs/references/%s-mobile.png' % args.id,
        ],
    }
    out = Path(args.out).resolve() if args.out else (outdir / ('%s.json' % args.id))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'ok': True, 'id': args.id, 'written': str(out),
                      'desktopVisibleImages': desktop['imageVisible'], 'mobileVisibleImages': mobile['imageVisible'],
                      'desktopTextChars': desktop['textChars'], 'mobileTextChars': mobile['textChars']},
                     ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
