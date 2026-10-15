#!/usr/bin/env python3
"""Offline tests for the workflow recorder. Standard library only, no network."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / 'workflow.py'


def run(*args, cwd=None):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True,
                          text=True, cwd=cwd)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.project = self.tmp / 'proj'
        self.project.mkdir()
        self.record = self.project / 'workflow.json'

    def test_init_creates_record(self):
        result = run('init', str(self.project), '--skill-version', '1.7.0',
                     '--project-name', 'Demo', '--runtime', 'node')
        self.assertEqual(result.returncode, 0, result.stderr)
        doc = json.loads(self.record.read_text(encoding='utf-8'))
        self.assertEqual(len(doc['stages']), 10)
        self.assertEqual(doc['currentStage'], 'environment')
        self.assertEqual([row['status'] for row in doc['stages']], ['unverified'] * 10)

    def test_init_refuses_overwrite(self):
        run('init', str(self.project), '--skill-version', '1.7.0')
        result = run('init', str(self.project), '--skill-version', '1.7.0')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already exists', result.stderr)

    def test_pass_requires_output_or_evidence(self):
        run('init', str(self.project), '--skill-version', '1.7.0')
        run('set', '--file', str(self.record), '--stage', 'environment', '--status', 'pass')
        result = run('check', '--file', str(self.record))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('pass requires', result.stdout)

    def test_pass_with_evidence(self):
        run('init', str(self.project), '--skill-version', '1.7.0')
        run('set', '--file', str(self.record), '--stage', 'environment', '--status', 'pass',
            '--evidence', 'docs/env-report.md')
        result = run('check', '--file', str(self.record))
        self.assertEqual(result.returncode, 0, result.stdout)
        doc = json.loads(self.record.read_text(encoding='utf-8'))
        self.assertEqual(doc['currentStage'], 'requirements-content')

    def test_skip_requires_reason(self):
        run('init', str(self.project), '--skill-version', '1.7.0')
        run('set', '--file', str(self.record), '--stage', 'full-site-motion', '--status', 'not-applicable')
        result = run('check', '--file', str(self.record))
        self.assertNotEqual(result.returncode, 0)
        run('set', '--file', str(self.record), '--stage', 'full-site-motion',
            '--status', 'not-applicable', '--skip-reason', 'No motion requirement for this project')
        result = run('check', '--file', str(self.record))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_invalidate_moves_downstream_to_unverified(self):
        run('init', str(self.project), '--skill-version', '1.7.0')
        for stage in ('module-components', 'real-sample', 'design-review'):
            run('set', '--file', str(self.record), '--stage', stage, '--status', 'pass',
                '--evidence', 'docs/%s.md' % stage)
        result = run('invalidate', '--file', str(self.record), '--stage', 'module-components',
                     '--reason', 'theme layout changed')
        self.assertEqual(result.returncode, 0, result.stderr)
        doc = json.loads(self.record.read_text(encoding='utf-8'))
        statuses = {row['id']: row['status'] for row in doc['stages']}
        self.assertEqual(statuses['real-sample'], 'unverified')
        self.assertEqual(statuses['design-review'], 'unverified')
        self.assertEqual(statuses['acceptance'], 'unverified')
        self.assertEqual(statuses['module-components'], 'pass')
        # every invalidated stage carries a traceable attempt note
        for row in doc['stages']:
            if row['id'] in ('real-sample', 'design-review', 'acceptance'):
                self.assertTrue(any('invalidated by change' in (a.get('note') or '') for a in row['attempts']))

    def test_blocked_requires_open_block(self):
        run('init', str(self.project), '--skill-version', '1.7.0')
        run('set', '--file', str(self.record), '--stage', 'packaging', '--status', 'blocked')
        self.assertNotEqual(run('check', '--file', str(self.record)).returncode, 0)
        run('block', '--file', str(self.record), '--id', 'b1', '--stage', 'packaging',
            '--summary', 'Cloudflare account credentials missing', '--owner', 'user')
        self.assertEqual(run('check', '--file', str(self.record)).returncode, 0)
        run('block', '--file', str(self.record), '--resolve', 'b1', '--reason', 'credentials provided')
        doc = json.loads(self.record.read_text(encoding='utf-8'))
        self.assertFalse([b for b in doc['blocks'] if b['resolvedAt'] is None])
        # a blocked stage with no open block is invalid again
        self.assertNotEqual(run('check', '--file', str(self.record)).returncode, 0)

    def test_aux_records_invocation(self):
        run('init', str(self.project), '--skill-version', '1.7.0')
        run('aux', '--file', str(self.record), '--capability', 'uiUxProMax',
            '--source', 'https://github.com/nextlevelbuilder/ui-ux-pro-max-skill',
            '--commit', '477bcb2', '--license', 'MIT', '--available', 'true',
            '--used-in', 'reference-selection', '--stage', 'reference-selection',
            '--action', 'design suggestions', '--result', 'success',
            '--evidence', 'docs/design-spec.json')
        doc = json.loads(self.record.read_text(encoding='utf-8'))
        slot = doc['auxCapabilities']['uiUxProMax']
        self.assertEqual(slot['available'], True)
        self.assertEqual(slot['commit'], '477bcb2')
        self.assertEqual(len(slot['invocations']), 1)

    def test_unknown_stage_rejected(self):
        run('init', str(self.project), '--skill-version', '1.7.0')
        result = run('set', '--file', str(self.record), '--stage', 'not-a-stage',
                     '--status', 'pass')
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
