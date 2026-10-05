// Offline authored-record helpers only; no database, HTTP route or live translation service.
import test from 'node:test';
import assert from 'node:assert/strict';
import { sourceHash, makeAuthoredRecord, findCurrentAuthored, seedImportCandidates } from './seed.mjs';
const block = { siteId: 'site-a', contentId: 'page:home', blockId: 'hero:title',
  sourceLanguage: 'en', text: 'Your trusted supplier', context: 'home hero title' };
const seed = () => makeAuthoredRecord(block, { translation: '您信赖的供应伙伴' });

test('initial Chinese is found without needing any engine; other languages miss', async () => {
  const records = [await seed()];
  assert.deepEqual(await findCurrentAuthored(block, 'zh', records),
    { translation: '您信赖的供应伙伴', origin: 'seed' });
  for (const lang of ['es', 'ar', 'ru', 'fr', 'de', 'pt'])
    assert.equal(await findCurrentAuthored(block, lang, records), null);
});
test('new content, changed source or changed context cannot reuse old Chinese', async () => {
  const records = [await seed()];
  for (const changed of [{ ...block, contentId: 'article:new' }, { ...block, text: 'A new source' },
    { ...block, context: 'another use' }])
    assert.equal(await findCurrentAuthored(changed, 'zh', records), null);
});
test('revision and unrelated insertion do not invalidate unchanged stable blocks', async () => {
  const record = await seed();
  assert.equal((await findCurrentAuthored({ ...block, revision: 2 }, 'zh', [record])).origin, 'seed');
  assert.equal(await findCurrentAuthored({ ...block, blockId: 'new:paragraph' }, 'zh', [record]), null);
});
test('site, block and source language identities isolate authored translations', async () => {
  const record = await seed();
  for (const changed of [{ ...block, siteId: 'site-b' }, { ...block, blockId: 'other:title' },
    { ...block, sourceLanguage: 'es' }])
    assert.equal(await findCurrentAuthored(changed, 'zh', [record]), null);
});
test('current manual translation wins; stale manual does not mask current seed', async () => {
  const currentSeed = await seed();
  const manual = await makeAuthoredRecord(block, { translation: '可靠的合作伙伴', origin: 'manual' });
  assert.deepEqual(await findCurrentAuthored(block, 'zh', [currentSeed, manual]),
    { translation: '可靠的合作伙伴', origin: 'manual' });
  const stale = await makeAuthoredRecord({ ...block, text: 'old source' },
    { translation: '旧译文', origin: 'manual' });
  assert.equal((await findCurrentAuthored(block, 'zh', [stale, currentSeed])).origin, 'seed');
});
test('import candidates are idempotent and leave existing manual records untouched', async () => {
  const record = await seed();
  const manual = await makeAuthoredRecord(block, { translation: '自定义中文', origin: 'manual' });
  assert.deepEqual(seedImportCandidates([manual], [record]), []);
  const first = seedImportCandidates([], [record, record]);
  assert.deepEqual(first, [record]);
  assert.deepEqual(seedImportCandidates(first, [record]), []);
  assert.equal(manual.translation, '自定义中文');
});
test('exact source fingerprint is deterministic and preserves whitespace and Unicode', async () => {
  assert.match(await sourceHash(block.text, block.context), /^[a-f0-9]{64}$/);
  assert.equal(await sourceHash(block.text, block.context), await sourceHash(block.text, block.context));
  assert.notEqual(await sourceHash('Hello', ''), await sourceHash('Hello ', ''));
  assert.notEqual(await sourceHash('é', ''), await sourceHash('e\u0301', ''));
});
test('invalid or conflicting authored records fail rather than silently selecting a translation', async () => {
  await assert.rejects(makeAuthoredRecord(block, { translation: '' }), /invalid_authored_translation/);
  const record = await seed();
  await assert.rejects(findCurrentAuthored(block, 'zh', [record, { ...record, translation: '冲突' }]),
    /invalid_authored_translation/);
  assert.throws(() => seedImportCandidates([], [{ ...record, sourceHash: 'invalid' }]),
    /invalid_authored_translation/);
});
