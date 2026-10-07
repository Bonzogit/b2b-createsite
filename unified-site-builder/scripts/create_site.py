#!/usr/bin/env python3
"""Create a runnable backend reference for one explicit deployment target."""
import argparse,json,shutil,hashlib,uuid,subprocess
from pathlib import Path

def create(target,runtime,brand='Reference Workshop'):
    target=Path(target).resolve();skill=Path(__file__).resolve().parents[1]
    if target.exists() and any(target.iterdir()):raise ValueError('Target must be empty; use the original project update flow for upgrades')
    shutil.copytree(skill/'assets/runtime',target,dirs_exist_ok=True)
    if runtime=='node':(target/'worker.mjs').unlink()
    else:(target/'server.mjs').unlink()
    def write(name,value):
        p=target/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    contract=json.loads((skill/'assets/site.contract.json').read_text(encoding='utf-8'));contract.update(runtime=runtime,entry='server.mjs' if runtime=='node' else 'worker.mjs',skillVersion='1.6.6',deploymentProfile='unified-node-v1' if runtime=='node' else 'unified-worker-do-v1');write('site.contract.json',contract)
    for name in ('engine','resolver','quality','seed'):
        p=target/'lib/translation'/f'{name}.mjs';p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(skill/'assets/translation'/f'{name}.mjs',p)
    package={'name':'unified-site','version':'1.0.0','type':'module','scripts':{'start':'node server.mjs'} if runtime=='node' else {},'engines':{'node':'>=22'}}
    write('package.json',package);write('package-lock.json',{'name':'unified-site','version':'1.0.0','lockfileVersion':3,'packages':{'':{'name':'unified-site','version':'1.0.0','engines':{'node':'>=22'}}}})
    if runtime=='node':shutil.copyfile(skill/'assets/deploy.node.json',target/'deploy.json')
    else:write('wrangler.json',{'name':'unified-site','main':'worker.mjs','compatibility_date':'2026-10-05','assets':{'directory':'./public','binding':'ASSETS','run_worker_first':True},'durable_objects':{'bindings':[{'name':'SITE','class_name':'UnifiedSite'}]},'migrations':[{'tag':'v1','new_sqlite_classes':['UnifiedSite']}],'vars':{'SITE_RELEASE':'1.6.6','TRANSLATION_PROVIDER':'hymt'}})
    site_id=uuid.uuid4().hex
    def item(key,title,summary,body,**extra):return {'id':key,'slug':key,'title':title,'summary':summary,'body':body,'status':'published','revision':1,**extra}
    content={'settings':{'siteId':site_id,'brand':brand,'sourceLanguage':'en','languages':['en','zh','es','ar','ru','fr','de','pt'],'displayLanguages':['en','zh','es','ar','ru','fr','de','pt'],'autoTranslateArticles':True,'translationTargets':['zh','es','ar','ru','fr','de','pt'],'publicContext':'Public product information','contact':{'displayEmail':'','whatsappNumber':'','address':''}},'pages':[item('home','Products and practical information','Explore products and send an inquiry.','Our team can discuss your project requirements.')],'products':[item('sample-product','Sample product','Product information for deployment validation.','Contact our team for specifications.',model='DEMO-101')],'articles':[item('sample-guide','Product guide','A published article for deployment validation.','Choose specifications that match your project.')],'categories':[item('sample-category','Products','Product category.','')]}
    write('seed/content.json',content)
    chinese={'home':['产品与实用信息','查看产品并提交询盘。','我们的团队可以与您沟通项目需求。'],'sample-product':['示例产品','用于部署验收的产品信息。','请联系我们了解规格。'],'sample-guide':['产品指南','用于部署验收的已发布文章。','选择符合项目需求的规格。'],'sample-category':['产品','产品分类。']}
    records=[]
    for plural,kind in [('pages','page'),('products','product'),('articles','article'),('categories','category')]:
        for row in content[plural]:
            blocks=[('title',row['title']),('summary',row['summary'])]+[('body'+str(i),v) for i,v in enumerate(row['body'].split('\n\n')) if v]
            for (key,value),translation in zip(blocks,chinese[row['id']]):
                material=json.dumps(['source-v1',value,content['settings']['publicContext']],ensure_ascii=False,separators=(',',':')).encode()
                records.append({'siteId':site_id,'contentId':kind+':'+row['id'],'blockId':row['id']+'#'+key,'sourceLanguage':'en','targetLanguage':'zh','sourceHash':hashlib.sha256(material).hexdigest(),'translation':translation,'origin':'seed'})
    write('seed/translations.zh.json',records)
    write('config/translation-glossary.json',{'version':'reference-1','entries':[{'source':'product','sourceLanguage':'en','targetLanguage':'zh','scope':'global','version':'1','mode':'translate','translation':'产品'}]})
    (target/'public/index.html').write_text('<!doctype html><title>Application-rendered home</title>Home is rendered by the backend.\n',encoding='utf-8')
    docs={'README.zh-CN.md':'可运行的后台参考工程。前台示例用于部署验收；实际客户网站须按业务替换内容、素材与设计。','CONFIGURATION.md':'Node：HOST/PORT、DATA_DIR、UPLOADS_DIR、SITE_ORIGIN、首次 SITE_ADMIN_PASSWORD。Worker：SITE/ASSETS 绑定及首次 SITE_ADMIN_PASSWORD Secret。通知默认关闭；后台翻译页可选择展示语言/默认翻译目标、关闭文章自动翻译；任务随站点数据持久保存，Node启动恢复，Worker使用Alarm；默认 Hy-MT2；部署时在服务器环境或 Worker Secret 配置 TRANSLATION_API_KEY。默认接口 https://43.162.83.155/translation/translate，可用 TRANSLATION_ENDPOINT 覆盖；TRANSLATION_PROVIDER=workers-ai 才启用 AI 绑定，或 openai-compatible 使用其他引擎。密钥不得放进源码、前端或 ZIP。','BACKUP-RESTORE.md':'Node：停止写入后备份 DATA_DIR 与 UPLOADS_DIR，隔离恢复后核验。Worker：使用 Durable Object 的平台备份/时间点恢复；升级保留对象类、对象名 main 与迁移。不得只备份公开页面。','HANDOFF.md':'共享 lib/app.mjs；运行适配分别为 server.mjs 与 worker.mjs。以 site.contract.json 选择一个目标，不用默认开发两份客户网站。文章保存自动翻译默认开启，目标为源语言以外七种；按预算可改为仅中文。一键翻译和展示语言设置在中文后台翻译页；更新保留原DATA_DIR或SITE对象。','TEST-REPORT.md':'此文件初始状态：生成结构待检查，网站运行、邮件、翻译语义和视觉均未验证。按 references/runtime-profiles.md 执行实际验收。'}
    for name,value in docs.items():p=target/'docs'/name;p.parent.mkdir(exist_ok=True);p.write_text(value+'\n',encoding='utf-8')
    return target

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('target');parser.add_argument('--runtime',choices=['node','cloudflare-workers'],required=True);parser.add_argument('--brand',default='Reference Workshop');args=parser.parse_args();print(create(args.target,args.runtime,args.brand))
