"""Bounded local resource probes, with success criteria defined before execution."""
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time
from importproof.worker import audit_bytes


def main():
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
    cases=[]
    for n in (100,2000,10000):
        raw=b'id,value\n'+b''.join(str(i).encode()+b',text\n' for i in range(n))
        cases.append((f'{n}-unique-rows',raw,raw,{'keys':['id']},'EQUIVALENT',3))
    basic=b'id,value\na,hello\n'
    cases.extend([
        ('oversized',b'x'*(5*1024*1024+1),basic,{},'ERROR',1),
        ('dense-cell-cap',b','.join(b'c'+str(i).encode() for i in range(256))+b'\n'+(b','*255+b'\n')*1500,basic,{},'ERROR',1),
        ('overlong-cell',b'id,value\na,'+b'x'*65537+b'\n',basic,{},'ERROR',1),
        ('bad-encoding',b'id,value\na,\xff\n',basic,{},'ERROR',1),
        ('null-byte',b'id,value\na,\0\n',basic,{},'ERROR',1),
        ('formula-like',b'id,value\na,=1+1\n',b'id,value\na,=1+1\n',{'keys':['id']},'UNKNOWN',1),
        ('truncated-findings',b'id,value\n'+b''.join(str(i).encode()+b',a\n' for i in range(2100)),b'id,value\n'+b''.join(str(i).encode()+b',b\n' for i in range(2100)),{'keys':['id']},'UNKNOWN',1),
    ])
    (out/'predeclared.json').write_text(json.dumps([{'case':name,'expected':want,'repeats':repeat} for name,b,a,p,want,repeat in cases],indent=2)+'\n',encoding='utf-8')
    rows=[]
    for name,b,a,p,want,repeat in cases:
        case_dir=out/name;case_dir.mkdir()
        (case_dir/'before.csv').write_bytes(b);(case_dir/'after.csv').write_bytes(a)
        times=[]
        for i in range(repeat):
            start=time.perf_counter();result=None;error=None
            try:
                result=audit_bytes(b,'before.csv',a,'after.csv',p);actual=result['verdict']
            except ValueError as exc:error=str(exc);actual='ERROR'
            times.append(time.perf_counter()-start)
            (case_dir/f'run-{i+1}.json').write_text(json.dumps({'actual':actual,'expected':want,'error':error,'seconds':times[-1],'report':result},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            assert actual==want,(name,actual,want,error)
        rows.append({'case':name,'status':'PASS','actual':actual,'expected':want,'seconds':times,'median_seconds':statistics.median(times),
                     'before_sha256':hashlib.sha256(b).hexdigest(),'after_sha256':hashlib.sha256(a).hexdigest()})
        print(name,'PASS',round(times[-1],3),flush=True)
    summary={'status':'PASS','python':sys.version,'platform':platform.platform(),'cases':rows,
             'scope':'Small bounded resource probes, no throughput SLA or complete hostile-input guarantee; Windows no hard RAM quota'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
