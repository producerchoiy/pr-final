from __future__ import annotations

from html import escape
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile


CONTENT_COLUMNS = [
    ("upload_date", "업로드일"),
    ("title", "제목"),
    ("professor", "출연 교수"),
    ("department", "진료과"),
    ("content_type", "콘텐츠 유형"),
    ("platform", "플랫폼"),
    ("url", "URL"),
    ("memo", "메모"),
    ("task_id", "업무 ID"),
]


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _cell(reference: str, value: object, style: int = 0) -> str:
    safe = escape("" if value is None else str(value), quote=False)
    style_attr = f' s="{style}"' if style else ""
    return f'<c r="{reference}" t="inlineStr"{style_attr}><is><t xml:space="preserve">{safe}</t></is></c>'


def content_records_excel(records: list[dict]) -> bytes:
    """Create a dependency-free XLSX file suitable for the hospital result sheet."""
    rows = [[label for _, label in CONTENT_COLUMNS]]
    rows.extend([[record.get(key, "") for key, _ in CONTENT_COLUMNS] for record in records])
    row_xml: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells = "".join(
            _cell(f"{_column_name(column_index)}{row_index}", value, 1 if row_index == 1 else 2)
            for column_index, value in enumerate(row, start=1)
        )
        row_xml.append(f'<row r="{row_index}">{cells}</row>')

    sheet = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <cols>
    <col min="1" max="1" width="13" customWidth="1"/><col min="2" max="2" width="34" customWidth="1"/>
    <col min="3" max="4" width="16" customWidth="1"/><col min="5" max="6" width="15" customWidth="1"/>
    <col min="7" max="7" width="38" customWidth="1"/><col min="8" max="8" width="30" customWidth="1"/>
    <col min="9" max="9" width="26" customWidth="1"/>
  </cols>
  <sheetData>{''.join(row_xml)}</sheetData>
  <autoFilter ref="A1:I{max(1, len(rows))}"/>
</worksheet>'''

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
    workbook = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="YouTube 콘텐츠 기록" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''
    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2"><font><sz val="11"/><name val="맑은 고딕"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="맑은 고딕"/></font></fonts>
  <fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF176F73"/><bgColor indexed="64"/></patternFill></fill></fills>
  <borders count="2"><border/><border><left style="thin"><color rgb="FFD8E8E5"/></left><right style="thin"><color rgb="FFD8E8E5"/></right><top style="thin"><color rgb="FFD8E8E5"/></top><bottom style="thin"><color rgb="FFD8E8E5"/></bottom></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''

    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/styles.xml", styles)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return output.getvalue()
