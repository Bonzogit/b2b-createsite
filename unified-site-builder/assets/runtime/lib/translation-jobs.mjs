// Persistent per-language jobs. No timers or provider credentials in this module.
export const supportedLanguages=['en','zh','es','ar','ru','fr','de','pt'];
export function languageSelection(values,{source='en',allowSource=true}={}) {
 if(!Array.isArray(values)||!values.length||values.some(v=>!supportedLanguages.includes(v)))throw Object.assign(Error('invalid_languages'),{status:400});
 const out=[...new Set(values)];if(!allowSource&&out.includes(source))throw Object.assign(Error('source_language_not_target'),{status:400});return out;
}
export function translationSettings(db) {
 const source=db.settings.sourceLanguage||'en';
 return {displayLanguages:db.settings.displayLanguages||db.settings.languages||supportedLanguages,
  autoTranslateArticles:db.settings.autoTranslateArticles??true,
  translationTargets:db.settings.translationTargets||supportedLanguages.filter(v=>v!==source)};
}
const active=j=>['queued','running','waiting_quota','retrying'].includes(j.status);
const stamp=()=>new Date().toISOString();
export function createTranslationJobs({storage,getContent,resolve,schedule=async()=>{},clock=Date.now}) {
 async function wake(){const db=await storage.read(),jobs=Object.values(db.translationJobs||{}).filter(active),running=jobs.filter(j=>j.status==='running'&&j.leaseUntil>clock());const times=(running.length?running:jobs).map(j=>j.status==='running'?j.leaseUntil:j.nextRunAt||clock());if(times.length)await schedule(Math.max(clock()+100,Math.min(...times)));}
 async function enqueue(contentId,targets){
  const db=await storage.read();targets=languageSelection(targets,{source:db.settings.sourceLanguage||'en',allowSource:false});
  const content=getContent(db,contentId);if(!content)throw Object.assign(Error('content_not_found'),{status:404});
  const result=await storage.mutate(d=>enqueueInto(d,contentId,targets));await wake();return result;
 }
 function enqueueInto(db,contentId,targets){
  const content=getContent(db,contentId);if(!content)throw Object.assign(Error('content_not_found'),{status:404});
  db.translationJobs||={};
  for(const j of Object.values(db.translationJobs))if(j.contentId===contentId&&j.revision!==content.revision&&active(j)){j.status='cancelled';j.reasonCode='stale_revision';j.updatedAt=stamp();}
  return targets.map(targetLanguage=>{
   const existing=Object.values(db.translationJobs).find(j=>j.contentId===contentId&&j.targetLanguage===targetLanguage&&j.revision===content.revision&&active(j));if(existing)return existing;
   const j={id:crypto.randomUUID(),contentId,revision:content.revision,targetLanguage,blockIds:content.blocks.map(b=>b.id),completed:[],total:content.blocks.length,status:content.blocks.length?'queued':'completed',reasonCode:null,attempts:0,nextRunAt:clock(),createdAt:stamp(),updatedAt:stamp()};db.translationJobs[j.id]=j;return j;
  });
 }
 function cancelInto(db,contentId){for(const j of Object.values(db.translationJobs||{}))if(j.contentId===contentId&&active(j)){j.status='cancelled';j.reasonCode='content_unpublished';j.updatedAt=stamp();}}
 async function tick(){
  const token=crypto.randomUUID(),t=clock();
  const job=await storage.mutate(db=>{
   db.translationJobs||={};
   // One engine call per site. Expired leases recover after process/instance restart.
   if(Object.values(db.translationJobs).some(j=>j.status==='running'&&j.leaseUntil>t))return null;
   const j=Object.values(db.translationJobs).filter(j=>active(j)&&(j.status==='running'?j.leaseUntil<=t:j.nextRunAt<=t)).sort((a,b)=>(a.nextRunAt||0)-(b.nextRunAt||0))[0];if(!j)return null;
   const c=getContent(db,j.contentId);if(!c||c.revision!==j.revision){j.status='cancelled';j.reasonCode='stale_revision';return null;}
   j.status='running';j.leaseToken=token;j.leaseUntil=t+120000;j.updatedAt=stamp();return j;
  });
  if(!job){await wake();return;}
  const blockId=job.blockIds.find(v=>!job.completed.includes(v));let result;
  try{result=await resolve({contentId:job.contentId,revision:job.revision,targetLanguage:job.targetLanguage,blockIds:[blockId]});}
  catch(e){result={blocks:{},reasonCode:['content_not_found','stale_revision'].includes(e.message)?e.message:'provider_error'};}
  await storage.mutate(db=>{
   const j=db.translationJobs[job.id],c=getContent(db,job.contentId);if(!j||j.status!=='running'||j.leaseToken!==token)return;
   delete j.leaseToken;delete j.leaseUntil;j.updatedAt=stamp();
   if(!c||c.revision!==job.revision){j.status='cancelled';j.reasonCode='stale_revision';return;}
   if(Object.hasOwn(result.blocks||{},blockId)){
    j.completed.push(blockId);j.attempts=0;j.reasonCode=null;j.status=j.completed.length===j.total?'completed':'queued';j.nextRunAt=clock();return;
   }
   const code=result.reasonCode||'provider_error';j.reasonCode=code;
   if(code==='stale_revision'||code==='content_not_found'){j.status='cancelled';return;}
   if(code==='quota_exceeded'){j.status='waiting_quota';j.nextRunAt=Date.parse(new Date(clock()).toISOString().slice(0,10))+86400000+1000;return;}
   if(result.status==='pending'){j.status='retrying';j.nextRunAt=clock()+5000;return;}
   if(['unconfigured','unauthorized','unsupported_direction','unsupported_model','placeholder_mismatch','invalid_engine_output'].includes(code)){j.status='failed';return;}
   if(++j.attempts>=3){j.status='failed';return;}j.status='retrying';j.nextRunAt=clock()+30000*2**(j.attempts-1);
  });
  await wake();
 }
 async function retry(jobId){const jobs=await storage.mutate(db=>{const old=db.translationJobs?.[jobId];if(!old)throw Object.assign(Error('not_found'),{status:404});return enqueueInto(db,old.contentId,[old.targetLanguage]);});await wake();return jobs;}
 return {enqueue,enqueueInto,cancelInto,tick,wake,retry};
}
