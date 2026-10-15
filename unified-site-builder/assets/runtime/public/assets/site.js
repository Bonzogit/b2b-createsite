// Bound both response headers and JSON body reads. A network stall must not lock UI.
async function requestJSON(url,options={},timeoutMs=8000){
 const controller=new AbortController(),parent=options.signal;let timer,onAbort;
 const cancelled=new Promise((_,reject)=>{
  const fail=name=>{const error=new Error(name);error.name=name;controller.abort();reject(error);};
  onAbort=()=>fail('AbortError');
  if(parent?.aborted){onAbort();return;}
  parent?.addEventListener('abort',onAbort,{once:true});
  timer=setTimeout(()=>fail('TimeoutError'),timeoutMs);
 });
 try{return await Promise.race([(async()=>{if(parent?.aborted){const e=new Error('aborted');e.name='AbortError';throw e;}const response=await fetch(url,{...options,signal:controller.signal});if(!response.ok)throw Error('unavailable');return response.json();})(),cancelled]);}
 finally{clearTimeout(timer);parent?.removeEventListener('abort',onAbort);}
}
document.querySelector('#language')?.addEventListener('change',e=>{const u=new URL(location.href);u.searchParams.set('lang',e.target.value);location.assign(u);});
const lang=document.documentElement.lang;
const messages={en:['Translating…','Some translations are unavailable. Original text is shown.','Retry'],zh:['正在翻译…','部分内容暂时无法翻译，已保留原文。','重试'],es:['Traduciendo…','Algunas traducciones no están disponibles. Se muestra el original.','Reintentar'],ar:['جارٍ الترجمة…','بعض الترجمات غير متاحة. يظهر النص الأصلي.','إعادة المحاولة'],ru:['Перевод…','Некоторые переводы недоступны. Показан оригинал.','Повторить'],fr:['Traduction…','Certaines traductions sont indisponibles. Le texte original est affiché.','Réessayer'],de:['Übersetzung…','Einige Übersetzungen sind nicht verfügbar. Der Originaltext wird angezeigt.','Erneut versuchen'],pt:['Traduzindo…','Algumas traduções estão indisponíveis. O original é exibido.','Tentar novamente']};
const words=messages[lang]||messages.en,state=document.querySelector('#translation-state'),retry=document.querySelector('#translation-retry');
let abort=new AbortController();addEventListener('pagehide',()=>abort.abort());
addEventListener('pageshow',event=>{if(event.persisted){abort=new AbortController();running=false;translate();}});
let running=false;
async function translate(retrying=false){
 if(running||lang==='en'||abort.signal.aborted)return;const nodes=[...document.querySelectorAll('[data-translation-block]')];if(!nodes.length){if(state)state.hidden=true;return;}running=true;let failed=false;const deadline=performance.now()+30000;
 if(state){state.hidden=false;state.querySelector('span').textContent=words[0];retry.hidden=true;}
 const groups=new Map();for(const node of nodes){const rect=node.getBoundingClientRect(),priority=rect.top<innerHeight&&rect.bottom>=0&&!node.closest('[hidden]')?0:1;const key=node.dataset.contentId+'|'+priority;if(!groups.has(key))groups.set(key,{contentId:node.dataset.contentId,revision:Number(node.dataset.revision),nodes:[],priority});groups.get(key).nodes.push(node);}
 const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 await Promise.all([...groups.values()].map(async group=>{
  let pending=group.nodes;
  try{for(let poll=0;pending.length&&poll<120;poll++){
   if(abort.signal.aborted)return;if(performance.now()>=deadline)break;
   const blockIds=[...new Set(pending.map(n=>n.dataset.translationBlock))];
   const response=await requestJSON('/api/v1/translations/resolve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({contentId:group.contentId,revision:group.revision,targetLanguage:lang,blockIds,priority:group.priority,...(retrying&&poll===0?{retry:true}:{})}),signal:abort.signal},Math.max(1,Math.min(8000,deadline-performance.now())));
   if(!response.ok)throw Error('unavailable');const data=response.data;
   for(const node of pending){const id=node.dataset.translationBlock;if(Object.hasOwn(data.blocks||{},id)){node.textContent=data.blocks[id];delete node.dataset.translationBlock;}}
   pending=pending.filter(n=>n.dataset.translationBlock);if(!pending.length)break;
   if(!data.retryAfterMs)throw Error('unavailable');await delay(Math.min(Math.max(1000,Math.min(5000,data.retryAfterMs)),Math.max(0,deadline-performance.now())));
  }if(pending.length)failed=true;
  }catch(e){if(e.name!=='AbortError')failed=true;}
 }));running=false;if(abort.signal.aborted||!state)return;if(failed){state.querySelector('span').textContent=words[1];retry.textContent=words[2];retry.hidden=false;}else state.hidden=true;
}
retry?.addEventListener('click',()=>translate(true));translate();
document.querySelector('#inquiry')?.addEventListener('submit',async e=>{e.preventDefault();const form=e.target,button=form.querySelector('button');button.disabled=true;form.setAttribute('aria-busy','true');const data=new FormData(form);data.set('submissionKey',form.dataset.key||(form.dataset.key=crypto.randomUUID()));try{const j=await requestJSON('/api/v1/inquiries',{method:'POST',body:data,signal:abort.signal},20000);if(!j.ok)throw Error('unavailable');document.querySelector('#result').textContent=(document.querySelector('#inquiry-saved')?.textContent||'Inquiry saved. Reference:')+' '+j.data.inquiryId;form.reset();delete form.dataset.key;}catch(error){if(error.name==='AbortError')return;document.querySelector('#result').textContent=document.querySelector('#inquiry-failed')?.textContent||'Unable to submit. Please try again.';}finally{button.disabled=false;form.removeAttribute('aria-busy');}});
