// End-to-end application checks with delayed/failing provider; no external service or customer data.
import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs/promises';import os from 'node:os';import path from 'node:path';import {execFileSync} from 'node:child_process';import {pathToFileURL} from 'node:url';
const skill=path.resolve(import.meta.dirname,'..'),dir=await fs.mkdtemp(path.join(os.tmpdir(),'public-translation-test-'));
execFileSync(process.env.PYTHON_BIN||'python',[path.join(skill,'scripts/create_site.py'),dir,'--runtime','node']);
const {initialize,createApplication}=await import(pathToFileURL(path.join(dir,'lib/app.mjs')));
const {createTranslationJobs}=await import(pathToFileURL(path.join(dir,'lib/translation-jobs.mjs')));
const seed=JSON.parse(await fs.readFile(path.join(dir,'seed/content.json'))),authored=JSON.parse(await fs.readFile(path.join(dir,'seed/translations.zh.json')));
const oldFetch=globalThis.fetch;let state,calls=0,active=0,maxActive=0,fail=false,order=[];
const st={read:async()=>structuredClone(state),initialize:async v=>{state=structuredClone(v);},mutate:async fn=>{const d=structuredClone(state),out=fn(d);state=d;return structuredClone(out);}};
const env={SITE_ORIGIN:'https://public.test',SITE_ADMIN_PASSWORD:crypto.randomUUID(),TRANSLATION_PROVIDER:'hymt',TRANSLATION_API_KEY:'test-only',TRANSLATION_ENDPOINT:'https://provider.invalid/translate'};
globalThis.fetch=async(_,options)=>{calls++;active++;maxActive=Math.max(maxActive,active);const d=JSON.parse(options.body);order.push(d.text);await new Promise(r=>setTimeout(r,40));active--;if(fail)return new Response('{}',{status:401});return Response.json({result:(d.to==='zh'?'这是验证使用的译文。':'Contenu traduit.')+(d.text.match(/\[\[B2BT_\d+\]\]/g)||[]).join(' ')});};
await initialize(st,seed,env,authored);const options={storage:st,env,glossary:{version:'1',entries:[]},scheduleTranslation:async()=>{},asset:async()=>new Response('asset')};let app=createApplication(options);
async function request(p,input,headers={}){const r=await app(new Request(env.SITE_ORIGIN+p,{method:input?'POST':'GET',headers:{origin:env.SITE_ORIGIN,'content-type':'application/json',...headers},body:input?JSON.stringify(input):undefined}));return {status:r.status,data:r.headers.get('content-type')?.includes('json')?(await r.json()).data:await r.text()};}
async function drain(){for(let i=0;i<100;i++){if(!Object.values(state.translationJobs||{}).some(j=>['queued','running'].includes(j.status)))return;await app.translationJobs.tick();}throw Error('Queue did not drain');}
test('cold HTML never invokes provider; lists and forms reuse target-language content',async()=>{
 const start=performance.now(),r=await request('/?lang=fr');assert.equal(r.status,200);assert(performance.now()-start<300);assert.equal(calls,0);assert(r.data.includes('data-translation-block="home#title"'));
 const zh=await request('/products/?lang=zh');assert(zh.data.includes('示例产品'));assert(zh.data.includes('用于部署验收的产品信息。'));assert.equal(calls,0);
 const form=await request('/contact/?lang=zh');assert(form.data.includes('需求内容'));assert(form.data.includes('提交询盘'));assert(form.data.includes('询盘已保存，编号：'));assert(!form.data.includes('name="message" value='));
});
test('public and background share queue, merge duplicates, prioritize visible blocks and never overlap',async()=>{
 const body={contentId:'product:sample-product',targetLanguage:'fr',blockIds:['sample-product#title']};
 await app.translationJobs.enqueue('article:sample-guide',['fr']);
 const [a,b]=await Promise.all([request('/api/v1/translations/resolve',body),request('/api/v1/translations/resolve',body)]);assert.equal(calls,0);assert.equal(a.data.status,'pending');assert.equal(b.data.status,'pending');
 assert.equal(Object.values(state.translationJobs).filter(j=>j.contentId===body.contentId).length,1);
 await Promise.all([app.translationJobs.tick(),app.translationJobs.tick()]);assert.equal(calls,1);assert(order[0].includes('Sample product'));assert.equal(maxActive,1);
 await drain();const before=calls;assert((await request('/products/?lang=fr')).data.includes('Contenu traduit.'));assert.equal(calls,before);
 assert.equal((await request('/api/v1/translations/resolve',body)).data.status,'ready');assert.equal(calls,before);
 // Rebuilt app reads the same persistent cache.
 app=createApplication(options);assert.equal((await request('/api/v1/translations/resolve',body)).data.status,'ready');assert.equal(calls,before);
 const invalid=await request('/api/v1/translations/resolve',{...body,blockIds:['invalid']});assert.equal(invalid.status,400);
 assert.equal((await request('/api/v1/translations/resolve',body,{origin:'https://foreign.test'})).status,403);
});
test('terminal provider failure is visible, polling does not restart it, explicit retry recovers',async()=>{
 const body={contentId:'page:home',targetLanguage:'fr',blockIds:['home#body0']};fail=true;
 await request('/api/v1/translations/resolve',body);await drain();const before=calls;
 const result=await request('/api/v1/translations/resolve',body);assert.equal(result.data.status,'failed');assert.equal(result.data.reasonCode,'unauthorized');assert.equal(result.data.retryAfterMs,0);
 await request('/api/v1/translations/resolve',body);assert.equal(calls,before);
 fail=false;await request('/api/v1/translations/resolve',{...body,retry:true});await drain();assert.equal((await request('/api/v1/translations/resolve',body)).data.status,'ready');assert.equal(calls,before+1);assert.equal(maxActive,1);
});
test('offscreen blocks never move ahead of visible blocks when requests merge',async()=>{
 let db={settings:{},translationJobs:{}},resolved=[];
 const storage={read:async()=>structuredClone(db),mutate:async fn=>{const d=structuredClone(db),r=fn(d);db=d;return structuredClone(r);}};
 const jobs=createTranslationJobs({storage,getContent:(_,id)=>({revision:1,blocks:(id==='article:a'?['below','visible']:['background']).map(id=>({id,text:id}))}),resolve:async input=>{resolved.push(input.blockIds[0]);return {blocks:{[input.blockIds[0]]:'Translated'}};}});
 await jobs.enqueue('article:b',['fr']);await jobs.enqueue('article:a',['fr'],{blockIds:['below'],priority:1});await jobs.enqueue('article:a',['fr'],{blockIds:['visible'],priority:0});
 await jobs.tick();await jobs.tick();await jobs.tick();assert.deepEqual(resolved,['visible','below','background']);
});
test.after(async()=>{globalThis.fetch=oldFetch;await fs.rm(dir,{recursive:true,force:true});});
