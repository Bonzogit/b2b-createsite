// Actual Worker adapter executed against Node SQLite with an emulated Alarm API.
// This verifies storage/recovery logic; it does not claim a Cloudflare deployment.
import test from 'node:test';import assert from 'node:assert/strict';import {DatabaseSync} from 'node:sqlite';import fs from 'node:fs/promises';import path from 'node:path';import os from 'node:os';import {execFileSync} from 'node:child_process';import {pathToFileURL} from 'node:url';
test('Worker SQLite jobs, Alarm continuation and instance restart',async()=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'worker-alarm-test-')),skill=path.resolve(import.meta.dirname,'..');
 execFileSync(process.env.PYTHON_BIN||'python',[path.join(skill,'scripts/create_site.py'),dir,'--runtime','cloudflare-workers']);
 let source=await fs.readFile(path.join(dir,'worker.mjs'),'utf8');source=source.replace("import { DurableObject } from 'cloudflare:workers';","const DurableObject=class{constructor(ctx,env){}};").replace(/from '(\.\/[^']+\.json)'/g,"from '$1' with {type:'json'}");await fs.writeFile(path.join(dir,'worker-test.mjs'),source);
 const {UnifiedSite}=await import(pathToFileURL(path.join(dir,'worker-test.mjs')));let database,alarm=null,calls=0;
 function context(){database=new DatabaseSync(path.join(dir,'storage.sqlite'));return {blockConcurrencyWhile:fn=>fn(),storage:{sql:{exec(query,...values){const stmt=database.prepare(query);values=values.map(v=>v instanceof ArrayBuffer?new Uint8Array(v):v);if(stmt.columns().length)return {toArray:()=>stmt.all(...values)};stmt.run(...values);return {toArray:()=>[]};}},transactionSync(fn){database.exec('BEGIN');try{const result=fn();database.exec('COMMIT');return result;}catch(e){database.exec('ROLLBACK');throw e;}},async getAlarm(){return alarm;},async setAlarm(t){alarm=t;}}};}
 const env={SITE_ADMIN_PASSWORD:crypto.randomUUID(),SITE_ORIGIN:'https://worker.fixture',TRANSLATION_PROVIDER:'hymt',TRANSLATION_API_KEY:'test-only',TRANSLATION_ENDPOINT:'https://translator.invalid/translate',ASSETS:{fetch:async()=>new Response('asset')}};
 const originalFetch=globalThis.fetch;globalThis.fetch=async(_,options)=>{calls++;const data=JSON.parse(options.body);return Response.json({result:(data.to==='zh'?'测试译文。':'Texte traduit.')+(data.text.match(/\[\[B2BT_\d+\]\]/g)||[]).join(' ')});};let site=new UnifiedSite(context(),env),cookie='',csrf='';
 async function request(p,method='GET',input){return site.fetch(new Request(env.SITE_ORIGIN+p,{method,headers:{origin:env.SITE_ORIGIN,cookie,'x-csrf-token':csrf,'content-type':'application/json'},body:input===undefined?undefined:JSON.stringify(input)}));}
 try{
  let r=await request('/api/v1/session','POST',{username:'admin',password:env.SITE_ADMIN_PASSWORD});cookie=r.headers.get('set-cookie').split(';')[0];csrf=(await r.json()).data.csrfToken;
  await request('/api/v1/admin/translation-settings','PUT',{translationTargets:['zh','fr']});r=await request('/api/v1/admin/articles','POST',{title:'Alarm guide',body:'Public source paragraph.'});const a=(await r.json()).data;assert(alarm);await site.alarm();assert.equal(calls,1);
  database.close();site=new UnifiedSite(context(),env);r=await request('/api/v1/admin/translation-jobs');assert.equal(r.status,200);let jobs=(await r.json()).data.items;assert(jobs.some(j=>j.completedCount===1));assert(jobs.every(j=>j.total===2));
  for(let i=0;i<5;i++){alarm=null;await site.alarm();}
  assert.equal(calls,4);jobs=(await(await request('/api/v1/admin/translation-jobs')).json()).data.items;assert(jobs.every(j=>j.status==='completed'));assert.equal((await request('/articles/'+a.slug+'/')).status,404);
  await request('/api/v1/admin/articles/'+a.id+'/publish','POST',{});for(let i=0;i<5;i++)await site.alarm();assert.equal(calls,4);const html=await(await request('/articles/'+a.slug+'/?lang=fr')).text();assert(html.includes('Texte traduit.'));
  database.close();site=new UnifiedSite(context(),env);const after=await(await request('/articles/'+a.slug+'/?lang=fr')).text();assert(after.includes('Texte traduit.'));assert.equal(calls,4);
 }finally{globalThis.fetch=originalFetch;database.close();await fs.rm(dir,{recursive:true,force:true});}
});
