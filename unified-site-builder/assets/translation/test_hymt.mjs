import test from 'node:test';
import assert from 'node:assert/strict';
import {initTranslationEngine} from './engine.mjs';
const env={TRANSLATION_PROVIDER:'hymt',TRANSLATION_API_KEY:'test-only'};
const options={sourceLanguage:'en',targetLanguage:'zh',protectedTerms:['Acme'],glossary:[{source:'full-grain leather',sourceLanguage:'en',targetLanguage:'zh',scope:'global',version:'1',mode:'translate',translation:'全粒面皮革'}]};
const mock = result => ({ok:true,status:200,json:async()=>({result})});
test('Hy native request preserves brand, model, dimensions and terminology',async()=>{
 const engine=initTranslationEngine({env,AI:{run:()=>assert.fail('wrong provider')},fetch:async(url,req)=>{
  assert.equal(url,'https://43.162.83.155/translation/translate');const body=JSON.parse(req.body);assert.equal(body.from,'en');assert.equal(body.to,'zh');assert.ok(!body.text.includes('Acme'));assert.ok(!body.text.includes('leather'));return mock('[[B2BT_0]] [[B2BT_1]] 使用 [[B2BT_2]]，其宽度为 [[B2BT_3]]。');
 }});
 assert.deepEqual(await engine.callEngine(['Acme VS-101 uses full-grain leather and is 42 cm wide.'],options),['Acme VS-101 使用 全粒面皮革，其宽度为 42 cm。']);
});
test('Hy rejects damaged placeholders and partial English output',async()=>{
 for(const result of ['产品 [[B2BT_0]]','[[B2BT_0]] [[B2BT_1]] uses [[B2BT_2]] and is [[B2BT_3]] wide.']){
 const engine=initTranslationEngine({env,fetch:async()=>mock(result)});await assert.rejects(engine.callEngine(['Acme VS-101 uses full-grain leather and is 42 cm wide.'],options));}
});
test('Hy missing key cannot silently use another engine',async()=>{
 const engine=initTranslationEngine({env:{TRANSLATION_PROVIDER:'hymt'},AI:{run:()=>assert.fail('fallback')}});assert.equal(engine.engineStatus().configured,false);
 await assert.rejects(engine.callEngine(['Hello'],options),e=>e.code==='unconfigured');
});
test('Hy unauthorized and non-HTTPS endpoints fail safely',async()=>{
 const engine=initTranslationEngine({env,fetch:async()=>({ok:false,status:401})});await assert.rejects(engine.callEngine(['Hello'],options),e=>e.code==='unauthorized');
 const unsafe=initTranslationEngine({env:{...env,TRANSLATION_ENDPOINT:'http://example.test/'},fetch:()=>assert.fail('key leak')});await assert.rejects(unsafe.callEngine(['Hello'],options),e=>e.code==='invalid_config');
});
test('Hy retry is bounded and timeout aborts retry delay',async()=>{
 let calls=0;const engine=initTranslationEngine({env,timeoutMs:25,fetch:async()=>{calls++;return {ok:false,status:429};}});await assert.rejects(engine.callEngine(['Hello'],options),e=>e.code==='timeout');assert.equal(calls,1);
});
