import test from 'node:test';
import assert from 'node:assert/strict';
import { createTranslationService } from './resolver.mjs';
import { makeAuthoredRecord } from './seed.mjs';
import { protectText } from './engine.mjs';
import { translationProblems } from './quality.mjs';

function fixture() {
  const content = { status: 'published', revision: 1, kind: 'product', blocks: [
    { id: 'a', text: 'Leather furniture', context: 'leather furniture' },
    { id: 'b', text: 'Seat frame', context: 'leather furniture' }] };
  const cache = new Map(), authored = []; let savedIdentity, calls = 0;
  const repository = { getContent: async () => content, getAuthored: async () => authored,
    getCached: async key => cache.get(key), putCached: async (key,value) => cache.set(key,value),
    withLock: async (_,work) => work(), getEngineIdentity: async () => savedIdentity,
    putEngineIdentity: async (_,value) => { savedIdentity = value; } };
  const AI = { run: async () => { calls++; return { translated_text: 'Muebles de cuero' }; } };
  const service = (runtime = { AI }) => createTranslationService({ siteId:'site', languages:['en','zh','es'],
    runtime:{ reserveUsage: async () => true, ...runtime }, repository });
  return { content,cache,authored,AI,service,calls:()=>calls };
}
test('new content translates and a second service reads the persistent cache without calls',async()=>{
  const f=fixture();let result=await f.service().resolve({contentId:'product:1',targetLanguage:'es'});
  assert.equal(result.status,'ready');assert.equal(f.calls(),2);
  result=await f.service().resolve({contentId:'product:1',targetLanguage:'es'});
  assert.equal(result.status,'ready');assert.equal(f.calls(),2);
  result=await f.service({}).resolve({contentId:'product:1',targetLanguage:'es'});
  assert.equal(result.status,'ready');assert.equal(f.calls(),2);
});
test('only a changed block translates again',async()=>{
  const f=fixture();await f.service().resolve({contentId:'product:1',targetLanguage:'es'});
  f.content.revision++;f.content.blocks[0].text='New leather furniture';
  await f.service().resolve({contentId:'product:1',targetLanguage:'es'});
  assert.equal(f.calls(),3);
});
test('initial Chinese is readable with no configured AI',async()=>{
  const f=fixture();for(const block of f.content.blocks)f.authored.push(await makeAuthoredRecord({
    siteId:'site',contentId:'product:1',blockId:block.id,sourceLanguage:'en',text:block.text,context:block.context
  },{translation:'中文正文'}));
  const result=await f.service({}).resolve({contentId:'product:1',targetLanguage:'zh'});
  assert.equal(result.status,'ready');assert.equal(f.calls(),0);
});
test('unpublished or changed content is never written after an AI call',async()=>{
  const f=fixture();f.AI.run=async()=>{f.content.status='draft';return {translated_text:'Texto traducido'};};
  const result=await f.service().resolve({contentId:'product:1',targetLanguage:'es',blockIds:['a']});
  assert.equal(result.reasonCode,'stale_revision');assert.equal(f.cache.size,0);
});
test('unknown language and block ids are rejected',async()=>{
  const f=fixture();await assert.rejects(f.service().resolve({contentId:'product:1',targetLanguage:'xx'}));
  await assert.rejects(f.service().resolve({contentId:'product:1',targetLanguage:'es',blockIds:['unknown']}));
});
test('degenerate repetitive output is rejected and never cached',async()=>{
  const f=fixture();f.AI.run=async()=>({translated_text:'أقراص وأقراص وأقراص وأقراص وأقراص'});
  const r=await f.service().resolve({contentId:'product:1',targetLanguage:'es'});
  assert.equal(r.reasonCode,'quality_rejected');assert.equal(f.cache.size,0);
  assert.deepEqual(translationProblems('Normal furniture description'),[]);
});
test('damaged brackets and Cyrillic placeholder transcription preserve a model',()=>{
  const protectedText=protectText('Model VS-101 leather',{targetLanguage:'ru',protectedTerms:['VS-101']});
  const damaged=protectedText.text.replaceAll('[[','[').replaceAll(']]',']').replaceAll('B2BT','В2ВТ');
  assert.equal(protectedText.restore(damaged),'Model VS-101 leather');
});
