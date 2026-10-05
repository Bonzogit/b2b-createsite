"""Tests only the offline checker/packager, not a generated website."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

import site_package as sp


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'site'
        self.root.mkdir()
        self.assets = Path(__file__).resolve().parents[1] / 'assets'
        shutil.copyfile(self.assets / 'site.contract.json', self.root / 'site.contract.json')
        shutil.copyfile(self.assets / 'deploy.node.json', self.root / 'deploy.json')
        for name in ('engine','resolver','quality','seed'):
            self.write('lib/translation/'+name+'.mjs', (self.assets/'translation'/f'{name}.mjs').read_text(encoding='utf-8'))
        self.json('config/translation-glossary.json', {'version':'1','entries':[{'source':'leather','sourceLanguage':'en','targetLanguage':'zh','scope':'global','version':'1','mode':'translate','translation':'皮革'}]})
        self.json('seed/translations.zh.json', [{'targetLanguage':'zh','origin':'seed','translation':'测试中文','sourceHash':'a'*64}])
        self.write('server.mjs', '// A structural fixture, not a working server.\n')
        self.write('public/index.html', '<html lang="en"><body>Fixture</body></html>')
        for doc in sp.DOCS:
            self.write('docs/' + doc, 'Structural fixture only; runtime unverified.\n')
        self.json('package.json', {'type': 'module', 'scripts': {'start': 'node server.mjs'}})
        self.json('package-lock.json', {'lockfileVersion': 3, 'packages': {'': {}}})

    def write(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')

    def json(self, name, value):
        self.write(name, json.dumps(value))

    def contract(self, **updates):
        p = self.root / 'site.contract.json'
        data = json.loads(p.read_text())
        data.update(updates)
        self.json('site.contract.json', data)

    def test_structure_does_not_claim_functionality(self):
        result, _ = sp.inspect(self.root)
        self.assertTrue(result['structurePassed'], result)
        self.assertFalse(result['runtimeVerified'])

    def test_missing_backend(self):
        (self.root / 'server.mjs').unlink()
        self.assertFalse(sp.inspect(self.root)[0]['structurePassed'])

    def test_malformed_json(self):
        self.write('site.contract.json', '{broken')
        self.assertFalse(sp.inspect(self.root)[0]['structurePassed'])

    def test_escape_path(self):
        self.contract(entry='../outside.mjs')
        self.assertFalse(sp.inspect(self.root)[0]['structurePassed'])

    def test_unknown_feature_mode(self):
        self.contract(features={'cms': True, 'articles': True, 'inquiries': True, 'translation': 'pretranslate-everything'})
        self.assertFalse(sp.inspect(self.root)[0]['structurePassed'])

    def test_lockfile_mismatch(self):
        self.json('package.json', {'type': 'module', 'scripts': {'start': 'node server.mjs'}, 'dependencies': {'abc': '1.0.0'}})
        self.assertFalse(sp.inspect(self.root)[0]['structurePassed'])

    def test_unimplemented_deploy_fields(self):
        p = self.root / 'deploy.json'
        data = json.loads(p.read_text())
        data['createDatabaseAutomatically'] = True
        self.json('deploy.json', data)
        self.assertFalse(sp.inspect(self.root)[0]['structurePassed'])

    def test_secrets_and_runtime_excluded_from_zip(self):
        for name in ['.env', 'credentials.json', 'data/app.json', 'uploads/private.pdf', 'node_modules/a/index.js']:
            self.write(name, 'private fixture')
        report, files = sp.inspect(self.root)
        self.assertTrue(report['structurePassed'], report)
        target = Path(self.tmp.name) / 'result.zip'
        result = sp.pack(self.root, target, files)
        self.assertEqual(len(result['sha256']), 64)
        with zipfile.ZipFile(target) as z:
            self.assertIsNone(z.testzip())
            self.assertIn('server.mjs', z.namelist())
            self.assertNotIn('.env', z.namelist())
            self.assertFalse(any(n.startswith(('data/', 'uploads/', 'node_modules/')) for n in z.namelist()))

    def test_public_secret_rejected(self):
        self.write('public/.env', 'private fixture')
        self.assertFalse(sp.inspect(self.root)[0]['structurePassed'])

    def test_public_runtime_rejected(self):
        self.write('public/uploads/private.pdf', 'private fixture')
        self.assertFalse(sp.inspect(self.root)[0]['structurePassed'])

    def test_no_overwrite(self):
        target = Path(self.tmp.name) / 'keep.zip'
        target.write_bytes(b'KEEP')
        with self.assertRaises(FileExistsError):
            sp.pack(self.root, target, sp.inspect(self.root)[1])
        self.assertEqual(target.read_bytes(), b'KEEP')

    def test_output_not_in_source(self):
        with self.assertRaises(ValueError):
            sp.pack(self.root, self.root / 'result.zip', sp.inspect(self.root)[1])

    def test_cloudflare_profile(self):
        self.contract(runtime='cloudflare-workers', entry='src/worker.mjs')
        self.write('src/worker.mjs', 'export default {};')
        self.json('wrangler.json', {'main': 'src/worker.mjs', 'assets': {'directory': 'public'}, 'compatibility_date': '2026-10-02'})
        report, _ = sp.inspect(self.root)
        self.assertTrue(report['structurePassed'], report)
        self.assertTrue(any('NOT verified' in w for w in report['warnings']))

    def test_cloudflare_assets_equivalent_directory(self):
        self.contract(runtime='cloudflare-workers',entry='worker.mjs')
        self.write('worker.mjs','export default {};')
        self.json('wrangler.json',{'main':'worker.mjs','assets':{'directory':'./public'},'compatibility_date':'2026-10-05'})
        self.assertTrue(sp.inspect(self.root)[0]['structurePassed'])

    def test_cloudflare_assets_escape_rejected(self):
        self.contract(runtime='cloudflare-workers',entry='worker.mjs')
        self.write('worker.mjs','export default {};')
        self.json('wrangler.json',{'main':'worker.mjs','assets':{'directory':'../public'},'compatibility_date':'2026-10-05'})
        self.assertFalse(sp.inspect(self.root)[0]['structurePassed'])

    def test_bad_cloudflare_assets(self):
        self.contract(runtime='cloudflare-workers')
        self.json('wrangler.json', {'main': 'server.mjs', 'assets': {'directory': 'missing'}, 'compatibility_date': '2026-10-02'})
        self.assertFalse(sp.inspect(self.root)[0]['structurePassed'])

    def test_symlink_rejected(self):
        target = Path(self.tmp.name) / 'outside.txt'
        target.write_text('private fixture')
        try:
            (self.root / 'public/linked.txt').symlink_to(target)
        except OSError:
            self.skipTest('Host does not allow creating test symlinks')
        self.assertFalse(sp.inspect(self.root)[0]['structurePassed'])


if __name__ == '__main__':
    unittest.main()
