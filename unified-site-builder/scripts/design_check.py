#!/usr/bin/env python3
"""Offline design-record checks; never proves visual quality or interaction success."""
import argparse
import json
from datetime import datetime
from pathlib import Path, PureWindowsPath


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def local_file(root, value):
    if not nonempty(value) or '\\' in value or ':' in value or PureWindowsPath(value).is_absolute():
        return False
    p = Path(value)
    if p.is_absolute() or '..' in p.parts:
        return False
    target = (root / p).resolve()
    return target.is_relative_to(root) and target.is_file() and target.stat().st_size > 0


def date_valid(value):
    try:
        return nonempty(value) and bool(datetime.fromisoformat(value.replace('Z', '+00:00')))
    except ValueError:
        return False


def inspect(project, require_verified=False, version=None):
    root = Path(project).resolve()
    errors, pending, refs = [], [], set()
    try:
        doc = json.loads((root / 'docs/design-record.json').read_text(encoding='utf-8-sig'))
        if not isinstance(doc, dict):
            raise ValueError('record must be an object')
    except (OSError, ValueError) as exc:
        return {'recordStructurePassed': False, 'verificationRecorded': False,
                'visualQualityVerifiedByTool': False, 'errors': [str(exc)], 'unverified': []}

    def need(condition, message):
        if not condition:
            errors.append(message)

    def paths(values, where, required=False):
        need(isinstance(values, list), where + ': expected a list')
        if not isinstance(values, list):
            return
        if required:
            need(bool(values), where + ': at least one local file required')
        for value in values:
            need(local_file(root, value), where + ': missing, empty or unsafe file: ' + str(value))

    def rows(name):
        value = doc.get(name)
        need(isinstance(value, list), name + ': expected a list')
        if not isinstance(value, list):
            return []
        valid = []
        seen = set()
        for i, row in enumerate(value):
            if not isinstance(row, dict):
                errors.append(f'{name}[{i}]: expected an object')
                continue
            ident = row.get('id')
            need(nonempty(ident) and ident not in seen, f'{name}[{i}]: missing or duplicate id')
            if nonempty(ident):
                seen.add(ident)
            valid.append(row)
        return valid

    def verification(row, where):
        v = row.get('verification', {})
        if not isinstance(v, dict):
            errors.append(where + ': verification must be an object')
            return
        status = v.get('status', 'unverified')
        need(status in ('pass', 'fail', 'unverified'), where + ': invalid verification status')
        paths(v.get('evidence', []), where + '.evidence', required=status == 'pass')
        if status != 'pass':
            pending.append(where)
            return
        for key in ('version', 'page', 'viewport', 'notes'):
            need(nonempty(v.get(key)), where + ': pass requires ' + key)
        need(date_valid(v.get('checkedAt')), where + ': pass requires checkedAt date')
        expected = version or doc.get('projectVersion')
        need(nonempty(expected) and v.get('version') == expected,
             where + ': verification version does not match current project version')

    need(doc.get('recordVersion') == '2.0', 'expected recordVersion 2.0; preserve old records and migrate explicitly')
    need(nonempty(doc.get('projectVersion')), 'projectVersion is required')
    if version:
        need(doc.get('projectVersion') == version, 'projectVersion differs from requested version')
    research_status = doc.get('researchStatus')
    need(research_status in ('pass', 'unverified', 'blocked'), 'invalid researchStatus')
    questions = doc.get('designQuestions', {})
    need(isinstance(questions, dict), 'designQuestions must be an object')
    if research_status == 'pass':
        for key in ('audienceTask', 'contentOrder', 'expressionBasis', 'feasibility'):
            need(isinstance(questions, dict) and nonempty(questions.get(key)), 'research pass requires answer: ' + key)
    else:
        pending.append('research')

    for r in rows('references'):
        where = 'reference:' + str(r.get('id'))
        if nonempty(r.get('id')):
            refs.add(r['id'])
        need(nonempty(r.get('source')), where + ': source is required')
        kind = r.get('observationType')
        need(kind in ('visual', 'interaction', 'screenshot', 'source', 'unverified'), where + ': invalid observationType')
        if kind != 'unverified':
            need(date_valid(r.get('observedAt')), where + ': observedAt date required')
            need(nonempty(r.get('observations')), where + ': observations required')
            need(nonempty(r.get('viewport')), where + ': viewport or not-applicable reason required')
            paths(r.get('evidence', []), where + '.evidence', required=True)

    decisions = rows('decisions')
    need(bool(decisions), 'at least one actual design decision is required')
    for row in decisions:
        where = 'decision:' + str(row.get('id'))
        for key in ('page', 'section', 'basis', 'decision'):
            need(nonempty(row.get(key)), where + ': missing ' + key)
        ids = row.get('referenceIds', [])
        need(isinstance(ids, list), where + ': referenceIds must be a list')
        if isinstance(ids, list):
            for ident in ids:
                need(isinstance(ident, str) and ident in refs, where + ': unknown reference id ' + str(ident))
        implementation = row.get('implementation', [])
        paths(implementation, where + '.implementation', required=row.get('verification', {}).get('status') == 'pass'
              if isinstance(row.get('verification', {}), dict) else False)
        verification(row, where)

    journeys = rows('journeys')
    need(bool(journeys) or nonempty(doc.get('journeyNotApplicableReason')),
         'record a task-relevant journey or journeyNotApplicableReason')
    for row in journeys:
        where = 'journey:' + str(row.get('id'))
        steps = row.get('steps')
        need(isinstance(steps, list) and bool(steps) and all(nonempty(x) for x in steps), where + ': steps required')
        need(nonempty(row.get('reason')), where + ': reason required')
        verification(row, where)

    if require_verified and pending:
        errors.append('unverified research, decisions or journeys remain')
    return {'recordStructurePassed': not errors, 'verificationRecorded': not errors and not pending,
            'visualQualityVerifiedByTool': False,
            'scope': 'Records, local files and version labels only; inspect evidence and reproduce interactions separately.',
            'errors': errors, 'unverified': pending}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('project')
    ap.add_argument('--require-verified', action='store_true')
    ap.add_argument('--version')
    args = ap.parse_args()
    report = inspect(args.project, args.require_verified, args.version)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['recordStructurePassed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
