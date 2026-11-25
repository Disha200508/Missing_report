import re
import os
import shutil
import zipfile
import markdown
import pymupdf

def clean_mermaid_for_doc(text):
    """Formats mermaid code blocks into styled architecture flow boxes."""
    def repl(match):
        code = match.group(1).strip()
        # Clean up arrows and formatting for readable display
        lines = code.split("\n")
        flow_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith("flowchart") or line.startswith("graph") or line.startswith("erDiagram") or line.startswith("subgraph"):
                continue
            if line == "end":
                continue
            flow_lines.append(line)
        content = "\n".join(flow_lines)
        return f'<div class="diagram-box"><strong>System Architecture Flow:</strong><pre>{content}</pre></div>'
    
    return re.sub(r'```mermaid\s*(.*?)```', repl, text, flags=re.DOTALL)

def md_to_html(md_path):
    with open(md_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Pre-process mermaid blocks
    processed_text = clean_mermaid_for_doc(raw_text)

    # Convert markdown to HTML
    html_body = markdown.markdown(
        processed_text,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"]
    )
    return html_body

def build_pdf(html_body, output_path):
    css = """
    @page {
        size: a4 portrait;
        margin: 20mm 15mm 20mm 15mm;
    }
    body {
        font-family: Helvetica, Arial, sans-serif;
        font-size: 10pt;
        line-height: 1.5;
        color: #1e293b;
    }
    h1 {
        font-size: 20pt;
        color: #0f172a;
        border-bottom: 2px solid #2563eb;
        padding-bottom: 4px;
        margin-top: 10px;
        margin-bottom: 6px;
    }
    h2 {
        font-size: 14pt;
        color: #1e3a8a;
        border-bottom: 1px solid #cbd5e1;
        padding-bottom: 3px;
        margin-top: 16px;
        margin-bottom: 8px;
    }
    h3 {
        font-size: 11pt;
        color: #1e40af;
        margin-top: 12px;
        margin-bottom: 4px;
    }
    p {
        margin-top: 4px;
        margin-bottom: 6px;
    }
    ul, ol {
        margin-top: 4px;
        margin-bottom: 6px;
        padding-left: 20px;
    }
    li {
        margin-bottom: 3px;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin-top: 8px;
        margin-bottom: 12px;
        font-size: 9pt;
    }
    th, td {
        border: 1px solid #94a3b8;
        padding: 6px 8px;
        text-align: left;
        vertical-align: top;
    }
    th {
        background-color: #f1f5f9;
        color: #0f172a;
        font-weight: bold;
    }
    tr:nth-child(even) td {
        background-color: #f8fafc;
    }
    pre {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 4px;
        padding: 8px;
        font-family: Courier, monospace;
        font-size: 8.5pt;
        overflow-x: auto;
        margin-top: 6px;
        margin-bottom: 8px;
        line-height: 1.35;
    }
    code {
        font-family: Courier, monospace;
        font-size: 8.5pt;
        background-color: #f1f5f9;
        padding: 1px 4px;
        border-radius: 3px;
    }
    blockquote {
        border-left: 4px solid #3b82f6;
        padding-left: 10px;
        margin-left: 0;
        color: #475569;
        font-style: italic;
    }
    hr {
        border: none;
        border-top: 1px solid #e2e8f0;
        margin: 14px 0;
    }
    .diagram-box {
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 6px;
        padding: 8px 12px;
        margin: 10px 0;
    }
    .diagram-box strong {
        color: #1d4ed8;
        display: block;
        margin-bottom: 4px;
    }
    """

    story = pymupdf.Story(html=html_body, user_css=css)
    writer = pymupdf.DocumentWriter(output_path)
    mediabox = pymupdf.paper_rect("a4")
    # 15mm margins in points (1 mm = 2.83465 pt)
    margin_x = 15 * 2.83465
    margin_y = 15 * 2.83465
    content_rect = pymupdf.Rect(margin_x, margin_y, mediabox.width - margin_x, mediabox.height - margin_y)
    ctm = pymupdf.Identity

    story.write(writer, lambda n, f: (mediabox, content_rect, ctm))
    writer.close()
    print(f"Generated PDF: {output_path}")

def build_doc(html_body, output_path):
    """Creates a full-featured Word Document (.doc) that Microsoft Word, LibreOffice, and Google Docs open with full formatting."""
    word_html = f"""<!DOCTYPE html>
<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
<head>
    <meta charset='utf-8'>
    <title>Missing Person Identification System (MPIS) - Project Report</title>
    <!--[if gte mso 9]>
    <xml>
        <w:WordDocument>
            <w:View>Print</w:View>
            <w:Zoom>100</w:Zoom>
            <w:DoNotOptimizeForBrowser/>
        </w:WordDocument>
    </xml>
    <![endif]-->
    <style>
        @page Section1 {{
            size: 595.3pt 841.9pt; /* A4 */
            margin: 54.0pt 54.0pt 54.0pt 54.0pt;
            mso-header-margin: 35.4pt;
            mso-footer-margin: 35.4pt;
            mso-paper-source: 0;
        }}
        div.Section1 {{
            page: Section1;
        }}
        body {{
            font-family: 'Calibri', 'Segoe UI', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #1e293b;
        }}
        h1 {{
            font-size: 22pt;
            color: #0f172a;
            border-bottom: 2.5pt solid #2563eb;
            padding-bottom: 4pt;
            margin-top: 12pt;
            margin-bottom: 8pt;
        }}
        h2 {{
            font-size: 16pt;
            color: #1e3a8a;
            border-bottom: 1pt solid #cbd5e1;
            padding-bottom: 3pt;
            margin-top: 18pt;
            margin-bottom: 8pt;
        }}
        h3 {{
            font-size: 12.5pt;
            color: #1e40af;
            margin-top: 12pt;
            margin-bottom: 4pt;
        }}
        p {{
            margin-top: 4pt;
            margin-bottom: 6pt;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-top: 10pt;
            margin-bottom: 14pt;
            font-size: 10pt;
        }}
        th, td {{
            border: 1pt solid #94a3b8;
            padding: 6pt 8pt;
            text-align: left;
            vertical-align: top;
        }}
        th {{
            background-color: #f1f5f9;
            color: #0f172a;
            font-weight: bold;
        }}
        tr:nth-child(even) td {{
            background-color: #f8fafc;
        }}
        pre {{
            background-color: #f8fafc;
            border: 1pt solid #cbd5e1;
            padding: 8pt;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 9.5pt;
            margin-top: 6pt;
            margin-bottom: 8pt;
            white-space: pre-wrap;
        }}
        code {{
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 9.5pt;
            background-color: #f1f5f9;
            padding: 2pt 4pt;
        }}
        blockquote {{
            border-left: 3pt solid #3b82f6;
            padding-left: 10pt;
            margin-left: 0;
            color: #475569;
            font-style: italic;
        }}
        hr {{
            border: none;
            border-top: 1pt solid #cbd5e1;
            margin: 16pt 0;
        }}
        .diagram-box {{
            background-color: #eff6ff;
            border: 1pt solid #bfdbfe;
            padding: 10pt;
            margin: 12pt 0;
        }}
        .diagram-box strong {{
            color: #1d4ed8;
            display: block;
            margin-bottom: 4pt;
        }}
    </style>
</head>
<body>
    <div class="Section1">
        {html_body}
    </div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(word_html)
    print(f"Generated DOC: {output_path}")

def build_docx(html_body, raw_md_path, output_path):
    """
    Creates an OpenXML (.docx) zip package with standard WordprocessingML.
    """
    with open(raw_md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Build XML document body from markdown lines
    body_xml_parts = []
    
    in_table = False
    table_rows = []

    def escape_xml(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

    def flush_table():
        nonlocal in_table, table_rows, body_xml_parts
        if not table_rows:
            in_table = False
            return
        
        xml = ['<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblBorders>'
               '<w:top w:val="single" w:sz="4" w:space="0" w:color="94A3B8"/>'
               '<w:left w:val="single" w:sz="4" w:space="0" w:color="94A3B8"/>'
               '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="94A3B8"/>'
               '<w:right w:val="single" w:sz="4" w:space="0" w:color="94A3B8"/>'
               '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
               '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
               '</w:tblBorders></w:tblPr>']
        
        for r_idx, row in enumerate(table_rows):
            xml.append('<w:tr>')
            for cell in row:
                shd = '<w:shd w:val="clear" w:color="auto" w:fill="F1F5F9"/>' if r_idx == 0 else ''
                bold = '<w:b/>' if r_idx == 0 else ''
                cell_text = escape_xml(cell.strip())
                xml.append(f'<w:tc><w:tcPr>{shd}</w:tcPr><w:p><w:r><w:rPr>{bold}</w:rPr><w:t>{cell_text}</w:t></w:r></w:p></w:tc>')
            xml.append('</w:tr>')
        xml.append('</w:tbl>')
        body_xml_parts.append("".join(xml))
        table_rows = []
        in_table = False

    for line in lines:
        line_s = line.strip()
        
        # Check for table rows
        if line_s.startswith("|") and line_s.endswith("|"):
            parts = [c.strip() for c in line_s.split("|")[1:-1]]
            if all(re.match(r"^:?-+:?$", p) for p in parts if p):
                continue # delimiter row
            in_table = True
            table_rows.append(parts)
            continue
        elif in_table:
            flush_table()

        if not line_s:
            continue
            
        if line_s.startswith("# "):
            text = escape_xml(line_s[2:].strip())
            body_xml_parts.append(f'<w:p><w:pPr><w:pStyle w:val="Heading1"/><w:spacing w:before="240" w:after="120"/></w:pPr><w:r><w:rPr><w:b/><w:color w:val="0F172A"/><w:sz w:val="36"/></w:rPr><w:t>{text}</w:t></w:r></w:p>')
        elif line_s.startswith("## "):
            text = escape_xml(line_s[3:].strip())
            body_xml_parts.append(f'<w:p><w:pPr><w:pStyle w:val="Heading2"/><w:spacing w:before="200" w:after="100"/></w:pPr><w:r><w:rPr><w:b/><w:color w:val="1E3A8A"/><w:sz w:val="28"/></w:rPr><w:t>{text}</w:t></w:r></w:p>')
        elif line_s.startswith("### "):
            text = escape_xml(line_s[4:].strip())
            body_xml_parts.append(f'<w:p><w:pPr><w:pStyle w:val="Heading3"/><w:spacing w:before="160" w:after="80"/></w:pPr><w:r><w:rPr><w:b/><w:color w:val="1E40AF"/><w:sz w:val="24"/></w:rPr><w:t>{text}</w:t></w:r></w:p>')
        elif line_s.startswith("```"):
            continue
        elif line_s.startswith("* ") or line_s.startswith("- "):
            text = escape_xml(line_s[2:].strip())
            body_xml_parts.append(f'<w:p><w:pPr><w:pStyle w:val="ListParagraph"/><w:spacing w:after="60"/></w:pPr><w:r><w:t>• {text}</w:t></w:r></w:p>')
        elif re.match(r"^\d+\.\s", line_s):
            text = escape_xml(re.sub(r"^\d+\.\s*", "", line_s))
            body_xml_parts.append(f'<w:p><w:pPr><w:pStyle w:val="ListParagraph"/><w:spacing w:after="60"/></w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>')
        elif line_s == "---":
            body_xml_parts.append('<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="CBD5E1"/></w:pBdr></w:pPr></w:p>')
        else:
            text = escape_xml(line_s)
            body_xml_parts.append(f'<w:p><w:pPr><w:spacing w:after="100"/></w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>')

    if in_table:
        flush_table()

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        {"".join(body_xml_parts)}
        <w:sectPr>
            <w:pgSz w:w="11906" w:h="16838"/>
            <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
        </w:sectPr>
    </w:body>
</w:document>"""

    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types_xml)
        z.writestr("_rels/.rels", rels_xml)
        z.writestr("word/document.xml", document_xml)

    print(f"Generated DOCX: {output_path}")

def main():
    root_dir = r"c:\Users\disha\Desktop\.vscode\coding\mpis"
    md_file = os.path.join(root_dir, "MPIS_Project_Report.md")
    
    html_body = md_to_html(md_file)
    
    # Target files in workspace
    pdf_workspace = os.path.join(root_dir, "MPIS_Project_Report.pdf")
    doc_workspace = os.path.join(root_dir, "MPIS_Project_Report.doc")
    docx_workspace = os.path.join(root_dir, "MPIS_Project_Report.docx")
    
    # 1. Generate PDF
    build_pdf(html_body, pdf_workspace)
    
    # 2. Generate DOC (Word HTML format)
    build_doc(html_body, doc_workspace)
    
    # 3. Generate DOCX (OpenXML format)
    build_docx(html_body, md_file, docx_workspace)
    print("All documents successfully generated!")

if __name__ == "__main__":
    main()
