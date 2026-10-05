"""Portable offline translation contract checks; never executes project code."""
import hashlib,json
from pathlib import Path,PurePosixPath

CORE_VERSION='unified-translation-v2:protected-v3'
CORE_HASHES={'engine': 'c2c056840f50a8e5e264dddf7a364a9df9a0a586202c053a0e5c3c1be05726d4', 'resolver': 'a6a4e9a145a83b504add2a0429ee15fca49d9986f8c1f71b9ad41775e204ed0c', 'quality': 'f44bf1c664dc8a2723001768673c465b543ab688ec85b8cdb9147c10d1f01c2e', 'seed': 'df774c5e7b681cec29c0cca00a34157d241deff3336872f626d943011e7ca11e'}
def inspect_translation(root,contract):
    root=Path(root).resolve();errors=[]
    cfg=contract.get('translationContract')
    if not isinstance(cfg,dict) or cfg.get('version')!=2:
        return ['Missing translationContract version 2; legacy packages need explicit migration']
    if cfg.get('coreVersion')!=CORE_VERSION:errors.append('Unsupported translation core version')
    if cfg.get('languages')!=contract.get('languages'):errors.append('Translation and site language lists differ')
    def read_file(value):
        if not isinstance(value,str) or '\\' in value or ':' in value or PurePosixPath(value).is_absolute() or any(p in ('..','.') for p in value.split('/')):
            raise ValueError('Unsafe translation path')
        p=(root/value).resolve()
        if not p.is_relative_to(root) or not p.is_file():raise ValueError('Missing translation file: '+str(value))
        return p.read_bytes()
    modules=cfg.get('modules',{})
    if not isinstance(modules,dict) or set(modules)!= {'engine','resolver','quality','seed'}:
        errors.append('Translation modules must include engine, resolver, quality and seed')
    else:
        paths=[PurePosixPath(item.get('path','')) for item in modules.values() if isinstance(item,dict)]
        if len(paths)!=4 or len({str(p.parent) for p in paths})!=1 or any(PurePosixPath(modules[name].get('path','')).name!=name+'.mjs' for name in modules):errors.append('Shared core filenames and relative imports must remain compatible')
        for name,item in modules.items():
            try:
                body=read_file(item['path'])
                if hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()!=item.get('sha256') or item.get('sha256')!=CORE_HASHES[name]:errors.append('Translation module fingerprint mismatch: '+name)
            except (ValueError,KeyError,TypeError,OSError) as e:errors.append(str(e))
    try:
        glossary=json.loads(read_file(cfg.get('glossaryPath')))
        if not isinstance(glossary.get('version'),str) or not glossary['version']:errors.append('Glossary version is required')
        entries=glossary.get('entries')
        if not isinstance(entries,list) or not entries:errors.append('Project glossary entries are missing')
        else:
            seen={}
            for entry in entries:
                fields=['source','sourceLanguage','targetLanguage','scope','version']
                if not isinstance(entry,dict) or any(not isinstance(entry.get(k),str) or not entry[k] for k in fields):
                    errors.append('Invalid glossary entry');continue
                if entry.get('mode') not in ('preserve','translate') or entry.get('mode')=='translate' and not entry.get('translation'):
                    errors.append('Invalid glossary translation')
                if entry['targetLanguage'] not in contract['languages']+['*']:errors.append('Unknown glossary target language')
                if entry['sourceLanguage']!=contract.get('sourceLanguage'):errors.append('Glossary source language differs')
                key=(entry['source'],entry['sourceLanguage'],entry['targetLanguage'],entry['scope'])
                value=entry.get('translation') if entry.get('mode')=='translate' else entry['source']
                if key in seen and seen[key]!=value:errors.append('Conflicting glossary entries')
                seen[key]=value
            if not any(e.get('mode')=='translate' for e in entries if isinstance(e,dict)):errors.append('Glossary only protects names; project terminology translations are missing')
        seed=json.loads(read_file(cfg.get('initialChinesePath')))
        if not isinstance(seed,list) or not seed:errors.append('Initial Chinese translations are missing')
        elif any(not isinstance(r,dict) for r in seed):errors.append('Invalid initial Chinese translation record')
        elif any(r.get('targetLanguage')!='zh' or r.get('origin') not in ('seed','manual') or not r.get('translation') or len(r.get('sourceHash',''))!=64 for r in seed if isinstance(r,dict)):
            errors.append('Invalid initial Chinese translation record')
    except (ValueError,KeyError,TypeError,OSError) as e:errors.append(str(e))
    return errors
