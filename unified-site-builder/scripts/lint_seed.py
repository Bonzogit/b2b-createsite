#!/usr/bin/env python3
"""Lint a project's seed content and initial Chinese translations.

Catches the seed defects that are invisible in the JSON but visible on the rendered
page, and that a reviewer cannot be expected to find by reading the source:

  * a literal backslash-n escape that the theme prints as text instead of starting a
    new paragraph (caused by a doubled backslash in the seed builder)
  * English/Chinese paragraph count mismatch, which leaves a body block untranslated
  * a content block that has no initial Chinese translation

The block list is derived by mirroring `contentBlocks()` in lib/app.mjs, which is the
single registry of translatable blocks. Predicting only title/summary/body is what let
this class of defect through: spec, option, FAQ, highlight and gallery blocks were never
predicted, so a page could ship with English specification rows, English image captions
and an untranslated inquiry-page FAQ while the lint still reported pass. Keep this list
in lockstep with contentBlocks(); if the registry grows, this lint must grow with it.

Usage:
    python lint_seed.py <project-dir> [--json]

Exit codes: 0 = clean, 1 = findings, 2 = seed files missing or unreadable.
"""
import argparse
import json
import sys
from pathlib import Path

TEXT_FIELDS = ('title', 'summary', 'body')
KINDS = ('pages', 'products', 'articles', 'categories')
BACKSLASH_N = chr(92) + 'n'
# Block families that a page can be missing while still showing Chinese elsewhere.
FAMILIES = ('spec', 'option', 'faq', 'highlight', 'gallery')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def present(*values):
    """contentBlocks() drops a block whose source text is empty, so only non-empty
    fields are expected to carry a translation."""
    return all(str(v or '').strip() for v in values)


def blocks_of(item):
    """Every block id contentBlocks() would emit for this item.

    Mirrors lib/app.mjs:
      title, summary, body<i>
      spec<i>.group / spec<i>.label / spec<i>.value
      faq<i>.q / faq<i>.a
      highlight<i>
      gallery<i>.alt / gallery<i>.caption
      option<i>.label / option<i>.value
    """
    blocks = []
    if present(item.get('title')):
        blocks.append('title')
    if present(item.get('summary')):
        blocks.append('summary')
    paragraphs = [p for p in str(item.get('body') or '').split('\n\n') if p]
    blocks += ['body%d' % i for i in range(len(paragraphs))]

    for index, spec in enumerate(item.get('specs') or []):
        for key in ('group', 'label', 'value'):
            if present(spec.get(key)):
                blocks.append('spec%d.%s' % (index, key))
    for index, row in enumerate(item.get('faqs') or []):
        for key in ('q', 'a'):
            if present(row.get(key)):
                blocks.append('faq%d.%s' % (index, key))
    for index, value in enumerate(item.get('highlights') or []):
        if present(value):
            blocks.append('highlight%d' % index)
    for index, row in enumerate(item.get('gallery') or []):
        for key in ('alt', 'caption'):
            if present(row.get(key)):
                blocks.append('gallery%d.%s' % (index, key))
    for index, row in enumerate(item.get('options') or []):
        for key in ('label', 'value'):
            if present(row.get(key)):
                blocks.append('option%d.%s' % (index, key))
    return blocks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--json', action='store_true', help='machine readable report')
    args = parser.parse_args()

    project = args.project.resolve()
    content_path = project / 'seed' / 'content.json'
    zh_path = project / 'seed' / 'translations.zh.json'
    for path in (content_path, zh_path):
        if not path.is_file():
            print('seed file not found: ' + str(path))
            return 2

    content = load(content_path)
    zh_rows = load(zh_path)
    zh_by_block = {row['blockId']: (row.get('translation') or '').strip() for row in zh_rows}

    findings = []
    counted = 0
    expected = 0
    by_kind = {}
    family_expect = {}
    for kind in KINDS:
        for item in content.get(kind) or []:
            counted += 1
            ident = '%s:%s' % (kind[:-1], item.get('slug') or item.get('id'))
            for field in TEXT_FIELDS:
                value = str(item.get(field) or '')
                if BACKSLASH_N in value:
                    findings.append({'rule': 'literal-escape', 'item': ident, 'field': field,
                                     'detail': 'contains a literal backslash-n; the theme will print it as text'})
            blocks = blocks_of(item)
            expected += len(blocks)
            by_kind[kind] = by_kind.get(kind, 0) + len(blocks)
            for block in blocks:
                block_id = item['id'] + '#' + block
                tail = block.split('.')[0].rstrip('0123456789')
                if tail in FAMILIES:
                    row = family_expect.setdefault(tail, {'blocks': 0, 'untranslated': 0})
                    row['blocks'] += 1
                    if not zh_by_block.get(block_id):
                        row['untranslated'] += 1
                if not zh_by_block.get(block_id):
                    findings.append({'rule': 'missing-initial-chinese', 'item': ident, 'block': block_id,
                                     'detail': 'no initial Chinese translation for this block'})
    for row in zh_rows:
        if not (row.get('translation') or '').strip():
            findings.append({'rule': 'empty-translation', 'item': row['blockId'], 'block': row['blockId'],
                             'detail': 'row present but translation is empty'})

    report = {
        'project': str(project),
        'items': counted,
        'expectedBlocks': expected,
        'blocksByKind': by_kind,
        'chineseBlocks': len(zh_rows),
        'familyCoverage': {k: family_expect[k] for k in sorted(family_expect)},
        'findings': findings,
        'passed': not findings,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print('project        : ' + report['project'])
        print('content items  : %d, expected translatable blocks: %d, initial Chinese blocks: %d'
              % (counted, expected, len(zh_rows)))
        for name in sorted(family_expect):
            row = family_expect[name]
            print('  coverage %-10s %4d blocks, %d untranslated' % (name, row['blocks'], row['untranslated']))
        for row in findings:
            print('  %-24s %-28s %s' % (row['rule'], row.get('item', ''), row['detail']))
        print('result         : ' + ('pass' if report['passed'] else 'fail (%d findings)' % len(findings)))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
