"""Optional real-application evidence runner, not a product/runtime dependency.

Run with the project's Python; --uno-python must be LibreOffice's Python with UNO.
Only the checked-in nonprivate, formula-free fixtures are passed to Calc.
"""
import argparse
import json
from pathlib import Path
import subprocess
import uuid


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--soffice',type=Path,required=True)
    parser.add_argument('--uno-python',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case',choices=['risk-default','risk-text','risk-special','control-default','control-text'])
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1]
    commands=[]
    for name in ['risk-default','risk-text','risk-special','control-default','control-text']:
        if args.case and args.case!=name:continue
        case=out/name;case.mkdir()
        source=root/'examples/real-calc'/('risk-source.csv' if name.startswith('risk-') else 'control-source.csv')
        pipe='importproof_'+uuid.uuid4().hex
        server=[str(args.soffice.resolve()),'-env:UserInstallation='+(case/'profile').as_uri(),
                '--headless','--nologo','--nodefault','--norestore',
                '--accept=pipe,name='+pipe+';urp;StarOffice.ServiceManager']
        worker=[str(args.uno_python.resolve()),str(root/'tools/real_calc_worker.py'),pipe,str(source),str(case),name.rsplit('-',1)[1]]
        with (case/'calc.stdout.log').open('wb') as stdout,(case/'calc.stderr.log').open('wb') as stderr:
            app=subprocess.Popen(server,stdout=stdout,stderr=stderr,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:
                p=subprocess.run(worker,capture_output=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (case/'worker.stdout.log').write_bytes(p.stdout);(case/'worker.stderr.log').write_bytes(p.stderr)
                commands.append({'case':name,'server':server,'worker':worker,'exit_code':p.returncode})
                (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
                if p.returncode:raise RuntimeError('Actual Calc worker failed; inspect '+str(case/'worker.stderr.log'))
                app.wait(timeout=20)
            finally:
                if app.poll() is None:app.terminate();app.wait(timeout=10)
        print(name,'PASS: actual CSV and XLSX exports created',flush=True)
    (out/'summary.json').write_text(json.dumps({'status':'PASS','cases':len(commands),
        'scope':'Real headless Calc process; no interactive GUI or Excel acceptance. ImportProof comparisons are a separate step.'},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
