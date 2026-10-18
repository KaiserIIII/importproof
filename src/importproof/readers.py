"""Bounded, evidence-preserving CSV/TSV and OOXML readers.

No spreadsheet calculation or network operation is performed. Numeric OOXML
tokens are read from validated XML rather than openpyxl's float conversion.
"""
from __future__ import annotations

import csv
import hashlib
import io
import posixpath
import re
import zipfile
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from pathlib import PurePosixPath

from defusedxml import ElementTree as SafeET
from openpyxl import load_workbook
from openpyxl.styles.numbers import BUILTIN_FORMATS, is_date_format, is_timedelta_format

MAX_FILE = 5 * 1024 * 1024
MAX_EXPANDED = 50 * 1024 * 1024
MAX_PARTS = 1000
MAX_SHEETS = 20
MAX_ROWS = 50000
MAX_COLUMNS = 256
MAX_CELLS = 300000
MAX_TEXT = 65536
MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
DOCREL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKGREL = 'http://schemas.openxmlformats.org/package/2006/relationships'
N = '{' + MAIN + '}'
CELL_REF = re.compile(r'^([A-Z]{1,3})([1-9][0-9]*)$')
NUMBER = re.compile(r'^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?$')


def _issue(code, message, **evidence):
    return {'code': code, 'message': message, **evidence}


def _column(index):
    result = ''
    while index:
        index, rem = divmod(index - 1, 26)
        result = chr(65 + rem) + result
    return result


def _cell(raw, kind, coordinate, **evidence):
    if raw is not None and len(raw) > MAX_TEXT:
        raise ValueError('Cell text exceeds 65536 characters')
    return {'raw': raw, 'kind': kind, 'coordinate': coordinate, **evidence}


def _headers_issues(headers, issues):
    names = [c['raw'] for c in headers]
    for index, cell in enumerate(headers, 1):
        if cell['raw'] in (None, ''):
            issues.append(_issue('EMPTY_HEADER', 'Header has no text; use indexed columns.', column=index, coordinate=cell['coordinate']))
    for name, count in Counter(names).items():
        if name not in (None, '') and count > 1:
            issues.append(_issue('DUPLICATE_HEADER', 'Duplicate header requires indexed columns.', header=name, count=count))


def _options(options):
    if options is None:
        options = {}
    if not isinstance(options, dict) or set(options) - {'encoding', 'delimiter', 'quotechar'}:
        raise ValueError('Input options must contain only encoding, delimiter, quotechar')
    encoding = options.get('encoding', 'auto')
    delimiter = options.get('delimiter', 'auto')
    quote = options.get('quotechar', '"')
    if encoding not in ('auto', 'utf-8', 'utf-8-sig', 'utf-16', 'cp1252', 'gb18030'):
        raise ValueError('Unsupported encoding')
    if delimiter not in ('auto', ',', '\t', ';', '|'):
        raise ValueError('Unsupported delimiter')
    if not isinstance(quote, str) or len(quote) != 1 or quote in '\r\n\x00':
        raise ValueError('quotechar must be one non-newline character')
    if delimiter == quote:
        raise ValueError('Delimiter and quote character must differ')
    return encoding, delimiter, quote


def _read_delimited(data, filename, options):
    encoding, delimiter, quote = _options(options)
    if encoding == 'auto':
        encoding = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    try:
        text = data.decode(encoding, errors='strict')
    except UnicodeError as exc:
        raise ValueError('Input cannot be decoded with the selected encoding') from exc
    if '\x00' in text:
        raise ValueError('NUL characters or BOM-less UTF-16 are unsupported')
    if delimiter == 'auto':
        delimiter = '\t' if filename.lower().endswith('.tsv') else ','
        # Never silently interpret a consistently separated file as one column.
        candidates = []
        for candidate in (',', '\t', ';', '|'):
            try:
                trial = csv.reader(io.StringIO(text, newline=''), delimiter=candidate, quotechar=quote, strict=True)
                widths = [len(row) for _, row in zip(range(100), trial) if row]
                if widths and min(widths) > 1 and len(set(widths)) == 1:
                    candidates.append(candidate)
            except csv.Error:
                pass
        if any(candidate != delimiter for candidate in candidates):
            raise ValueError('Ambiguous delimiter; select delimiter explicitly')
    if delimiter == quote:
        raise ValueError('Delimiter and quote character must differ')
    old_limit = csv.field_size_limit()
    csv.field_size_limit(MAX_TEXT)
    records, issues = [], []
    width = 0
    # csv counts CR/LF records, not Unicode paragraph/line separators.
    physical = re.findall(r'[^\r\n]*(?:\r\n|\r|\n|$)', text)
    try:
        reader = csv.reader(io.StringIO(text, newline=''), delimiter=delimiter, quotechar=quote,
                            quoting=csv.QUOTE_NOTNULL, strict=True)
        previous = 0
        for fields in reader:
            end = reader.line_num
            if len(records) >= MAX_ROWS or len(fields) > MAX_COLUMNS:
                raise ValueError('CSV row or column limit exceeded')
            width = max(width, len(fields))
            # Enforce projected rectangular size BEFORE allocating this row's
            # cell dictionaries or padding earlier ragged rows.
            if (len(records) + 1) * width > MAX_CELLS:
                raise ValueError('Document cell limit exceeded')
            source = {'line_start': previous + 1, 'line_end': end,
                      'raw_record': ''.join(physical[previous:end])}
            if not fields:
                issues.append(_issue('BLANK_RECORD', 'Blank physical CSV record retained.', **source))
            cells = [_cell(value, 'blank' if value is None else ('empty' if value == '' else 'text'),
                           f'{_column(i)}{len(records)+1}') for i, value in enumerate(fields, 1)]
            records.append({'number': len(records) + 1, 'cells': cells, 'source': source})
            previous = end
    except csv.Error as exc:
        raise ValueError('Malformed CSV or oversized cell: ' + str(exc)) from exc
    finally:
        csv.field_size_limit(old_limit)
    width = max((len(r['cells']) for r in records), default=0)
    if len(records) * width > MAX_CELLS:
        raise ValueError('Document cell limit exceeded')
    header_width = len(records[0]['cells']) if records else 0
    for record in records:
        if len(record['cells']) != header_width:
            issues.append(_issue('RAGGED_ROW', 'Record field count differs from header.',
                                 row=record['number'], expected=header_width, actual=len(record['cells']), **record['source']))
        record['cells'].extend(_cell(None, 'missing', f'{_column(i)}{record["number"]}')
                               for i in range(len(record['cells']) + 1, width + 1))
    headers = records[0]['cells'] if records else []
    _headers_issues(headers, issues)
    if not records:
        issues.append(_issue('EMPTY_DOCUMENT', 'No records are present.'))
    return [{'name': 'data', 'headers': headers, 'rows': records[1:], 'issues': issues}], {
        'encoding': encoding, 'delimiter': delimiter, 'quotechar': quote,
        'header_source': records[0]['source'] if records else None,
    }


def _validated_zip(data):
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        infos = archive.infolist()
        if len(infos) > MAX_PARTS or sum(info.file_size for info in infos) > MAX_EXPANDED:
            raise ValueError('Expanded ZIP size or member count limit exceeded')
        parts, roots, seen = {}, {}, set()
        total = 0
        for info in infos:
            name = info.filename
            path = PurePosixPath(name)
            if (name.casefold() in seen or '\\' in name or name.startswith('/') or ':' in name
                    or '..' in path.parts or (info.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError('Unsafe or duplicate ZIP member path')
            seen.add(name.casefold())
            if info.flag_bits & 1 or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise ValueError('Encrypted or unsupported ZIP compression')
            lower = name.lower()
            if ('vba' in lower or 'externallinks/' in lower or lower.endswith(('.bin', '.xlsm', '.xlam'))):
                raise ValueError('Macros, binary parts, or external links are forbidden')
            raw = archive.read(info)
            total += len(raw)
            if total > MAX_EXPANDED:
                raise ValueError('Expanded ZIP size limit exceeded')
            parts[name] = raw
            if lower.endswith(('.xml', '.rels')) or name == '[Content_Types].xml':
                root = SafeET.fromstring(raw, forbid_dtd=True, forbid_entities=True, forbid_external=True)
                roots[name] = root
                relationship_ids = set()
                for node in root.iter():
                    if node.tag.rsplit('}', 1)[-1] == 'Relationship':
                        identifier = node.get('Id')
                        if not identifier or identifier in relationship_ids:
                            raise ValueError('Missing or duplicate relationship ID')
                        relationship_ids.add(identifier)
                    if node.tag.rsplit('}', 1)[-1] == 'Relationship' and (
                            node.get('TargetMode', '').lower() == 'external' or
                            'externallink' in node.get('Type', '').lower() or
                            ':' in node.get('Target', '') or '\\' in node.get('Target', '')):
                        raise ValueError('External relationships are forbidden')
                    if any('macroenabled' in value.lower() or 'vbaproject' in value.lower()
                           for key, value in node.attrib.items() if key == 'ContentType'):
                        raise ValueError('Macro-enabled content types are forbidden')
        archive.close()
        for required in ('[Content_Types].xml', 'xl/workbook.xml', 'xl/_rels/workbook.xml.rels'):
            if required not in roots:
                raise ValueError('Missing required OOXML part: ' + required)
        return roots
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Invalid or unsafe XLSX ZIP/XML') from exc


def _coordinate(value):
    match = CELL_REF.fullmatch(value or '')
    if not match:
        raise ValueError('Missing or invalid XLSX cell coordinate')
    column = 0
    for character in match[1]:
        column = column * 26 + ord(character) - 64
    row = int(match[2])
    if row > MAX_ROWS or column > MAX_COLUMNS:
        raise ValueError('XLSX row or column limit exceeded')
    return row, column


def _string(node):
    # Phonetic guide rPh/t is annotation, not the displayed cell value.
    return ''.join(child.text or '' for child in node.findall(N + 't')) + ''.join(
        text.text or '' for run in node.findall(N + 'r') for text in run.findall(N + 't'))


def _format(workbook, style):
    try:
        identifier = workbook._cell_styles[style].numFmtId
        return (BUILTIN_FORMATS.get(identifier, 'General') if identifier < 164
                else workbook._number_formats[identifier - 164])
    except (IndexError, TypeError) as exc:
        raise ValueError('Invalid XLSX style reference') from exc


def _serial_date(token, workbook, fmt, issues, coordinate):
    """Decode Excel serial using Decimal arithmetic and preserve the stored token."""
    value = Decimal(token)
    if not Decimal('-3652059') <= value <= Decimal('3652059'):
        raise ValueError('XLSX date serial is out of range')
    with localcontext() as context:
        context.prec = max(28, len(token) + 16)
        micros = value * Decimal(86400000000)
    rounded = micros.to_integral_value(rounding=ROUND_HALF_EVEN)
    if rounded != micros:
        issues.append(_issue('DATE_PRECISION', 'Date serial exceeds microsecond resolution.', coordinate=coordinate, stored=token))
    if is_timedelta_format(fmt):
        issues.append(_issue('UNSUPPORTED_DURATION', 'Duration format requires review.', coordinate=coordinate))
        return token
    if workbook.epoch.year == 1899 and Decimal(0) < value < Decimal(60):
        rounded += 86400000000
    if workbook.epoch.year == 1899 and Decimal(60) <= value < Decimal(61):
        issues.append(_issue('EXCEL_LEAP_DAY', 'Excel serial 60 refers to an invalid calendar date.', coordinate=coordinate))
    try:
        converted = workbook.epoch + timedelta(microseconds=int(rounded))
    except (ValueError, OverflowError) as exc:
        raise ValueError('XLSX date serial is out of range') from exc
    return converted.time().isoformat() if Decimal(0) <= value < Decimal(1) else converted.isoformat()


def _xlsx_cell(element, workbook, shared, issues):
    coordinate = element.get('r')
    tagtype = element.get('t', 'n')
    try:
        style = int(element.get('s', '0'))
        if style < 0:
            raise ValueError('Negative style index')
    except ValueError as exc:
        raise ValueError('Invalid XLSX style index') from exc
    fmt = _format(workbook, style)
    values = element.findall(N + 'v')
    formulas = element.findall(N + 'f')
    if len(values) > 1 or len(formulas) > 1:
        raise ValueError('Duplicate cell value or formula')
    stored = values[0].text if values else None
    if stored is not None and len(stored) > MAX_TEXT:
        raise ValueError('Cell stored value exceeds text limit')
    evidence = {'format': fmt, 'style_index': style, 'stored': stored}
    unsupported = [child.tag.rsplit('}', 1)[-1] for child in element if child.tag not in {N+'v', N+'f', N+'is'}]
    extra_attributes = set(element.attrib) - {'r', 's', 't'}
    if unsupported or extra_attributes:
        issues.append(_issue('UNSUPPORTED_CELL_CONSTRUCT', 'Cell metadata is not interpreted.', coordinate=coordinate,
                             constructs=unsupported, attributes={key:element.get(key) for key in sorted(extra_attributes)}))
    if formulas:
        formula = formulas[0]
        raw = '=' + (formula.text or '')
        evidence.update(stored=formula.text or '', cached=stored, formula_attributes=dict(formula.attrib))
        issues.append(_issue('FORMULA', 'Formula is not evaluated; review required.', coordinate=coordinate))
        return _cell(raw, 'formula', coordinate, **evidence)
    if tagtype == 'inlineStr':
        inline = element.find(N + 'is')
        if inline is not None and any(child.tag != N + 't' for child in inline):
            issues.append(_issue('UNSUPPORTED_RICH_TEXT', 'Rich text and phonetic annotations require review.', coordinate=coordinate))
        raw = _string(inline) if inline is not None else ''
        return _cell(raw, 'empty' if raw == '' else 'text', coordinate, **evidence)
    if tagtype == 'str' and values and stored is None:
        return _cell('', 'empty', coordinate, **evidence)
    if stored is None:
        return _cell(None, 'blank', coordinate, **evidence)
    if tagtype == 's':
        try:
            index = int(stored)
            if index < 0:
                raise IndexError
            raw = shared[index]
        except (ValueError, IndexError) as exc:
            raise ValueError('Invalid shared string index') from exc
        return _cell(raw, 'empty' if raw == '' else 'text', coordinate, **evidence)
    if tagtype in ('str', 'e'):
        if tagtype == 'e':
            issues.append(_issue('CELL_ERROR', 'Spreadsheet error cell requires review.', coordinate=coordinate))
        return _cell(stored, 'error' if tagtype == 'e' else 'text', coordinate, **evidence)
    if tagtype == 'b':
        if stored not in ('0', '1'):
            raise ValueError('Invalid XLSX boolean')
        return _cell('true' if stored == '1' else 'false', 'boolean', coordinate, **evidence)
    if tagtype == 'd':
        try:
            datetime.fromisoformat(stored.replace('Z', '+00:00'))
        except ValueError as exc:
            raise ValueError('Invalid ISO date cell') from exc
        return _cell(stored, 'date', coordinate, **evidence)
    if tagtype != 'n':
        issues.append(_issue('UNSUPPORTED_CELL_TYPE', 'Unsupported XLSX cell type retained as text.', coordinate=coordinate, type=tagtype))
        return _cell(stored, 'text', coordinate, **evidence)
    if not NUMBER.fullmatch(stored):
        raise ValueError('Invalid XLSX numeric token')
    try:
        if not Decimal(stored).is_finite():
            raise ValueError('Nonfinite XLSX number')
    except InvalidOperation as exc:
        raise ValueError('Invalid XLSX number') from exc
    if is_date_format(fmt):
        return _cell(_serial_date(stored, workbook, fmt, issues, coordinate), 'date', coordinate, **evidence)
    return _cell(stored, 'number', coordinate, **evidence)


def _read_xlsx(data, options):
    _options(options)
    if options:
        raise ValueError('Text input options are not applicable to XLSX')
    roots = _validated_zip(data)
    sheets = roots['xl/workbook.xml'].find(N + 'sheets')
    if sheets is None or len(sheets) > MAX_SHEETS:
        raise ValueError('Missing sheets or XLSX sheet limit exceeded')
    relationships = {node.get('Id'): node for node in roots['xl/_rels/workbook.xml.rels']}
    shared_root = roots.get('xl/sharedStrings.xml')
    shared = [_string(item) for item in shared_root] if shared_root is not None else []
    shared_rich = shared_root is not None and any(child.tag != N+'t' for item in shared_root for child in item)
    if any(len(value) > MAX_TEXT for value in shared):
        raise ValueError('Shared string exceeds cell text limit')
    workbook = None
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=False, keep_links=False)
        tables, total, seen_names = [], 0, set()
        for sheet in sheets:
            name = sheet.get('name')
            if not name or name in seen_names:
                raise ValueError('Missing or duplicate XLSX sheet name')
            seen_names.add(name)
            relation = relationships.get(sheet.get('{' + DOCREL + '}id'))
            if relation is None:
                raise ValueError('Missing sheet relationship')
            target = relation.get('Target', '')
            part = posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join('xl', target))
            if part not in roots or not relation.get('Type', '').endswith('/worksheet'):
                raise ValueError('Unsupported or missing sheet type')
            root = roots[part]
            issues, cellmap, explicit_rows = [], {}, set()
            if shared_rich:
                issues.append(_issue('UNSUPPORTED_RICH_TEXT', 'Shared-string rich text or annotations require review.'))
            for child in roots['xl/workbook.xml']:
                tag = child.tag.rsplit('}', 1)[-1]
                if tag not in {'sheets', 'workbookPr', 'bookViews', 'fileVersion', 'calcPr'}:
                    issues.append(_issue('UNSUPPORTED_WORKBOOK_CONSTRUCT', 'Workbook construct is not interpreted.', construct=tag))
            unsupported_parts = [part for part in roots if part.startswith(('xl/drawings/', 'xl/charts/', 'xl/comments', 'xl/pivot', 'xl/tables/', 'xl/persons/'))]
            if unsupported_parts:
                issues.append(_issue('UNSUPPORTED_PACKAGE_PART', 'Workbook contains unsupported auxiliary data.', parts=unsupported_parts))
            width = height = 0
            if sheet.get('state', 'visible') != 'visible':
                issues.append(_issue('HIDDEN_SHEET', 'Hidden sheet data is retained.', state=sheet.get('state')))
            for child in root:
                tag = child.tag.rsplit('}', 1)[-1]
                if tag == 'mergeCells':
                    issues.append(_issue('MERGED_CELLS', 'Merged cells are not expanded; review required.', ranges=[item.get('ref') for item in child]))
                elif tag not in {'sheetData', 'dimension', 'sheetViews', 'sheetFormatPr', 'pageMargins', 'sheetPr'}:
                    issues.append(_issue('UNSUPPORTED_SHEET_CONSTRUCT', 'Worksheet construct is not rendered.', construct=tag))
            sheetdata = root.find(N + 'sheetData')
            if sheetdata is None:
                raise ValueError('Worksheet missing sheetData')
            for row in sheetdata:
                try:
                    rownum = int(row.get('r', '0'))
                except ValueError as exc:
                    raise ValueError('Invalid XLSX row number') from exc
                if rownum < 1 or rownum > MAX_ROWS or rownum in explicit_rows:
                    raise ValueError('Invalid, duplicate, or excessive XLSX row')
                explicit_rows.add(rownum)
                height = max(height, rownum)
                if set(row.attrib) - {'r', 'spans'}:
                    issues.append(_issue('UNSUPPORTED_ROW_ATTRIBUTES', 'Row presentation attributes are retained as metadata only.', row=rownum, attributes=dict(row.attrib)))
                for element in row:
                    if element.tag != N + 'c':
                        issues.append(_issue('UNSUPPORTED_ROW_CONSTRUCT', 'Unknown row construct.', row=rownum))
                        continue
                    r, col = _coordinate(element.get('r'))
                    if r != rownum or (r, col) in cellmap:
                        raise ValueError('Duplicate or mismatched XLSX cell coordinate')
                    width = max(width, col)
                    if height * width + total > MAX_CELLS:
                        raise ValueError('Document cell limit exceeded')
                    cellmap[r, col] = _xlsx_cell(element, workbook, shared, issues)
            total += height * width
            if total > MAX_CELLS:
                raise ValueError('Document cell limit exceeded')
            rows = []
            for r in range(1, height + 1):
                cells = [cellmap.get((r, c), _cell(None, 'missing', f'{_column(c)}{r}')) for c in range(1, width + 1)]
                rows.append({'number': r, 'cells': cells, 'source': {'sheet': name, 'row': r, 'explicit': r in explicit_rows}})
                if not any((r, c) in cellmap for c in range(1, width + 1)):
                    issues.append(_issue('BLANK_RECORD', 'Empty or absent worksheet row retained.', row=r))
            headers = rows[0]['cells'] if rows else []
            _headers_issues(headers, issues)
            if not rows:
                issues.append(_issue('EMPTY_DOCUMENT', 'Worksheet contains no rows.'))
            tables.append({'name': name, 'headers': headers, 'rows': rows[1:], 'issues': issues,
                           'metadata': {'state': sheet.get('state', 'visible'), 'part': part}})
        if not tables:
            raise ValueError('Workbook contains no worksheets')
        styles_root = roots.get('xl/styles.xml')
        styles_digest = hashlib.sha256(SafeET.tostring(styles_root)).hexdigest() if styles_root is not None else None
        return tables, {'date_epoch': workbook.epoch.isoformat(), 'formulas_evaluated': False,
                        'styles_sha256': styles_digest}
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Malformed or unsupported XLSX workbook') from exc
    finally:
        if workbook is not None:
            workbook.close()


def read_document(data: bytes, filename: str, options: dict | None = None) -> dict:
    """Read bounded bytes into JSON-compatible evidence; invalid inputs raise ValueError."""
    if not isinstance(data, bytes) or not isinstance(filename, str):
        raise ValueError('Expected bytes and a filename string')
    if len(data) > MAX_FILE:
        raise ValueError('Input exceeds 5 MiB file limit')
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if extension in ('csv', 'tsv'):
        tables, metadata = _read_delimited(data, filename, options)
    elif extension == 'xlsx':
        tables, metadata = _read_xlsx(data, options)
    else:
        raise ValueError('Only .csv, .tsv and .xlsx files are supported')
    return {'format': extension, 'sha256': hashlib.sha256(data).hexdigest(),
            'bytes': len(data), 'metadata': metadata, 'tables': tables}
