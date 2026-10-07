"""Install the shared core into a project without replacing its glossary or translations."""
import argparse,hashlib,json,shutil
from pathlib import Path

def install(project):
    project=Path(project).resolve();assets=Path(__file__).resolve().parents[1]/'assets/translation'
    path=project/'site.contract.json';contract=json.loads(path.read_text(encoding='utf-8'))
    cfg=json.loads((assets/'core-manifest.json').read_text(encoding='utf-8'))
    cfg['languages']=contract['languages']
    for name,item in cfg['modules'].items():
        target=project/item['path'];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(assets/(name+'.mjs'),target)
        item['sha256']=hashlib.sha256(target.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    glossary=project/cfg['glossaryPath'];glossary.parent.mkdir(parents=True,exist_ok=True)
    if not glossary.exists():glossary.write_text(json.dumps({'version':'1','reviewStatus':'unreviewed','entries':[]},indent=2),encoding='utf-8')
    contract['skillVersion']='1.6.5';contract['translationContract']=cfg
    path.write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'coreInstalled':True,'runtimeConnected':False,'glossaryPath':cfg['glossaryPath'],
      'initialChinesePath':cfg['initialChinesePath'],'next':'Implement persistent repository, generate glossary and Chinese records, then run real site acceptance'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('project',type=Path)
    print(json.dumps(install(parser.parse_args().project),ensure_ascii=False))
