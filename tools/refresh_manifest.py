#!/usr/bin/env python3
"""Refresh or verify the release manifest from a maintained Git checkout."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args()
 version=(ROOT/'VERSION').read_text(encoding='utf-8').strip();skill=(ROOT/'unified-site-builder/SKILL.md').read_text(encoding='utf-8');match=re.search(r'^\s*version:\s*["\']?([0-9.]+)',skill,re.M)
 if not match or match.group(1)!=version:raise SystemExit('VERSION and Skill metadata differ')
 names=sorted(set(subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()))
 old=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'));new={k:v for k,v in old.items() if k not in ('version','files')};new={'version':version,**new,'files':[{'path':n,'sha256':hashlib.sha256((ROOT/n).read_bytes()).hexdigest()} for n in names if n!='manifest.json' and (ROOT/n).is_file()]}
 if args.check:
  if old!=new:raise SystemExit('release manifest is stale')
  print('manifest verified: '+version+' / '+str(len(new['files']))+' files')
 else:(ROOT/'manifest.json').write_text(json.dumps(new,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('manifest refreshed: '+version+' / '+str(len(new['files']))+' files')
if __name__=='__main__':main()
