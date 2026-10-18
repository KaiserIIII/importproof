"""Same controlled byte inputs actually used for csv-diff and daff comparisons."""
import hashlib
import json
from pathlib import Path
import unittest
from importproof.readers import read_document
from importproof.compare import compare_documents


class CompatibilityTests(unittest.TestCase):
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
