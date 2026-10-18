"""Run with LibreOffice's bundled Python. Actual Calc load/export; no ImportProof code."""
import json
from pathlib import Path
import sys
import time
import uno
from com.sun.star.beans import PropertyValue

pipe, input_file, output_dir, mode = sys.argv[1:]
out=Path(output_dir)

def prop(name,value):
    p=PropertyValue();p.Name=name;p.Value=value;return p

local=uno.getComponentContext()
resolver=local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver',local)
for attempt in range(200):
    try:
        context=resolver.resolve('uno:pipe,name='+pipe+';urp;StarOffice.ComponentContext')
        break
    except Exception:
        if attempt==199:raise
        time.sleep(.1)
desktop=context.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop',context)
props=[prop('Hidden',True),prop('ReadOnly',True),prop('FilterName','Text - txt - csv (StarCalc)'),
       prop('MacroExecutionMode',uno.getConstantByName('com.sun.star.document.MacroExecMode.NEVER_EXECUTE')),
       prop('UpdateDocMode',uno.getConstantByName('com.sun.star.document.UpdateDocMode.NO_UPDATE'))]
options=None
if mode=='text':
    options='44,34,76,1,'+'/'.join(str(i)+'/2' for i in range(1,11))+',1033,false,false,true,false,false,0,false,false,false'
elif mode=='special':
    options='44,34,76,1,,1033,false,true,true,false,false,0,false,false,true'
elif mode!='default':raise ValueError(mode)
if options is not None:props.append(prop('FilterOptions',options))
doc=None
try:
    doc=desktop.loadComponentFromURL(uno.systemPathToFileUrl(str(Path(input_file).resolve())),'_blank',0,tuple(props))
    if doc is None:raise RuntimeError('Calc returned no document')
    sheets=doc.getSheets()
    sheet=sheets.getByIndex(0)
    cursor=sheet.createCursor();cursor.gotoEndOfUsedArea(True)
    area=cursor.getRangeAddress()
    if area.EndRow>100 or area.EndColumn>30:raise RuntimeError('Unexpected used range')
    observed=[]
    for r in range(area.EndRow+1):
        row=[]
        for c in range(area.EndColumn+1):
            cell=sheet.getCellByPosition(c,r)
            kind=cell.getType().value
            fmt=doc.getNumberFormats().getByKey(cell.NumberFormat)
            row.append({'row':r+1,'column':c+1,'type':kind,'string':cell.getString(),
                        'value_repr':repr(cell.getValue()) if kind=='VALUE' else None,
                        'formula':cell.getFormula(),'number_format':fmt.FormatString})
        observed.append(row)
    actual={p.Name:p.Value for p in doc.getArgs() if p.Name in ('FilterName','FilterOptions','ReadOnly','Hidden') and isinstance(p.Value,(str,int,bool,float))}
    export_options='44,34,76,1,,1033,false,true,true,false,false,0,false,false'
    metadata={'mode':mode,'requested_filter_options':options,'actual_document_args':actual,
              'sheet_names':list(sheets.getElementNames()),'rows':area.EndRow+1,'columns':area.EndColumn+1,
              'macro_execution':'NEVER_EXECUTE','update_document':'NO_UPDATE','headless':True,
              'csv_export_filter_options':export_options,'cells':observed}
    (out/'cells-before-export.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    doc.storeToURL(uno.systemPathToFileUrl(str((out/'export.xlsx').resolve())),
                   (prop('FilterName','Calc MS Excel 2007 XML'),prop('Overwrite',False)))
    doc.storeToURL(uno.systemPathToFileUrl(str((out/'export.csv').resolve())),
                   (prop('FilterName','Text - txt - csv (StarCalc)'),prop('FilterOptions',export_options),prop('Overwrite',False)))
    metadata['status']='PASS'
    (out/'conversion.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','mode':mode,'rows':metadata['rows'],'columns':metadata['columns']}))
finally:
    if doc is not None:doc.close(True)
    desktop.terminate()
