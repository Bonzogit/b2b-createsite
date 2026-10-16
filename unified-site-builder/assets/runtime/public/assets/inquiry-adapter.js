// Optional adapter; credentials and storage stay in the existing site backend.
export function createInquirySubmit({endpoint='/api/v1/inquiries',fetcher=fetch,timeout=20000}={}) {
  return async function submit(values,{signal,key}={}) {
    if(!key)throw new Error('Missing stable submission key');
    const controller=new AbortController();
    const cancel=()=>controller.abort(signal?.reason);
    if(signal?.aborted)cancel();else signal?.addEventListener('abort',cancel,{once:true});
    const timer=setTimeout(()=>controller.abort(new DOMException('Request timed out','TimeoutError')),timeout);
    try {
      const data={...values,submissionKey:key};
      const hasFile=Object.values(data).some(value=>typeof File!=='undefined'&&value instanceof File&&value.size>0);
      let body,headers={};
      if(hasFile){body=new FormData();for(const [name,value]of Object.entries(data))body.append(name,value??'');}
      else {delete data.file;body=JSON.stringify(data);headers={'Content-Type':'application/json'};}
      const response=await fetcher(endpoint,{method:'POST',credentials:'same-origin',headers,body,signal:controller.signal});
      const payload=await response.json();
      if(!response.ok||!payload?.ok){const error=new Error('需求未确认保存，请保留内容后重试');error.code=payload?.error?.code||'INQUIRY_FAILED';throw error;}
      if(typeof payload.data?.inquiryId!=='string'||!payload.data.inquiryId)throw new Error('服务未返回保存编号');
      return {id:payload.data.inquiryId,status:'saved',emailStatus:payload.data.emailStatus};
    } catch(error) {
      if(controller.signal.aborted){if(signal?.aborted)throw new DOMException('操作已取消','AbortError');throw new Error('提交超时；请保留内容并使用同一提交编号重试');}
      throw error;
    } finally {clearTimeout(timer);signal?.removeEventListener('abort',cancel);}
  };
}
