#!/usr/bin/env python3
"""Project-level workflow state recorder for the unified site builder.

The recorder stores facts about a nine-stage delivery pipeline. It never runs the
website, never touches services and never infers a result: every status transition
must be supplied by whoever actually performed the work. Offline, standard library
only, Python 3.11+.

Commands
  init       create <project>/workflow.json from assets/workflow.json
  set        record a stage result (pass/fail/unverified/blocked/not-applicable)
  invalidate mark stages whose evidence was voided by later edits
  aux        record an auxiliary capability version and one invocation result
  block      add or resolve a blocking item
  show       print current state
  check      validate the record against the stage contract

A skipped stage must carry a skipReason. A pass without at least one output path or
evidence entry fails check, because a workflow record may not replace execution.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / 'assets' / 'workflow.json'
STATUSES = ('pass', 'fail', 'unverified', 'blocked', 'not-applicable')
STAGE_IDS = ('environment', 'requirements-content', 'reference-selection', 'design-spec',
             'module-components', 'real-sample', 'design-review', 'full-site-motion',
             'acceptance', 'packaging')
# Stages whose evidence a later stage invalidates when content or code changes.
DOWNSTREAM = {
    'environment': [],
    'requirements-content': ['design-spec', 'acceptance', 'packaging'],
    'reference-selection': ['design-spec', 'module-components', 'design-review',
                            'acceptance', 'packaging'],
    'design-spec': ['module-components', 'real-sample', 'design-review',
                    'full-site-motion', 'acceptance', 'packaging'],
    'module-components': ['real-sample', 'design-review', 'full-site-motion',
                          'acceptance', 'packaging'],
    'real-sample': ['design-review', 'full-site-motion', 'acceptance', 'packaging'],
    'design-review': ['full-site-motion', 'acceptance', 'packaging'],
    'full-site-motion': ['acceptance', 'packaging'],
    'acceptance': ['packaging'], 'packaging': []
}
DOWNSTREAM_BY_TOPIC = {
    'content': ['real-sample', 'design-review', 'acceptance', 'packaging'],
    'visual': ['real-sample', 'design-review', 'full-site-motion', 'acceptance', 'packaging'],
    'runtime': ['acceptance', 'packaging'],
    'admin': ['acceptance', 'packaging']
}


def stamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load(path):
    path = Path(path)
    doc = json.loads(path.read_text(encoding='utf-8'))
    return path, doc


def save(path, doc):
    doc['updatedAt'] = stamp()
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def stage(doc, name):
    for row in doc['stages']:
        if row['id'] == name:
            return row
    raise KeyError('unknown stage: %s' % name)


def relative(project, value):
    """Store paths relative to the project root when they live inside it."""
    if value is None:
        return None
    root = Path(project).resolve()
    target = Path(value).resolve() if os.path.isabs(value) or Path(value).exists() else None
    if target is not None:
        try:
            return str(target.relative_to(root)).replace('\\', '/')
        except ValueError:
            return str(target).replace('\\', '/')
    return str(value).replace('\\', '/')


def cmd_init(args):
    project = args.extra[0]
    if not TEMPLATE.exists():
        raise SystemExit('workflow template not found next to the skill assets')
    doc = json.loads(TEMPLATE.read_text(encoding='utf-8'))
    doc['skillVersion'] = args.skill_version
    doc['projectId'] = args.project_id
    doc['projectName'] = args.project_name
    doc['runtime'] = args.runtime
    doc['createdAt'] = stamp()
    doc['currentStage'] = STAGE_IDS[0]
    path = Path(project) / 'workflow.json'
    if path.exists() and not args.force:
        raise SystemExit('workflow.json already exists; use --force to replace it')
    path.parent.mkdir(parents=True, exist_ok=True)
    save(path, doc)
    print(str(path))
    return 0


def cmd_set(args):
    path, doc = load(args.file)
    # Only init used to write the top-level version, so a project re-verified against a
    # newer Skill kept advertising the version it was originally created with. Let a
    # recorded stage carry the version it was actually verified against.
    if args.skill_version and not args.stage and not args.status:
        # A version-only bump is a legitimate standalone action. It must not be smuggled
        # in as a stage transition: writing `--stage packaging --status pass` would claim
        # a re-verification that did not happen, which is exactly the kind of record that
        # makes the next version problem invisible.
        previous = doc.get('skillVersion')
        doc['skillVersion'] = args.skill_version
        doc['updatedAt'] = stamp()
        save(path, doc)
        print('skillVersion %s -> %s' % (previous, args.skill_version))
        return 0
    if args.skill_version:
        doc['skillVersion'] = args.skill_version
    row = stage(doc, args.stage)
    row['status'] = args.status
    if args.skip_reason:
        row['skipReason'] = args.skip_reason
    elif args.status != 'not-applicable':
        row['skipReason'] = None
    if args.executor:
        row['executor'] = args.executor
    if args.checker:
        row['checker'] = args.checker
    for collection, values in (('outputs', args.output), ('evidence', args.evidence),
                               ('gates', args.gate), ('requiredInputs', args.input),
                               ('capabilities', args.capability), ('scope', args.scope)):
        for value in values:
            stored = relative(Path(args.file).parent, value)
            if stored not in row[collection]:
                row[collection].append(stored)
    row['attempts'].append({'at': stamp(), 'status': args.status, 'actor': args.actor, 'note': args.note})
    row['updatedAt'] = stamp()
    if args.status == 'pass':
        following = [s for s in STAGE_IDS if STAGE_IDS.index(s) > STAGE_IDS.index(args.stage)]
        if following:
            doc['currentStage'] = min(following, key=lambda s: STAGE_IDS.index(s))
    else:
        doc['currentStage'] = args.stage
    save(path, doc)
    print('%s -> %s' % (args.stage, args.status))
    return 0


def cmd_invalidate(args):
    path, doc = load(args.file)
    if args.topic:
        targets = DOWNSTREAM_BY_TOPIC[args.topic]
    else:
        targets = DOWNSTREAM.get(args.stage, []) + ([args.stage] if args.self_stage else [])
    touched = []
    for name in targets:
        row = stage(doc, name)
        if row['status'] in ('pass', 'unverified'):
            row['status'] = 'unverified'
            row['updatedAt'] = stamp()
            row['attempts'].append({'at': stamp(), 'status': 'unverified', 'actor': args.actor,
                                    'note': 'invalidated by change in %s: %s' % (args.stage or args.topic, args.reason)})
            touched.append(name)
    if touched:
        doc['currentStage'] = min(touched, key=lambda s: STAGE_IDS.index(s))
    save(path, doc)
    print('invalidated: %s' % ', '.join(touched) if touched else 'nothing invalidated')
    return 0


def cmd_aux(args):
    path, doc = load(args.file)
    if len(args.capability) != 1:
        raise SystemExit('aux requires exactly one --capability')
    slot = doc['auxCapabilities'].get(args.capability[0])
    if slot is None:
        raise SystemExit('unknown capability: %s' % args.capability[0])
    if args.source:
        slot['source'] = args.source
    if args.commit:
        slot['commit'] = args.commit
    if args.license:
        slot['license'] = args.license
    slot['available'] = args.available
    if args.used_in:
        for value in args.used_in:
            if value not in slot['usedIn']:
                slot['usedIn'].append(value)
    if args.stage or args.result:
        slot['invocations'].append({
            'at': stamp(), 'stage': args.stage, 'action': args.action,
            'result': args.result, 'evidence': relative(Path(args.file).parent, args.evidence[-1]) if args.evidence else None,
            'note': args.note
        })
    save(path, doc)
    print('%s recorded' % args.capability[0])
    return 0


def cmd_block(args):
    path, doc = load(args.file)
    if args.resolve:
        remaining = [b for b in doc['blocks'] if b['id'] != args.resolve]
        if len(remaining) == len(doc['blocks']):
            raise SystemExit('blocking item not found: %s' % args.resolve)
        for row in doc['blocks']:
            if row['id'] == args.resolve:
                row.update(resolvedAt=stamp(), resolution=args.reason)
        doc['blocks'] = remaining + [row for row in doc['blocks'] if row['id'] == args.resolve]
    else:
        if any(b['id'] == args.id for b in doc['blocks']):
            raise SystemExit('blocking item already recorded: %s' % args.id)
        doc['blocks'].append({'id': args.id, 'stage': args.stage, 'summary': args.summary,
                              'owner': args.owner, 'raisedAt': stamp(), 'resolvedAt': None, 'resolution': None})
    save(path, doc)
    print('block %s' % ('resolved' if args.resolve else 'recorded'))
    return 0


def render_summary(doc):
    lines = ['project %s  skill %s  runtime %s' % (doc.get('projectName'), doc.get('skillVersion'), doc.get('runtime'))]
    lines.append('current stage: %s   updated: %s' % (doc.get('currentStage'), doc.get('updatedAt')))
    for row in doc['stages']:
        lines.append('  %-18s %-11s %s' % (row['id'], row['status'], row['skipReason'] or ''))
    return '\n'.join(lines)


def cmd_show(args):
    _, doc = load(args.file)
    if args.json:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    else:
        print(render_summary(doc))
    return 0


def cmd_check(args):
    path, doc = load(args.file)
    errors, warnings = [], []
    if not doc.get('skillVersion'):
        errors.append('skillVersion is required')
    ids = [row['id'] for row in doc['stages']]
    if tuple(ids) != STAGE_IDS:
        errors.append('stage list must be exactly: %s' % ', '.join(STAGE_IDS))
    for row in doc['stages']:
        if row['status'] not in STATUSES:
            errors.append('%s: unknown status %s' % (row['id'], row['status']))
            continue
        if row['status'] == 'not-applicable':
            if not row.get('skipReason'):
                errors.append('%s: not-applicable stage requires a skipReason' % row['id'])
        if not row.get('executor'):
            errors.append('%s: missing executor (who runs this stage)' % row['id'])
        if not row.get('checker'):
            errors.append('%s: missing checker (who verifies the gate)' % row['id'])
            continue
        if row['status'] == 'pass' and not (row.get('outputs') or row.get('evidence')):
            errors.append('%s: pass requires at least one output path or evidence entry' % row['id'])
        if row['status'] == 'blocked' and not any(b['resolvedAt'] is None for b in doc.get('blocks', [])):
            errors.append('%s: blocked stage requires an open blocking item' % row['id'])
        if row['status'] == 'fail' and not row.get('attempts'):
            errors.append('%s: fail requires an attempt note' % row['id'])
    for row in doc['stages']:
        if row['status'] in ('unverified', 'fail', 'blocked'):
            warnings.append('%s: %s' % (row['id'], row['status']))
    print(render_summary(doc))
    for message in errors:
        print('ERROR  ' + message)
    for message in warnings:
        print('WARN   ' + message)
    print('%d error(s), %d warning(s)' % (len(errors), len(warnings)))
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description='Record AI site-building workflow state')
    parser.add_argument('mode', choices=['init', 'set', 'invalidate', 'aux', 'block', 'show', 'check'])
    parser.add_argument('extra', nargs='*', help='init only: target project directory')
    parser.add_argument('--file', dest='file')
    parser.add_argument('--stage', choices=STAGE_IDS)
    parser.add_argument('--status', choices=STATUSES)
    parser.add_argument('--skip-reason', dest='skip_reason')
    parser.add_argument('--note')
    parser.add_argument('--actor', default='agent')
    parser.add_argument('--output', action='append', default=[])
    parser.add_argument('--evidence', action='append', default=[])
    parser.add_argument('--gate', action='append', default=[])
    parser.add_argument('--input', action='append', default=[])
    parser.add_argument('--capability', action='append', default=[])
    parser.add_argument('--scope', action='append', default=[])
    parser.add_argument('--executor', help='who runs this stage, e.g. mainSkill / aux:uiUxProMax / user')
    parser.add_argument('--checker', help='who verifies the gate, e.g. mainSkill / aux:impeccable')
    parser.add_argument('--topic', choices=sorted(DOWNSTREAM_BY_TOPIC))
    parser.add_argument('--self-stage', dest='self_stage', action='store_true')
    parser.add_argument('--reason')
    parser.add_argument('--source')
    parser.add_argument('--commit')
    parser.add_argument('--license', dest='license')
    parser.add_argument('--available', choices=['true', 'false'])
    parser.add_argument('--used-in', dest='used_in', action='append', default=[])
    parser.add_argument('--action')
    parser.add_argument('--result', choices=['success', 'partial', 'failed', 'not-run'])
    parser.add_argument('--id', dest='id')
    parser.add_argument('--summary')
    parser.add_argument('--owner')
    parser.add_argument('--resolve')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--skill-version', dest='skill_version')
    parser.add_argument('--project-id', dest='project_id')
    parser.add_argument('--project-name', dest='project_name')
    parser.add_argument('--runtime')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    if args.mode == 'init':
        if not args.extra:
            parser.error('init requires a target project directory')
        if not args.skill_version:
            parser.error('init requires --skill-version')
        return cmd_init(args)
    if not args.file:
        parser.error('--file is required for %s' % args.mode)
    if args.mode == 'set':
        if not args.stage and not args.status and args.skill_version:
            # Version-only bump: see cmd_set. Re-recording the version after the Skill
            # moves on must not force a stage transition.
            return cmd_set(args)
        if not args.stage or not args.status:
            parser.error('--stage and --status are required (or give --skill-version alone)')
        return cmd_set(args)
    if args.mode == 'invalidate':
        if not (args.stage or args.topic) or not args.reason:
            parser.error('--stage|--topic and --reason are required')
        return cmd_invalidate(args)
    if args.mode == 'aux':
        if not args.capability:
            parser.error('--capability is required')
        args.available = None if args.available is None else args.available == 'true'
        return cmd_aux(args)
    if args.mode == 'block':
        return cmd_block(args)
    if args.mode == 'show':
        return cmd_show(args)
    return cmd_check(args)


if __name__ == '__main__':
    sys.exit(main())
