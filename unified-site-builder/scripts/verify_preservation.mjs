import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const base=process.env.SITE_TEST_ORIGIN,password=process.env.SITE_TEST_PASSWORD;
const {snapshot}=JSON.parse(await readFile(process.argv[2],'utf8'));
let cookie='',csrf='',checks=0;
async function call(path,method='GET',data){const r=await fetch(base+path,{method,headers:{origin:base,'user-agent':'Mozilla/5.0',cookie,'x-csrf-token':csrf,'content-type':'application/json'},...(data?{body:JSON.stringify(data)}:{})});assert.equal(r.status,200,path);checks++;const raw=await r.text();let j;try{j=JSON.parse(raw);}catch{j=raw;}return {r,j,raw};}
const login=await call('/api/v1/session','POST',{username:'admin',password});cookie=login.r.headers.get('set-cookie').split(';')[0];csrf=login.j.data.csrfToken;
assert.equal((await call('/api/v1/admin/products/'+snapshot.productId)).j.data.model,'CHECK-202');
assert.equal((await call('/api/v1/admin/articles/'+snapshot.articleId)).j.data.status,'draft');
assert.equal((await call('/api/v1/admin/inquiries/'+snapshot.inquiryId)).j.data.note,'Validation note');
assert.ok((await call('/api/v1/admin/attachments/'+snapshot.attachmentId)).raw.startsWith('%PDF'));
await call('/media/'+snapshot.mediaId);
assert.equal((await call('/api/v1/admin/settings')).j.data.contact.displayEmail,'validation@example.com');
assert.ok((await call('/?lang=zh')).raw.includes('产品与实用信息'));
const before=(await call('/api/v1/admin/translations')).j.data;
if(before.engine.configured){
 const body={contentId:'product:sample-product',targetLanguage:'es',revision:1,blockIds:['sample-product#summary']};
 const first=(await call('/api/v1/translations/resolve','POST',body)).j.data;assert.equal(first.status,'ready');
 const usage=(await call('/api/v1/admin/translations')).j.data.usage.calls;
 const second=(await call('/api/v1/translations/resolve','POST',body)).j.data;assert.deepEqual(first.blocks,second.blocks);
 assert.equal((await call('/api/v1/admin/translations')).j.data.usage.calls,usage);
 if(process.env.SITE_REQUIRE_EXISTING_CACHE==='1'){assert.ok(before.cachedBlocks>0);assert.equal(usage,before.usage.calls);}
 console.log(JSON.stringify({checks,cached:true,engine:before.engine.provider,usage,semanticQualityVerified:false}));
}else{const r=(await call('/api/v1/translations/resolve','POST',{contentId:'product:sample-product',targetLanguage:'es',revision:1,blockIds:['sample-product#summary']})).j.data;assert.equal(r.status,'unconfigured');console.log(JSON.stringify({checks,engine:'unconfigured',initialChinese:true,dataPreserved:true}));}
await call('/api/v1/session','DELETE');
