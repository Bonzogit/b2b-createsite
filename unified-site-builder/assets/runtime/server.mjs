import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { initialize, createApplication } from './lib/app.mjs';
const root=path.dirname(fileURLToPath(import.meta.url));
const env=process.env,dataDir=path.resolve(env.DATA_DIR||env.SITE_DATA_DIR||path.join(root,'data')),uploadsDir=path.resolve(env.UPLOADS_DIR||path.join(root,'uploads'));
await fs.mkdir(dataDir,{recursive:true});await fs.mkdir(uploadsDir,{recursive:true});
const dbPath=path.join(dataDir,'site.json');let queue=Promise.resolve();
async function read(){try{return JSON.parse(await fs.readFile(dbPath,'utf8'));}catch(e){if(e.code==='ENOENT')return null;throw e;}}
async function write(value){const temp=dbPath+'.tmp';await fs.writeFile(temp,JSON.stringify(value),{mode:0o600});await fs.rename(temp,dbPath);}
const storage={read:async()=>{await queue;return read();},initialize:value=>{const task=queue.then(async()=>{if(!await read())await write(value);});queue=task.catch(()=>{});return task;},mutate:fn=>{const task=queue.then(async()=>{const d=await read();const result=fn(d);if(result?.then)throw Error('Storage mutation must be synchronous');await write(d);return structuredClone(result);});queue=task.catch(()=>{});return task;},putFile:(id,bytes)=>fs.writeFile(path.join(uploadsDir,id),bytes,{mode:0o600}),getFile:id=>fs.readFile(path.join(uploadsDir,id))};
const seed=JSON.parse(await fs.readFile(path.join(root,'seed/content.json'),'utf8')),authored=JSON.parse(await fs.readFile(path.join(root,'seed/translations.zh.json'),'utf8')),glossary=JSON.parse(await fs.readFile(path.join(root,'config/translation-glossary.json'),'utf8'));
await initialize(storage,seed,env,authored);
const mime={'.html':'text/html;charset=utf-8','.js':'text/javascript;charset=utf-8','.css':'text/css;charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.webp':'image/webp'};
const app=createApplication({storage,env,glossary,release:env.SITE_RELEASE||'1.6.0',asset:async request=>{let name=decodeURIComponent(new URL(request.url).pathname);if(name.endsWith('/'))name+='index.html';const target=path.resolve(root,'public','.'+name);if(!target.startsWith(path.join(root,'public')+path.sep))return new Response('Not found',{status:404});try{return new Response(await fs.readFile(target),{headers:{'content-type':mime[path.extname(target)]||'application/octet-stream','cache-control':name.startsWith('/admin/')?'no-store':'public, max-age=60','x-content-type-options':'nosniff'}});}catch{return new Response('Not found',{status:404});}}});
const server=http.createServer(async(req,res)=>{try{const chunks=[];let size=0;for await(const part of req){size+=part.length;if(size>7*1024*1024){res.writeHead(413);res.end('Too large');return;}chunks.push(part);}const headers=new Headers();for(const [k,v]of Object.entries(req.headers)){if(v&&!['cf-connecting-ip','x-client-ip','x-forwarded-for','x-forwarded-host','x-forwarded-proto'].includes(k))headers.set(k,Array.isArray(v)?v.join(','):v);}headers.set('x-client-ip',req.socket.remoteAddress||'local');const url=(env.SITE_ORIGIN||'http://'+req.headers.host)+(req.url||'/');const request=new Request(url,{method:req.method,headers,...(!['GET','HEAD'].includes(req.method)?{body:Buffer.concat(chunks)}:{})});const response=await app(request);res.writeHead(response.status,Object.fromEntries(response.headers));if(req.method==='HEAD')res.end();else res.end(Buffer.from(await response.arrayBuffer()));}catch{res.writeHead(500);res.end('Request failed');}});
server.listen(Number(env.PORT||3000),env.HOST||'0.0.0.0',()=>console.log('Site ready'));
process.on('SIGTERM',()=>server.close(()=>process.exit(0)));
