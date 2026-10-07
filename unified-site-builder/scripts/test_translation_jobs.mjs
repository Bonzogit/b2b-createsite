// Isolated in-memory integration with a deterministic provider; no production writes.
import test from 'node:test';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';import fs from 'node:fs/promises';import path from 'node:path';import os from 'node:os';import {execFileSync} from 'node:child_process';
const skill=path.resolve(import.meta.dirname,'..'),fixture=await fs.mkdtemp(path.join(os.tmpdir(),'skill-translation-jobs-'));
execFileSync(process.env.PYTHON_BIN||'python',[path.join(skill,'scripts/create_site.py'),fixture,'--runtime','node']);
const {initialize,createApplication}=await import(pathToFileURL(path.join(fixture,'lib/app.mjs')));
const {sourceHash}=await import(pathToFileURL(path.join(fixture,'lib/translation/seed.mjs')));
const {createTranslationJobs}=await import(pathToFileURL(path.join(fixture,'lib/translation-jobs.mjs')));
let state=null,calls=0,wakes=[],failProvider=false,changeDuringCall=null;
const storage={async read(){return structuredClone(state);},async initialize(v){state=structuredClone(v);},async mutate(fn){const next=structuredClone(state),out=fn(next);state=next;return structuredClone(out);}};
const seed=JSON.parse(await fs.readFile(path.join(fixture,'seed/content.json'),'utf8')),authored=JSON.parse(await fs.readFile(path.join(fixture,'seed/translations.zh.json'),'utf8'));
const env={SITE_ADMIN_PASSWORD:crypto.randomUUID(),SITE_ORIGIN:'https://fixture.test',TRANSLATION_PROVIDER:'hymt',TRANSLATION_API_KEY:'isolated-test-key',TRANSLATION_ENDPOINT:'https://translator.invalid/translate'};
await initialize(storage,seed,env,authored);
const originalFetch=globalThis.fetch;globalThis.fetch=async(url,options)=>{assert.equal(url,env.TRANSLATION_ENDPOINT);assert.equal(options.redirect,'manual');calls++;const data=JSON.parse(options.body);if(changeDuringCall){const fn=changeDuringCall;changeDuringCall=null;await fn();}if(failProvider)return new Response('{}',{status:503});const words={zh:'这是测试译文。',es:'Texto traducido.',ar:'نص مترجم.',ru:'Переведённый текст.',fr:'Texte traduit.',de:'Übersetzter Text.',pt:'Texto traduzido.'};return Response.json({result:words[data.to]+(data.text.match(/\[\[B2BT_\d+\]\]/g)||[]).join(' ')});};
const appOptions={storage,env,glossary:{version:'1',entries:[]},scheduleTranslation:async t=>wakes.push(t),asset:async()=>new Response('asset')};let app=createApplication(appOptions),cookie='',csrf='';
async function request(p,method='GET',input,auth=true){const r=await app(new Request(env.SITE_ORIGIN+p,{method,headers:{origin:env.SITE_ORIGIN,...(auth?{cookie,'x-csrf-token':csrf}:{}),'content-type':'application/json'},body:input===undefined?undefined:JSON.stringify(input)}));return {status:r.status,headers:r.headers,data:r.headers.get('content-type')?.includes('application/json')?await r.json():await r.text()};}
async function drain(){for(let i=0;i<300;i++){const active=Object.values(state.translationJobs||{}).some(j=>['queued','running'].includes(j.status));if(!active)return;await app.translationJobs.tick();}throw Error('Queue did not drain');}
test('administrator workflows, private drafts, cache reuse and visibility',async()=>{
 let r=await request('/api/v1/session','POST',{username:'admin',password:env.SITE_ADMIN_PASSWORD},false);cookie=r.headers.get('set-cookie').split(';')[0];csrf=r.data.data.csrfToken;
 assert.equal((await request('/api/v1/admin/translation-jobs','GET',undefined,false)).status,401);
 assert.equal((await request('/api/v1/admin/translation-settings','PUT',{displayLanguages:['zh']})).status,400);
 assert.equal((await request('/api/v1/admin/translation-settings','PUT',{translationTargets:['unknown']})).status,400);
 assert.equal((await request('/api/v1/admin/translation-settings','PUT',{displayLanguages:['en','zh'],translationTargets:['zh','fr'],autoTranslateArticles:true})).status,200);
 r=await request('/api/v1/admin/articles','POST',{title:'New guide',summary:'A summary.',body:'First paragraph.\n\nSecond paragraph.'});const a=r.data.data,cid='article:'+a.id;
 assert.equal(a.status,'draft');assert.equal(Object.values(state.translationJobs).length,2);assert(wakes.length);
 assert.equal((await request('/articles/'+a.slug+'/')).status,404);
 assert.equal((await request('/api/v1/translations/resolve','POST',{contentId:cid,targetLanguage:'zh',revision:a.revision},false)).status,404);
 await drain();assert.equal(calls,8);assert(Object.values(state.translationJobs).every(j=>j.status==='completed'));assert.equal(Object.keys(state.cache).length,8);
 // A private, hidden target can be prepared before its front-end option is enabled.
 assert.equal((await request('/api/v1/translations/resolve','POST',{contentId:cid,targetLanguage:'fr'},false)).status,400);
 const before=calls;await request('/api/v1/admin/articles/'+a.id+'/publish','POST',{});await drain();assert.equal(calls,before);
 assert(!(await request('/articles/'+a.slug+'/?lang=fr')).data.includes('lang="fr"'));
 await request('/api/v1/admin/translation-settings','PUT',{displayLanguages:['en','zh','fr']});assert((await request('/articles/'+a.slug+'/?lang=fr')).data.includes('Texte traduit.'));assert.equal(calls,before);
 const current=state.articles.find(v=>v.id===a.id);await request('/api/v1/admin/articles/'+a.id,'PATCH',{revision:current.revision,body:'Changed paragraph.\n\nSecond paragraph.'});await drain();assert.equal(calls,before+2);
 // Manual correction is reused by a one-click job without replacing it.
 await request('/api/v1/admin/translations','POST',{contentId:cid,blockId:a.id+'#body0',targetLanguage:'fr',translation:'Correction humaine.'});
 await request('/api/v1/admin/translation-jobs','POST',{contentId:cid,targetLanguages:['fr']});await drain();assert.equal(calls,before+2);assert((await request('/articles/'+a.slug+'/?lang=fr')).data.includes('Correction humaine.'));
 await request('/api/v1/admin/translation-jobs','POST',{contentId:cid,targetLanguages:['es','ar','ru','de','pt']});app=createApplication(appOptions);await drain();assert.equal(calls,before+22);
 assert(Object.values(state.translationJobs).every(j=>j.status==='completed'));
 const c=state.articles.find(v=>v.id===a.id);await request('/api/v1/admin/articles/'+a.id,'PATCH',{revision:c.revision,title:'Another guide'});
 await request('/api/v1/admin/articles/'+a.id+'/unpublish','POST',{});assert(Object.values(state.translationJobs).filter(j=>j.revision===c.revision+1).every(j=>j.status==='cancelled'));assert.equal((await request('/articles/'+a.slug+'/')).status,404);
 const d=state.articles.find(v=>v.id===a.id);await request('/api/v1/admin/articles/'+a.id,'PATCH',{revision:d.revision,body:'Newest paragraph.'});const job=Object.values(state.translationJobs).find(j=>j.contentId===cid&&j.status==='queued');
 const beforeStale=calls;changeDuringCall=async()=>storage.mutate(db=>{const row=db.articles.find(v=>v.id===a.id);row.body='A replacement paragraph.';row.revision++;});await app.translationJobs.tick();assert.equal(state.translationJobs[job.id].status,'cancelled');assert.equal(calls,beforeStale+1);
 const staleTitleHash=await sourceHash('Another guide',state.settings.publicContext);assert(!Object.keys(state.cache).some(k=>{const parts=JSON.parse(k);return parts[2]===a.id+'#title'&&parts[5]===staleTitleHash;}));
 await request('/api/v1/admin/translation-settings','PUT',{autoTranslateArticles:false});const count=Object.keys(state.translationJobs).length;await request('/api/v1/admin/articles','POST',{title:'Disabled automatic translation',body:'A draft.'});assert.equal(Object.keys(state.translationJobs).length,count);
});
test('retries, expired lease recovery, quota scheduling and single-flight coordination',async()=>{
 let t=Date.now(),db={settings:{},translationJobs:{}},resolved=0,mode='failure',nextTime=0;
 const st={async read(){return structuredClone(db);},async mutate(fn){const copy=structuredClone(db),out=fn(copy);db=copy;return structuredClone(out);}};
 const content={revision:1,blocks:[{id:'b',text:'Original'}]},jobs=createTranslationJobs({storage:st,getContent:()=>content,clock:()=>t,schedule:async x=>{nextTime=x;},resolve:async()=>{resolved++;return mode==='ok'?{blocks:{b:'Translation'}}:{blocks:{},reasonCode:mode==='quota'?'quota_exceeded':'provider_error'};}});
 const [j]=await jobs.enqueue('article:a',['zh']);await jobs.tick();assert.equal(db.translationJobs[j.id].status,'retrying');assert.equal(resolved,1);t=nextTime;await jobs.tick();t=nextTime;await jobs.tick();assert.equal(db.translationJobs[j.id].status,'failed');
 mode='quota';const [q]=await jobs.retry(j.id);await jobs.tick();assert.equal(db.translationJobs[q.id].status,'waiting_quota');assert(nextTime>t);
 t=nextTime;mode='ok';await jobs.tick();assert.equal(db.translationJobs[q.id].status,'completed');
 const [lease]=await jobs.enqueue('article:a',['zh']);db.translationJobs[lease.id].status='running';db.translationJobs[lease.id].leaseUntil=t+120000;const before=resolved;await jobs.tick();assert.equal(resolved,before);assert.equal(nextTime,t+120000);t+=120001;await jobs.tick();assert.equal(db.translationJobs[lease.id].status,'completed');
 const duplicates=await jobs.enqueue('article:a',['fr']);const again=await jobs.enqueue('article:a',['fr']);assert.equal(duplicates[0].id,again[0].id);
});
process.on('exit',()=>{globalThis.fetch=originalFetch;});
test.after(async()=>fs.rm(fixture,{recursive:true,force:true}));
