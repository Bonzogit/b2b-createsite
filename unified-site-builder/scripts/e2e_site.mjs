// Destructive only to deliberately created validation fixtures, never a customer site.
import assert from 'node:assert/strict';
const base=process.env.SITE_TEST_ORIGIN,password=process.env.SITE_TEST_PASSWORD;
if(!base||!password||process.env.SITE_E2E_ALLOW_WRITE!=='1')throw Error('An isolated fixture origin, password and write opt-in are required');
let cookie='',csrf='',count=0;
function check(value,message){assert.ok(value,message);count++;}
async function call(path,{method='GET',data,auth=true,expected=200,origin=base,token=csrf}={}){
 const headers={origin,'user-agent':'Mozilla/5.0',...(auth&&cookie?{cookie}:{}),...(auth&&token?{'x-csrf-token':token}:{})};
 if(data!==undefined&&!(data instanceof FormData))headers['content-type']='application/json';
 const response=await fetch(base+path,{method,headers,body:data===undefined?undefined:data instanceof FormData?data:JSON.stringify(data)});
 check(response.status===expected,path+' expected '+expected+' received '+response.status);
 const raw=await response.text();let result;try{result=JSON.parse(raw);}catch{result=raw;}
 return {response,result,raw};
}
async function login(){const {response,result}=await call('/api/v1/session',{method:'POST',data:{username:'admin',password},auth:false});cookie=response.headers.get('set-cookie').split(';')[0];csrf=result.data.csrfToken;check(!!csrf,'csrf token');}
for(let i=0;i<50;i++){try{const r=await fetch(base+'/healthz');if(r.ok)break;}catch{}if(i===49)throw Error('Fixture did not start');await new Promise(r=>setTimeout(r,100));}
const nonce=Date.now().toString(36);
await call('/healthz');await call('/admin/');await call('/api/v1/admin/overview',{auth:false,expected:401});await login();
await call('/api/v1/admin/settings',{method:'PUT',data:{brand:'Forbidden'},origin:'https://invalid.example',expected:403});
await call('/api/v1/admin/settings',{method:'PUT',data:{brand:'Forbidden'},token:'invalid',expected:403});
await call('/api/v1/admin/settings',{method:'PUT',data:{contact:{displayEmail:'validation@example.com',whatsappNumber:'+12025550123',address:'Validation address'}}});
const home=(await call('/')).raw;const protectedEmail=home.match(/data-cfemail="([a-f0-9]+)"/);let decoded='';if(protectedEmail){const bytes=Buffer.from(protectedEmail[1],'hex');decoded=String.fromCharCode(...[...bytes.subarray(1)].map(v=>v^bytes[0]));}check(home.includes('validation@example.com')||decoded==='validation@example.com','central contact reflected');
check((await call('/')).raw.includes('https://wa.me/12025550123'),'WhatsApp reflected');
const zh=(await call('/?lang=zh')).raw;check(zh.includes('产品与实用信息'),'initial Chinese without AI');check(zh.includes('lang="zh"'),'Chinese HTML language');
const product=(await call('/api/v1/admin/products',{method:'POST',data:{title:'Validation product '+nonce,body:'A product specification.',model:'CHECK-202',summary:'Validation product summary'}})).result.data;
await call('/api/v1/products/'+product.slug,{auth:false,expected:404});
await call('/api/v1/admin/products/'+product.id+'/publish',{method:'POST',data:{}});
check((await call('/products/'+product.slug+'/')).raw.includes('Validation product'),'published product HTML');
const article=(await call('/api/v1/admin/articles',{method:'POST',data:{title:'Validation article '+nonce,summary:'Article summary',body:'Safe article body <script>alert(1)</script>'}})).result.data;
await call('/api/v1/articles/'+article.slug,{auth:false,expected:404});
check((await call('/api/v1/admin/preview/articles/'+article.id)).raw.includes(article.title),'authenticated draft preview');
await call('/api/v1/admin/articles/'+article.id+'/publish',{method:'POST',data:{}});
const publicHtml=(await call('/articles/'+article.slug+'/')).raw;check(publicHtml.includes('&lt;script&gt;'),'stored content escaped');check(!publicHtml.includes('<script>alert(1)'),'stored script not executable');
check((await call('/articles/')).raw.includes(article.title),'article list publication');
check((await call('/sitemap.xml')).raw.includes('/articles/'+article.slug+'/'),'sitemap publication');
const png=Uint8Array.from(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j4l0AAAAASUVORK5CYII=','base64'));
const form=new FormData();form.set('file',new Blob([png],{type:'image/png'}),'validation.png');const media=(await call('/api/v1/admin/media',{method:'POST',data:form})).result.data;
await call(media.url,{auth:false});
const inquiryForm=new FormData();for(const [k,v]of Object.entries({name:'Validation contact',email:'validation@example.com',message:'Deployment validation inquiry',submissionKey:'e2e-'+nonce}))inquiryForm.set(k,v);
inquiryForm.set('file',new Blob(['%PDF-1.4\nValidation fixture'],{type:'application/pdf'}),'validation.pdf');
const inquiry=(await call('/api/v1/inquiries',{method:'POST',data:inquiryForm,auth:false})).result.data;check(inquiry.emailStatus==='unconfigured','inquiry saved without email');
const repeated=(await call('/api/v1/inquiries',{method:'POST',data:inquiryForm,auth:false})).result.data;check(repeated.inquiryId===inquiry.inquiryId,'idempotent inquiry');
inquiryForm.set('message','Changed message');await call('/api/v1/inquiries',{method:'POST',data:inquiryForm,auth:false,expected:409});
const row=(await call('/api/v1/admin/inquiries/'+inquiry.inquiryId)).result.data;check(row.attachments.length===1,'attachment metadata persistent');
await call('/api/v1/admin/attachments/'+row.attachments[0].id,{auth:false,expected:401});
check((await call('/api/v1/admin/attachments/'+row.attachments[0].id)).raw.startsWith('%PDF'),'authorized private attachment');
await call('/media/'+row.attachments[0].id,{auth:false,expected:404});
await call('/api/v1/admin/inquiries/'+inquiry.inquiryId,{method:'PATCH',data:{note:'Validation note',inquiryStatus:'contacted'}});
check((await call('/api/v1/admin/inquiries/'+inquiry.inquiryId)).result.data.note==='Validation note','inquiry follow-up');
check((await call('/api/v1/admin/inquiries/export')).raw.includes('Validation note'),'inquiry CSV export');
await call('/api/v1/admin/email-settings',{method:'PUT',data:{enabled:false,from:'validation@example.com',recipients:['validation@example.com']}});
check(!(await call('/api/v1/admin/email-settings')).raw.includes('apiKey"'),'existing secret not returned');
const source=(await call('/api/v1/admin/articles/'+article.id)).result.data;
await call('/api/v1/admin/translations',{method:'POST',data:{contentId:'article:'+article.id,blockId:article.id+'#title',targetLanguage:'zh',translation:'人工审核标题'}});
const translated=(await call('/api/v1/translations/resolve',{method:'POST',data:{contentId:'article:'+article.id,revision:source.revision,targetLanguage:'zh',blockIds:[article.id+'#title']},auth:false})).result.data;
check(translated.blocks[article.id+'#title']==='人工审核标题','manual translation precedence');
await call('/api/v1/translations/resolve',{method:'POST',data:{contentId:'article:'+article.id,targetLanguage:'zh',blockIds:['unknown']},auth:false,expected:400});
await call('/api/v1/admin/articles/'+article.id,{method:'PATCH',data:{revision:source.revision,title:'Updated title '+nonce}});
const stale=(await call('/api/v1/translations/resolve',{method:'POST',data:{contentId:'article:'+article.id,revision:source.revision,targetLanguage:'zh'},auth:false})).result.data;
check(stale.reasonCode==='stale_revision','stale source translation rejected');
await call('/api/v1/admin/articles/'+article.id,{method:'PATCH',data:{revision:source.revision,title:'Conflict'},expected:409});
await call('/api/v1/admin/articles/'+article.id+'/unpublish',{method:'POST',data:{}});
await call('/articles/'+article.slug+'/',{auth:false,expected:404});
check(!(await call('/sitemap.xml')).raw.includes('/articles/'+article.slug+'/'),'unpublished sitemap removed');
await call('/api/v1/translations/resolve',{method:'POST',data:{contentId:'article:'+article.id,targetLanguage:'zh'},auth:false,expected:404});
const snapshot={productId:product.id,articleId:article.id,inquiryId:row.id,attachmentId:row.attachments[0].id,mediaId:media.id};
console.log(JSON.stringify({passed:count,snapshot,emailSent:false,semanticQualityVerified:false}));
await call('/api/v1/session',{method:'DELETE'});
