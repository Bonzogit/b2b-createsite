// Real shared app and canonical adapter; no provider calls or customer data.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {execFileSync,spawn} from 'node:child_process';
import {createInquirySubmit} from '../assets/runtime/public/assets/inquiry-adapter.js';

test('generated app persists adapter requests, retries, conflict and real file',async()=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'skill-interface-'));
 try{
  execFileSync(process.env.PYTHON_BIN||'python',[fileURLToPath(new URL('./create_site.py',import.meta.url)),dir,'--runtime','node']);
  const {initialize,createApplication}=await import(pathToFileURL(path.join(dir,'lib/app.mjs')));
  let db;const files=new Map();const storage={read:async()=>structuredClone(db),initialize:async d=>{db=structuredClone(d)},mutate:async f=>{const d=structuredClone(db),r=f(d);db=d;return structuredClone(r)},putFile:async(id,bytes)=>files.set(id,bytes)};
  const seed=JSON.parse(await fs.readFile(path.join(dir,'seed/content.json')));const authored=JSON.parse(await fs.readFile(path.join(dir,'seed/translations.zh.json')));
  const env={SITE_ORIGIN:'https://fixture.invalid',SITE_ADMIN_PASSWORD:crypto.randomUUID()};await initialize(storage,seed,env,authored);
  const app=createApplication({storage,env,asset:()=>new Response('asset'),glossary:{version:'fixture',entries:[]}});
  const submit=createInquirySubmit({fetcher:(url,options)=>app(new Request(env.SITE_ORIGIN+url,{...options,headers:{...options.headers,origin:env.SITE_ORIGIN}}))});
  const values={name:'Fixture',email:'test@example.org',message:'A desktop requirement',website:''};
  const a=await submit(values,{key:'fixture-stable-key'}),b=await submit(values,{key:'fixture-stable-key'});
  assert.equal(a.id,b.id);assert.equal(a.status,'saved');assert.equal(a.emailStatus,'unconfigured');assert.equal(db.inquiries.length,1);
  await assert.rejects(submit({...values,message:'Changed requirement'},{key:'fixture-stable-key'}));assert.equal(db.inquiries.length,1);
  const c=await submit({...values,file:new File(['%PDF-fixture attachment'],'requirements.pdf',{type:'application/pdf'})},{key:'fixture-file-key'});assert(c.id);assert.equal(db.inquiries.length,2);assert.equal(files.size,1);
 }finally{await fs.rm(dir,{recursive:true,force:true});}
});

test('Node serves module adapter with JavaScript MIME under nosniff',async()=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'skill-module-'));let child;
 try{
  execFileSync(process.env.PYTHON_BIN||'python',[fileURLToPath(new URL('./create_site.py',import.meta.url)),dir,'--runtime','node']);
  await fs.copyFile(path.join(dir,'public/assets/inquiry-adapter.js'),path.join(dir,'public/assets/module-test.mjs'));
  // Allocate one local listener and obtain its assigned port from the server itself.
  const source=await fs.readFile(path.join(dir,'server.mjs'),'utf8');await fs.writeFile(path.join(dir,'server.mjs'),source.replace("()=>console.log('Site ready')","()=>console.log('PORT:'+server.address().port)"));
  child=spawn(process.execPath,['server.mjs'],{cwd:dir,env:{...process.env,PORT:'0',HOST:'127.0.0.1',SITE_ADMIN_PASSWORD:crypto.randomUUID()},stdio:['ignore','pipe','pipe']});
  const port=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('startup timeout')),10000);child.stdout.on('data',b=>{const m=String(b).match(/PORT:(\d+)/);if(m){clearTimeout(timer);resolve(m[1]);}});child.on('exit',()=>{clearTimeout(timer);reject(Error('server exited'));});});
  for(const name of ['inquiry-adapter.js','module-test.mjs']){const r=await fetch(`http://127.0.0.1:${port}/assets/${name}`);assert.equal(r.status,200);assert.match(r.headers.get('content-type'),/^text\/javascript/);assert.equal(r.headers.get('x-content-type-options'),'nosniff');}
 }finally{if(child){child.kill();await new Promise(resolve=>child.once('exit',resolve));}await fs.rm(dir,{recursive:true,force:true});}
});
