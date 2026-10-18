"""Real byte-parser tests; OOXML fixtures are authored here, without private files."""
import io
import json
import unittest
import zipfile
from xml.sax.saxutils import escape

try:
    from importproof.readers import read_document
except ImportError:
    read_document = None


NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'


def xlsx(sheets=None, extras=None, workbook_extra='', styles=None):
    """Small valid OOXML ZIP, with exact lexical values controlled by each test."""
    sheets = sheets or [('Data', '<row r="1"><c r="A1" t="inlineStr"><is><t>id</t></is></c></row><row r="2"><c r="A2"><v>1</v></c></row>')]
    content = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    content += ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(sheets)+1))
    if styles:
        content += '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    members = {
        '[Content_Types].xml': content + '</Types>',
        '_rels/.rels': f'<Relationships xmlns="{REL}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': f'<workbook xmlns="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' + ''.join(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i, (name, _) in enumerate(sheets, 1)) + '</sheets>' + workbook_extra + '</workbook>',
        'xl/_rels/workbook.xml.rels': f'<Relationships xmlns="{REL}">' + ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(sheets)+1)) + (f'<Relationship Id="styles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' if styles else '') + '</Relationships>',
    }
    for i, (_, body) in enumerate(sheets, 1):
        members[f'xl/worksheets/sheet{i}.xml'] = f'<worksheet xmlns="{NS}"><sheetData>{body}</sheetData></worksheet>'
    if styles:
        members['xl/styles.xml'] = styles
    members.update(extras or {})
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, body in members.items():
            archive.writestr(name, body)
    return result.getvalue()


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(read_document), 'read_document implementation is missing')

    def table(self, data, name='input.csv', options=None):
        document = read_document(data, name, options)
        json.dumps(document, allow_nan=False)
        self.assertEqual(document['bytes'], len(data))
        self.assertEqual(len(document['sha256']), 64)
        return document['tables'][0]

    def test_csv_preserves_text_quoted_empty_blank_and_missing(self):
        table = self.table(b'id,blank,empty,absent\r\n0001,,""\r\n')
        self.assertEqual([(c['kind'], c['raw']) for c in table['rows'][0]['cells']], [('text', '0001'), ('blank', None), ('empty', ''), ('missing', None)])
        self.assertIn('RAGGED_ROW', {i['code'] for i in table['issues']})

    def test_csv_physical_line_spans_and_blank_record_are_retained(self):
        table = self.table(b'a,b\n"two\nlines",x\n\nz,y\n')
        self.assertEqual(len(table['rows']), 3)
        self.assertEqual(table['rows'][0]['source']['line_start'], 2)
        self.assertEqual(table['rows'][0]['source']['line_end'], 3)
        self.assertEqual(table['rows'][1]['source']['line_start'], 4)
        self.assertIn('BLANK_RECORD', {i['code'] for i in table['issues']})

    def test_csv_unicode_line_separator_is_not_a_physical_newline(self):
        table = self.table('a,b\nx\u2028y,z\nlast,row\n'.encode())
        self.assertEqual(table['rows'][0]['source']['raw_record'], 'x\u2028y,z\n')
        self.assertEqual(table['rows'][1]['source']['raw_record'], 'last,row\n')

    def test_duplicate_empty_headers_and_extra_columns_surface(self):
        table = self.table(b'a,a,\n1,2,3,4\n')
        codes = {i['code'] for i in table['issues']}
        self.assertTrue({'DUPLICATE_HEADER', 'EMPTY_HEADER', 'RAGGED_ROW'} <= codes)
        self.assertEqual(len(table['headers']), 4)
        self.assertEqual(table['headers'][3]['kind'], 'missing')

    def test_supported_encodings_tsv_and_explicit_delimiter(self):
        for data, name, opts in [(b'\xef\xbb\xbfid,v\n1,caf\xc3\xa9\n', 'a.csv', None), ('id,v\n1,café\n'.encode('utf-16'), 'a.csv', None), ('id,v\n1,café\n'.encode('cp1252'), 'a.csv', {'encoding':'cp1252'}), ('id,v\n1,中文\n'.encode('gb18030'), 'a.csv', {'encoding':'gb18030'})]:
            with self.subTest(opts=opts):
                self.assertIn(self.table(data, name, opts)['rows'][0]['cells'][1]['raw'], ['café','中文'])
        self.assertEqual(self.table(b'id\tv\n1\t02\n', 'a.tsv')['rows'][0]['cells'][1]['raw'], '02')
        self.assertEqual(self.table(b'id;v\n1;2\n', options={'delimiter':';'})['rows'][0]['cells'][1]['raw'], '2')

    def test_decode_delimiter_quote_and_option_failures_reject(self):
        for data, opts in [(b'a\n\xff\n', None), (b'a;b\n1;2\n', None), (b'a,b\n"unfinished', None), (b'a\n1', {'encoding':'latin1'}), (b'a\n1', {'delimiter':'xx'}), (b'a\n1', {'unknown':True}), (b'a\n1', {'quotechar':''})]:
            with self.subTest(data=data, opts=opts), self.assertRaises(ValueError):
                read_document(data, 'a.csv', opts)

    def test_csv_bounded_size_width_height_and_cell_text(self):
        for data in [b'a' * (5*1024*1024+1), (','.join(['a']*257)).encode(), b'a\n' + b'1\n'*50001, b'a\n' + b'x'*65537]:
            with self.subTest(length=len(data)), self.assertRaises(ValueError):
                read_document(data, 'a.csv')

    def test_xlsx_exact_numeric_text_and_all_sheets(self):
        body = '<row r="1"><c r="A1" t="inlineStr"><is><t>value</t></is></c></row><row r="2"><c r="A2"><v>12345678901234567890.0100</v></c></row>'
        doc = read_document(xlsx([('One', body), ('Two', body)]), 'a.xlsx')
        self.assertEqual([t['name'] for t in doc['tables']], ['One','Two'])
        cell = doc['tables'][0]['rows'][0]['cells'][0]
        self.assertEqual(cell['raw'], '12345678901234567890.0100')
        self.assertEqual(cell['stored'], '12345678901234567890.0100')
        self.assertEqual(cell['kind'], 'number')
        self.assertEqual(cell['coordinate'], 'A2')

    def test_xlsx_preserves_blank_inlineempty_missing_formula_boolean_and_error(self):
        headers = ''.join(f'<c r="{c}1" t="inlineStr"><is><t>{c}</t></is></c>' for c in 'ABCDEF')
        body = f'<row r="1">{headers}</row><row r="2"><c r="A2"/><c r="B2" t="inlineStr"><is><t/></is></c><c r="D2"><f>1+1</f><v>2</v></c><c r="E2" t="b"><v>1</v></c><c r="F2" t="e"><v>#DIV/0!</v></c></row>'
        table = self.table(xlsx([('Data',body)]), 'a.xlsx')
        self.assertEqual([c['kind'] for c in table['rows'][0]['cells']], ['blank','empty','missing','formula','boolean','error'])
        self.assertEqual(table['rows'][0]['cells'][3]['raw'], '=1+1')
        self.assertIn('FORMULA', {i['code'] for i in table['issues']})

    def test_xlsx_styles_dates_hidden_and_merged_are_evidence(self):
        styles = f'<styleSheet xmlns="{NS}"><numFmts count="1"><numFmt numFmtId="164" formatCode="yyyy-mm-dd"/></numFmts><fonts count="1"><font/></fonts><fills count="1"><fill><patternFill/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="164"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'
        body = '<row r="1"><c r="A1" t="inlineStr"><is><t>date</t></is></c></row><row r="2" hidden="1"><c r="A2" s="1"><v>45292</v></c></row>'
        data = xlsx([('Data',body)], styles=styles)
        table = self.table(data, 'a.xlsx')
        cell = table['rows'][0]['cells'][0]
        self.assertEqual(cell['raw'], '2024-01-01T00:00:00')
        self.assertEqual(cell['stored'], '45292')
        self.assertEqual(cell['format'], 'yyyy-mm-dd')
        self.assertEqual(len(read_document(data, 'a.xlsx')['metadata']['styles_sha256']), 64)
        self.assertIn('UNSUPPORTED_ROW_ATTRIBUTES', {i['code'] for i in table['issues']})
        root = f'<worksheet xmlns="{NS}"><sheetData>{body}</sheetData><mergeCells count="1"><mergeCell ref="A1:B1"/></mergeCells></worksheet>'
        table = self.table(xlsx(extras={'xl/worksheets/sheet1.xml':root}, styles=styles), 'a.xlsx')
        self.assertIn('MERGED_CELLS', {i['code'] for i in table['issues']})

    def test_xlsx_zip_xml_macro_external_security_rejection(self):
        bad = [b'not a zip', xlsx(extras={'../escape.xml':'<a/>'}), xlsx(extras={'xl/vbaProject.bin':b'vba'}), xlsx(extras={'evil.xml':'<!DOCTYPE a [<!ENTITY x "boom">]><a>&x;</a>'}), xlsx(extras={'evil.xml':'<broken>'}), xlsx(extras={'xl/externalLinks/externalLink1.xml':'<a/>'}), xlsx(extras={'evil.rels': f'<Relationships xmlns="{REL}"><Relationship Id="x" TargetMode="External" Target="https://example.invalid/"/></Relationships>'})]
        for data in bad:
            with self.subTest(length=len(data)), self.assertRaises(ValueError):
                read_document(data, 'a.xlsx')
        with self.assertRaises(ValueError):
            read_document(xlsx(), 'a.xlsm')

    def test_xlsx_rejects_excessive_sheet_cell_coordinates_and_expansion(self):
        for data in [xlsx([('S'+str(i), '') for i in range(21)]), xlsx([('Data','<row r="50001"><c r="A50001"><v>1</v></c></row>')]), xlsx([('Data','<row r="1"><c r="IW1"><v>1</v></c></row>')]), xlsx(extras={'big.xml':'<x>'+(' '* (50*1024*1024))+'</x>'})]:
            with self.subTest(length=len(data)), self.assertRaises(ValueError):
                read_document(data, 'a.xlsx')

    def test_xlsx_duplicate_members_reject(self):
        stream = io.BytesIO(xlsx())
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(stream, 'a') as archive:
                archive.writestr('xl/workbook.xml', '<a/>')
        with self.assertRaises(ValueError):
            read_document(stream.getvalue(), 'a.xlsx')

    def test_xlsx_rich_text_excludes_phonetic_annotation_from_value(self):
        body = '<row r="1"><c r="A1" t="inlineStr"><is><t>name</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><r><t>東京</t></r><rPh sb="0" eb="2"><t>とうきょう</t></rPh></is></c></row>'
        table = self.table(xlsx([('Data',body)]), 'a.xlsx')
        self.assertEqual(table['rows'][0]['cells'][0]['raw'], '東京')
        self.assertIn('UNSUPPORTED_RICH_TEXT', {i['code'] for i in table['issues']})

    def test_xlsx_defined_names_and_unknown_cell_markup_require_review(self):
        body = '<row r="1"><c r="A1" t="inlineStr"><is><t>id</t></is></c></row><row r="2"><c r="A2" cm="1"><v>1</v><extLst/></c></row>'
        table = self.table(xlsx([('Data',body)], workbook_extra='<definedNames><definedName name="Set">Data!$A$1:$A$2</definedName></definedNames>'), 'a.xlsx')
        codes = {i['code'] for i in table['issues']}
        self.assertTrue({'UNSUPPORTED_WORKBOOK_CONSTRUCT','UNSUPPORTED_CELL_CONSTRUCT'} <= codes)

    def test_xlsx_encrypted_zip_flag_and_member_count_reject(self):
        data = bytearray(xlsx())
        start = 0
        while (start := data.find(b'PK\x01\x02', start)) != -1:
            data[start+8] |= 1
            start += 4
        with self.assertRaises(ValueError):
            read_document(bytes(data), 'a.xlsx')
        with self.assertRaises(ValueError):
            read_document(xlsx(extras={f'extra/{i}.xml':'<a/>' for i in range(1000)}), 'a.xlsx')

    def test_xlsx_dense_materialization_enforces_document_cell_limit(self):
        body = '<row r="1"><c r="IV1"><v>1</v></c></row><row r="1172"><c r="A1172"><v>1</v></c></row>'
        with self.assertRaises(ValueError):
            read_document(xlsx([('Data',body)]), 'a.xlsx')

    def test_xlsx_duplicate_relationship_ids_reject(self):
        rels = f'<Relationships xmlns="{REL}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
        with self.assertRaises(ValueError):
            read_document(xlsx(extras={'xl/_rels/workbook.xml.rels':rels}), 'a.xlsx')

    def test_xlsx_shared_string_keeps_zeroes_and_empty(self):
        body = '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="inlineStr"><is><t>empty</t></is></c></row><row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2" t="s"><v>2</v></c></row>'
        shared = f'<sst xmlns="{NS}" count="3" uniqueCount="3"><si><t>code</t></si><si><t>00001</t></si><si><t/></si></sst>'
        table = self.table(xlsx([('Data',body)], extras={'xl/sharedStrings.xml':shared}), 'a.xlsx')
        self.assertEqual([(c['raw'],c['kind']) for c in table['rows'][0]['cells']], [('00001','text'),('','empty')])

    def test_xlsx_typed_empty_string_is_not_blank(self):
        body = '<row r="1"><c r="A1" t="inlineStr"><is><t>value</t></is></c></row><row r="2"><c r="A2" t="str"><v/></c></row>'
        self.assertEqual(self.table(xlsx([('Data',body)]), 'a.xlsx')['rows'][0]['cells'][0]['kind'], 'empty')

    def test_xlsx_oversized_formula_cache_is_rejected(self):
        body = '<row r="1"><c r="A1"><f>1+1</f><v>' + ('x'*65537) + '</v></c></row>'
        with self.assertRaises(ValueError):
            read_document(xlsx([('Data',body)]), 'a.xlsx')

    def test_empty_document_keeps_table_and_issue(self):
        table = self.table(b'')
        self.assertEqual(table['rows'], [])
        self.assertIn('EMPTY_DOCUMENT', {i['code'] for i in table['issues']})

    def test_csv_cell_limit_is_enforced_before_materializing_excess_cells(self):
        # A lowered public limit exercises the same allocation boundary with a
        # small input; wraps counts real constructed cells without replacing them.
        import importproof.readers as readers
        from unittest.mock import patch
        with patch.object(readers, 'MAX_CELLS', 4), patch.object(readers, '_cell', wraps=readers._cell) as cells:
            with self.assertRaisesRegex(ValueError, 'cell limit'):
                read_document(b'a,b\nx,y\nz,w\n', 'a.csv')
            self.assertLessEqual(cells.call_count, 4)


if __name__ == '__main__':
    unittest.main()
