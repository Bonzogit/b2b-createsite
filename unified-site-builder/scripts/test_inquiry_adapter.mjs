import test from 'node:test';
import assert from 'node:assert/strict';
import {createInquirySubmit} from '../assets/runtime/public/assets/inquiry-adapter.js';
const good=()=>Response.json({ok:true,data:{inquiryId:'persisted-1',emailStatus:'failed'}});
test('maps body key and wrapped response without treating email as storage failure',async()=>{
 let sent;const submit=createInquirySubmit({fetcher:async(url,options)=>{sent=options;assert.equal(url,'/api/v1/inquiries');return good();}});
 const result=await submit({name:'Test',email:'test@example.org',message:'Requirement',productId:'p1',website:''},{key:'stable'});
 assert.equal(JSON.parse(sent.body).submissionKey,'stable');assert.equal(JSON.parse(sent.body).productId,'p1');
 assert.deepEqual(result,{id:'persisted-1',status:'saved',emailStatus:'failed'});
});
test('retries preserve caller key',async()=>{
 const keys=[];const submit=createInquirySubmit({fetcher:async(_,o)=>{keys.push(JSON.parse(o.body).submissionKey);return good();}});
 await submit({message:'same'},{key:'stable'});await submit({message:'same'},{key:'stable'});assert.deepEqual(keys,['stable','stable']);
});
test('preserves real attachment using multipart',async()=>{
 const submit=createInquirySubmit({fetcher:async(_,o)=>{assert.ok(o.body instanceof FormData);assert.equal(o.body.get('file').name,'requirements.txt');assert.equal(o.body.get('submissionKey'),'stable');assert.equal(o.headers['Content-Type'],undefined);return good();}});
 await submit({file:new File(['spec'],'requirements.txt')},{key:'stable'});
});
test('rejects HTTP failure and malformed success',async()=>{
 await assert.rejects(createInquirySubmit({fetcher:async()=>Response.json({ok:false,error:{code:'submission_conflict'}},{status:409})})({},{key:'x'}));
 await assert.rejects(createInquirySubmit({fetcher:async()=>Response.json({ok:true,data:{}})})({},{key:'x'}));
});
test('caller cancellation reaches request',async()=>{
 const outer=new AbortController();const submit=createInquirySubmit({fetcher:async(_,o)=>{outer.abort();o.signal.throwIfAborted();}});
 await assert.rejects(submit({},{key:'x',signal:outer.signal}),{name:'AbortError'});
});
test('deadline includes response body',async()=>{
 const submit=createInquirySubmit({timeout:10,fetcher:async(_,o)=>({ok:true,json:()=>new Promise((resolve,reject)=>o.signal.addEventListener('abort',()=>reject(o.signal.reason),{once:true}))})});
 await assert.rejects(submit({},{key:'x'}),/超时/);
});
