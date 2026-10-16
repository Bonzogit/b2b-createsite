"""Behavioral tests for record integrity; these fixtures are not visual evidence."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('design_check', Path(__file__).with_name('design_check.py'))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class DesignChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'docs').mkdir()
        (self.root / 'docs/check.md').write_text('Synthetic test fixture, not an actual browser check', encoding='utf-8')
        (self.root / 'page.html').write_text('<h1>Test fixture</h1>', encoding='utf-8')
        self.verification = {'status': 'pass', 'version': 'demo-2', 'checkedAt': '2026-10-16',
                             'page': '/products', 'viewport': '390x844 Chromium simulation',
                             'evidence': ['docs/check.md'], 'notes': 'Synthetic test record'}
        self.doc = {'recordVersion': '2.0', 'projectVersion': 'demo-2', 'researchStatus': 'pass',
                    'designQuestions': {k: 'Fixture answer' for k in ('audienceTask', 'contentOrder', 'expressionBasis', 'feasibility')},
                    'references': [], 'decisions': [{'id': 'list', 'page': '/products', 'section': 'list',
                     'basis': 'User asks to compare sizes', 'decision': 'Display sizes on cards', 'referenceIds': [],
                     'implementation': ['page.html'], 'verification': dict(self.verification)}],
                    'journeys': [{'id': 'inquiry', 'steps': ['Open product', 'Open inquiry'],
                                  'reason': 'Buyer inquiry task', 'verification': dict(self.verification)}]}

    def check(self, strict=True, version='demo-2'):
        (self.root / 'docs/design-record.json').write_text(json.dumps(self.doc), encoding='utf-8')
        return tool.inspect(self.root, strict, version)

    def test_complete_record_does_not_claim_visual_quality(self):
        report = self.check()
        self.assertTrue(report['recordStructurePassed'], report)
        self.assertTrue(report['verificationRecorded'])
        self.assertFalse(report['visualQualityVerifiedByTool'])

    def test_unverified_is_not_verified_or_strict_success(self):
        self.doc['decisions'][0]['verification'] = {'status': 'unverified'}
        report = self.check(strict=False)
        self.assertTrue(report['recordStructurePassed'], report)
        self.assertFalse(report['verificationRecorded'])
        self.assertFalse(self.check()['recordStructurePassed'])

    def test_missing_or_empty_evidence_rejected(self):
        for value in ('docs/missing.png', 'docs/empty.png'):
            (self.root / 'docs/empty.png').write_bytes(b'')
            self.doc['decisions'][0]['verification']['evidence'] = [value]
            self.assertFalse(self.check()['recordStructurePassed'])

    def test_outside_project_path_rejected(self):
        self.doc['decisions'][0]['verification']['evidence'] = ['../outside.png']
        self.assertFalse(self.check()['recordStructurePassed'])

    def test_old_version_rejected(self):
        self.doc['journeys'][0]['verification']['version'] = 'demo-1'
        self.assertFalse(self.check()['recordStructurePassed'])

    def test_unknown_reference_rejected(self):
        self.doc['decisions'][0]['referenceIds'] = ['invented-source']
        self.assertFalse(self.check()['recordStructurePassed'])

    def test_observed_reference_needs_date_viewport_and_evidence(self):
        self.doc['references'] = [{'id': 'ref-1', 'source': 'User screenshot', 'observationType': 'screenshot'}]
        self.assertFalse(self.check()['recordStructurePassed'])
        self.doc['references'][0].update(observedAt='2026-10-16', viewport='User screenshot, device unknown',
                                         observations='Fixture observation', evidence=['docs/check.md'])
        self.assertTrue(self.check()['recordStructurePassed'])

    def test_research_pass_requires_answers(self):
        self.doc['designQuestions']['feasibility'] = ''
        self.assertFalse(self.check()['recordStructurePassed'])

    def test_pass_requires_implementation(self):
        self.doc['decisions'][0]['implementation'] = []
        self.assertFalse(self.check()['recordStructurePassed'])

    def test_no_journey_requires_reason(self):
        self.doc['journeys'] = []
        self.assertFalse(self.check()['recordStructurePassed'])
        self.doc['journeyNotApplicableReason'] = 'Only a decorative divider changed; no navigation or operation affected'
        self.assertTrue(self.check()['recordStructurePassed'])

    def test_bad_json_and_wrong_root_fail(self):
        p = self.root / 'docs/design-record.json'
        for value in ('{bad', '[]'):
            p.write_text(value)
            self.assertFalse(tool.inspect(self.root)['recordStructurePassed'])


if __name__ == '__main__':
    unittest.main()
