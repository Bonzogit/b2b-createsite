// Offline adapter tests. All AI/network calls below are doubles, not live translations.
import test from 'node:test';
import assert from 'node:assert/strict';
import { initTranslationEngine, protectText, DEFAULT_WORKERS_MODEL } from './engine.mjs';

const options = { sourceLanguage: 'en', targetLanguage: 'es' };
const external = { TRANSLATION_ENDPOINT: 'https://engine.example/v1/chat/completions',
  TRANSLATION_API_KEY: 'test-only', TRANSLATION_MODEL: 'test-model' };
const tokens = value => value.match(/\[\[B2BT_[a-f0-9]+_\d+\]\]/g) || [];
const rejects = (promise, code) => assert.rejects(promise, error => error.code === code);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
function mockResponse(input, transform = value => value) {
  const body = JSON.parse(input.body);
  const texts = JSON.parse(body.messages[1].content);
  return { ok: true, json: async () => ({ choices: [{ message: { content: JSON.stringify(texts.map(transform)) } }] }) };
}

test('unconfigured does not call a provider; same-language text bypasses AI', async () => {
  const engine = initTranslationEngine({ fetch: () => assert.fail('unexpected call') });
  assert.deepEqual(engine.engineStatus(), { provider: 'unconfigured', model: null, configured: false,
    engineVersion: 'dual-engine-v1:protected-v1', glossaryVersion: '1' });
  await rejects(engine.callEngine(['Hello'], options), 'unconfigured');
  assert.deepEqual(await engine.callEngine(['Hello'], { targetLanguage: 'en' }), ['Hello']);
});

test('partial external config stays unconfigured and status contains no secrets', async () => {
  const env = { ...external }; delete env.TRANSLATION_MODEL;
  const engine = initTranslationEngine({ env });
  assert.equal(engine.engineStatus().configured, false);
  assert.ok(!JSON.stringify(engine.engineStatus()).includes('test-only'));
});

test('Workers AI wins over external config and uses one synchronous call per block', async () => {
  const calls = [];
  const engine = initTranslationEngine({ env: external,
    AI: { run: async (model, input) => { calls.push({ model, input }); return { translated_text: 'Traducido: ' + input.text }; } },
    fetch: () => assert.fail('fallback must not run') });
  assert.equal(engine.engineStatus().provider, 'workers-ai');
  assert.deepEqual(await engine.callEngine(['Hello', 'World'], options), ['Traducido: Hello', 'Traducido: World']);
  assert.equal(calls.length, 2);
  assert.deepEqual(calls[0], { model: DEFAULT_WORKERS_MODEL, input: { text: 'Hello', source_lang: 'en', target_lang: 'es' } });
});

test('all default language directions are routed with language codes', async () => {
  let calls = 0;
  const engine = initTranslationEngine({ AI: { run: async (_, input) => { calls++; return { translated_text: input.text }; } } });
  for (const sourceLanguage of ['en', 'zh', 'es', 'ar', 'ru', 'fr', 'de', 'pt']) {
    for (const targetLanguage of ['en', 'zh', 'es', 'ar', 'ru', 'fr', 'de', 'pt']) {
      await engine.callEngine(['Hello'], { sourceLanguage, targetLanguage });
    }
  }
  assert.equal(calls, 56); // Routing only; mocks do not prove model language quality.
});

test('brands, repeated model codes, dimensions, units, email and URL survive translation', () => {
  const source = 'Valenza VL-200: 120 × 60 × 80 cm, 24 V, 3.5 kg, 25%; sales@example.com https://example.com/p/200. Valenza VL-200.';
  const protectedText = protectText(source, { ...options, protectedTerms: ['Valenza', 'VL-200'] });
  assert.ok(!protectedText.text.includes('Valenza'));
  assert.ok(!protectedText.text.includes('sales@example.com'));
  assert.ok(!protectedText.text.includes('24 V'));
  const found = tokens(protectedText.text);
  assert.equal(new Set(found).size, found.length);
  assert.equal(protectedText.restore(protectedText.text), source);
  const translated = protectedText.text.split(/(\[\[B2BT_[a-f0-9]+_\d+\]\])/g)
    .map(part => tokens(part).length ? part : ' traducido ').join('');
  const restored = protectedText.restore(translated);
  for (const value of ['Valenza', 'VL-200', '120 × 60 × 80 cm', '24 V', '3.5 kg', '25%', 'sales@example.com', 'https://example.com/p/200']) {
    assert.ok(restored.includes(value), `protected value missing: ${value}`);
  }
});

test('glossary uses target translation, content scope and exact word boundaries', () => {
  const glossary = [
    { source: 'leather', sourceLanguage: 'en', targetLanguage: 'es', mode: 'translate', translation: 'cuero', scope: 'global', version: '1' },
    { source: 'leather', sourceLanguage: 'en', targetLanguage: 'es', mode: 'translate', translation: 'piel', scope: 'product', version: '2' },
    { source: 'Valenza', sourceLanguage: 'en', targetLanguage: '*', mode: 'preserve', translation: null, scope: 'global', version: '1' }
  ];
  const block = protectText('Valenza leather leatherette', { ...options, scope: 'product', glossary });
  assert.equal(block.restore(block.text), 'Valenza piel leatherette');
});

test('longer glossary phrases win and conflicting equal-scope entries are rejected', () => {
  const base = { sourceLanguage: 'en', targetLanguage: 'es', mode: 'translate', scope: 'global', version: '1' };
  const glossary = [{ ...base, source: 'leather', translation: 'cuero' },
    { ...base, source: 'full-grain leather', translation: 'cuero de plena flor' }];
  const block = protectText('full-grain leather', { ...options, glossary });
  assert.equal(block.restore(block.text), 'cuero de plena flor');
  assert.throws(() => protectText('leather', { ...options, glossary: [...glossary, { ...base, source: 'leather', translation: 'piel' }] }), error => error.code === 'invalid_glossary');
});

test('missing, duplicated, mutated and unknown placeholders fail closed', () => {
  const block = protectText('Valenza furniture', { ...options, protectedTerms: ['Valenza'] });
  const [token] = tokens(block.text);
  for (const output of [block.text.replace(token, ''), block.text + token,
    block.text.replace(token, token.replace('B2BT_', 'MODIFIED_')),
    block.text + ' [[B2BT_unknown_0]]']) {
    assert.throws(() => block.restore(output), error => error.code === 'placeholder_mismatch');
  }
});

test('literal source placeholders are preserved without collision', () => {
  const text = 'Reference [[B2BT_old_0]] and 200 kg';
  const block = protectText(text, options);
  assert.equal(block.restore(block.text), text);
});

test('Chinese terms are protected within text without spaces', () => {
  const text = '使用华伦品牌的皮革家具';
  const block = protectText(text, { sourceLanguage: 'zh', targetLanguage: 'en', protectedTerms: ['华伦'] });
  assert.ok(!block.text.includes('华伦'));
  assert.equal(block.restore(block.text), text);
});

test('parallel requests share a concurrency cap and retain input order', async () => {
  let active = 0, maximum = 0;
  const engine = initTranslationEngine({ concurrency: 2, AI: { run: async (_, input) => {
    active++; maximum = Math.max(maximum, active);
    await sleep(input.text === 'First' ? 10 : 1); active--;
    return { translated_text: 'T:' + input.text };
  } } });
  const output = await Promise.all([engine.callEngine(['First', 'Second'], options), engine.callEngine(['Third', 'Fourth'], options)]);
  assert.equal(maximum, 2);
  assert.deepEqual(output, [['T:First', 'T:Second'], ['T:Third', 'T:Fourth']]);
});

test('provider failure never falls back to a configured paid engine', async () => {
  const engine = initTranslationEngine({ env: external, AI: { run: async () => { throw new Error('private provider detail'); } },
    fetch: () => assert.fail('fallback must not run') });
  await rejects(engine.callEngine(['Hello'], options), 'provider_error');
});

test('persistent budget hook can stop calls before any AI invocation', async () => {
  const engine = initTranslationEngine({ reserveUsage: async () => false, AI: { run: () => assert.fail('budget exceeded') } });
  await rejects(engine.callEngine(['Hello'], options), 'quota_exceeded');
});

test('unsupported direction and alternate model require explicit support', async () => {
  const engine = initTranslationEngine({ AI: { run: () => assert.fail('unsupported direction') } });
  await rejects(engine.callEngine(['Hello'], { targetLanguage: 'xx' }), 'unsupported_direction');
  const custom = initTranslationEngine({ AI: { run: () => assert.fail('unknown schema') }, env: { WORKERS_AI_TRANSLATION_MODEL: 'other-model' } });
  await rejects(custom.callEngine(['Hello'], options), 'unsupported_model');
});

test('OpenAI compatible batch uses configured endpoint/model and validates protected output', async () => {
  let url, request;
  const engine = initTranslationEngine({ env: external, fetch: async (u, r) => {
    url = u; request = r; return mockResponse(r, text => 'T:' + text);
  } });
  const output = await engine.callEngine(['Valenza furniture', '24 V motor'], { ...options, protectedTerms: ['Valenza'] });
  assert.deepEqual(output, ['T:Valenza furniture', 'T:24 V motor']);
  assert.equal(url, external.TRANSLATION_ENDPOINT);
  assert.equal(JSON.parse(request.body).model, 'test-model');
  assert.equal(request.redirect, 'error');
  assert.equal(engine.engineStatus().provider, 'openai-compatible');
});

test('invalid output shape and placeholder damage reject a batch', async () => {
  const wrongShape = initTranslationEngine({ env: external, fetch: async () => ({ ok: true, json: async () => ({ choices: [{ message: { content: '["Only one"]' } }] }) }) });
  await rejects(wrongShape.callEngine(['Hello', 'World'], options), 'invalid_engine_output');
  const damaged = initTranslationEngine({ env: external, fetch: async (_, r) => mockResponse(r, text => text.replace(/\[\[B2BT_[^\]]+\]\]/g, '')) });
  await rejects(damaged.callEngine(['Valenza furniture'], { ...options, protectedTerms: ['Valenza'] }), 'placeholder_mismatch');
});

test('HTTP authorization and rate-limit failures are sanitized', async () => {
  for (const [status, code] of [[401, 'unauthorized'], [403, 'unauthorized'], [429, 'rate_limited'], [500, 'provider_error']]) {
    const engine = initTranslationEngine({ env: external, fetch: async () => ({ ok: false, status }) });
    await rejects(engine.callEngine(['Hello'], options), code);
  }
});

test('timeout retains the occupied Workers slot until the underlying call settles', async () => {
  let finish, calls = 0;
  const engine = initTranslationEngine({ concurrency: 1, timeoutMs: 15, AI: { run: async (_, input) => {
    calls++; if (calls === 1) await new Promise(resolve => { finish = resolve; });
    return { translated_text: input.text };
  } } });
  await rejects(engine.callEngine(['Hello'], options), 'timeout');
  await rejects(engine.callEngine(['World'], options), 'timeout');
  assert.equal(calls, 1);
  finish(); await sleep(5);
  assert.equal(calls, 1); // Expired queued call is discarded, no duplicate billable call.
});

test('unsafe external endpoint is rejected before transmitting its key', async () => {
  const engine = initTranslationEngine({ env: { ...external, TRANSLATION_ENDPOINT: 'http://engine.example/' }, fetch: () => assert.fail('unsafe transmission') });
  await rejects(engine.callEngine(['Hello'], options), 'invalid_config');
});

test('budget reservation that finishes after timeout cannot initiate an AI call', async () => {
  let reserved;
  const engine = initTranslationEngine({ timeoutMs: 10, reserveUsage: () => new Promise(resolve => { reserved = resolve; }),
    AI: { run: () => assert.fail('late provider call') } });
  await rejects(engine.callEngine(['Hello'], options), 'timeout');
  reserved(true); await sleep(5);
});
