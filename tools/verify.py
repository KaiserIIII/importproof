"""Installed package + real CLI acceptance on nonprivate examples. No network or formula evaluation."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=False)
    commands = []

    def run(label, args, expected=0):
        command = [sys.executable, *map(str, args)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=120)
        (out / (label + '.stdout.log')).write_bytes(result.stdout)
        (out / (label + '.stderr.log')).write_bytes(result.stderr)
        commands.append({'label': label, 'command': command, 'exit_code': result.returncode, 'expected': expected})
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n', encoding='utf-8')
        assert result.returncode == expected, (label, result.returncode, result.stderr.decode('utf-8','replace')[-1000:])
        return result

    tests = run('full-tests', ['-m','unittest','discover','-s',ROOT/'tests','-v'])
    import re
    count = int(re.search(rb'Ran (\d+) tests', tests.stderr)[1])
    reports = []
    for label, b, a, policy, expected, verdict in [
        ('strict-loss','before.csv','after-controlled.tsv','strict-policy.json',2,'CONFIRMED_LOSS'),
        ('same','before.csv','before.csv','strict-policy.json',0,'EQUIVALENT'),
        ('sqlite-actual','sqlite-before.csv','sqlite-after.csv',None,2,'CONFIRMED_LOSS'),
        ('xlsx-long-number','two-sheets.xlsx','rounded-controlled.xlsx',None,2,'CONFIRMED_LOSS'),
    ]:
        args=['-m','importproof','compare',ROOT/'examples'/b,ROOT/'examples'/a,'--output',out/label]
        if policy: args += ['--policy',ROOT/'examples'/policy]
        result=run(label,args,expected)
        report=json.loads((out/label/'report.json').read_text(encoding='utf-8'))
        assert report['verdict']==verdict, report['verdict']
        for side,name in [('before',b),('after',a)]:
            assert report['inputs'][side]['sha256']==hashlib.sha256((ROOT/'examples'/name).read_bytes()).hexdigest()
        for finding in report['findings']:
            for side in ['before','after']:
                evidence=finding.get(side)
                if evidence and 'cell' in evidence:
                    assert evidence['row']>=2 and evidence['column_index']>=1
                    assert 'coordinate' in evidence['cell']
        reports.append({'case':label,'verdict':report['verdict'],'summary':report['summary'],'findings':report['findings']})
    invalid=out/'invalid.csv';invalid.write_bytes(b'a\n\xff\n')
    run('invalid',['-m','importproof','compare',invalid,invalid],1)
    assert '中文' in (out/'strict-loss/report.json').read_text(encoding='utf-8')
    result={'status':'PASS','tests':count,'python':sys.version,'platform':platform.platform(),'cli_exits':[0,2,1],
            'unicode':'PASS','hash_and_coordinates':'PASS','reports':reports,
            'scope':'Controlled files, actual installed CLI and real SQLite typed import/export; not a validated office application workflow'}
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='reports'}))


if __name__=='__main__':
    main()
