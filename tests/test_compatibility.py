"""Same controlled byte inputs actually used for csv-diff and daff comparisons."""
import hashlib
import json
from pathlib import Path
import unittest
from importproof.readers import read_document
from importproof.compare import compare_documents


class CompatibilityTests(unittest.TestCase):
    def test_actual_calc_exports_retain_loss_and_normal_control_oracles(self):
        root=Path(__file__).resolve().parents[1]/'examples/real-calc'
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        for item in manifest['files']:
            self.assertEqual(hashlib.sha256((root/item['path']).read_bytes()).hexdigest(),item['sha256'])
        before=read_document((root/'risk-source.csv').read_bytes(),'risk-source.csv')
        default=read_document((root/'risk-default/export.csv').read_bytes(),'export.csv')
        report=compare_documents(before,default,{'keys':['row_id']})
        self.assertEqual(report['verdict'],'CONFIRMED_LOSS')
        self.assertTrue(any(f['code']=='LONG_NUMBER_PRECISION_CHANGE' and f['before']['cell']['raw']=='12345678901234567890'
                            and f['after']['cell']['raw']=='1.23456789012346E+019' for f in report['findings']))
        text=read_document((root/'risk-text/export.csv').read_bytes(),'export.csv')
        strict=compare_documents(before,text,{'keys':['row_id']})
        self.assertEqual(strict['summary']['CONFIRMED_LOSS'],3)
        self.assertTrue(all(f['code']=='EMPTY_NULL_CHANGE' for f in strict['findings']))
        self.assertEqual(compare_documents(before,text,{'keys':['row_id'],'null_tokens':['']})['verdict'],'EQUIVALENT')
        self.assertEqual(compare_documents(before,default,{'keys':['business_id']})['verdict'],'UNKNOWN')
        control=read_document((root/'control-source.csv').read_bytes(),'control.csv')
        csv_control=read_document((root/'control-default/export.csv').read_bytes(),'export.csv')
        xlsx_control=read_document((root/'control-default/export.xlsx').read_bytes(),'export.xlsx')
        self.assertEqual(compare_documents(control,csv_control,{'keys':['row_id']})['verdict'],'EQUIVALENT')
        workbook=compare_documents(control,xlsx_control,{'keys':['row_id']})
        self.assertEqual(workbook['verdict'],'UNKNOWN')
        self.assertEqual(workbook['summary']['CONFIRMED_LOSS'],0)

    def test_frozen_controlled_baseline_oracles(self):
        root=Path(__file__).with_name('compatibility')
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        for item in manifest['files']:
            self.assertEqual(hashlib.sha256((root/item['path']).read_bytes()).hexdigest(),item['sha256'])
        for case,wanted in manifest['cases'].items():
            with self.subTest(case=case):
                before=read_document((root/case/'before.csv').read_bytes(),'before.csv')
                after=read_document((root/case/'after.csv').read_bytes(),'after.csv')
                self.assertEqual(compare_documents(before,after,{'keys':['id']})['verdict'],wanted)


if __name__=='__main__':unittest.main()
