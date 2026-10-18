import unittest
from importproof.worker import audit_bytes


class WorkerTests(unittest.TestCase):
    def test_real_csv_to_tsv_with_same_raw_cells(self):
        r = audit_bytes(b'id,value\na,001\n', 'a.csv', b'id\tvalue\na\t001\n', 'b.tsv', {"keys": ["id"]})
        self.assertEqual(r["verdict"], "EQUIVALENT")
        self.assertEqual(len(r["inputs"]["before"]["sha256"]), 64)

    def test_unknown_policy_rejected_without_equality(self):
        with self.assertRaises(ValueError):
            audit_bytes(b'a\nx\n', 'a.csv', b'a\nx\n', 'b.csv', {"unknown_field": True})

    def test_oversized_input_rejected(self):
        with self.assertRaises(ValueError):
            audit_bytes(b'x' * (5*1024*1024+1), 'a.csv', b'a\nx\n', 'b.csv')


if __name__ == '__main__':
    unittest.main()
