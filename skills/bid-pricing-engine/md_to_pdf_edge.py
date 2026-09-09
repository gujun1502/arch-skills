import sys, subprocess, pathlib, urllib.parse
import markdown

md_path = pathlib.Path(sys.argv[1])
pdf_path = pathlib.Path(sys.argv[2])
edge = sys.argv[3]

text = md_path.read_text(encoding="utf-8")
body = markdown.markdown(text, extensions=["tables", "fenced_code", "toc", "sane_lists"])

CSS = """
@page { size: A4; margin: 1.8cm 1.6cm; }
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei","SimSun",sans-serif; font-size: 11.5pt;
       line-height: 1.75; color: #1a1a1a; max-width: 100%; }
h1 { font-size: 22pt; color: #0b3d66; border-bottom: 3px solid #0b3d66;
     padding-bottom: 8px; margin-top: 0; }
h2 { font-size: 16pt; color: #0b3d66; border-left: 6px solid #2e7fb8;
     padding-left: 10px; margin-top: 28px; }
h3 { font-size: 13pt; color: #1f5a82; margin-top: 20px; }
h4 { font-size: 12pt; color: #333; }
blockquote { background: #eef5fb; border-left: 4px solid #2e7fb8; margin: 12px 0;
             padding: 8px 14px; color: #335; }
table { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 10.5pt; }
th, td { border: 1px solid #b9c9d6; padding: 6px 9px; text-align: left;
         vertical-align: top; }
th { background: #0b3d66; color: #fff; }
tr:nth-child(even) td { background: #f3f8fc; }
pre { background: #1e2530; color: #e6edf3; padding: 14px; border-radius: 6px;
      overflow-x: auto; font-size: 8.6pt; line-height: 1.45;
      font-family: "Consolas","Courier New",monospace; white-space: pre; }
code { font-family: "Consolas","Courier New",monospace; }
:not(pre) > code { background: #eef1f4; color: #c0341d; padding: 1px 5px;
                   border-radius: 3px; font-size: 9.5pt; }
hr { border: none; border-top: 1px solid #ccd; margin: 22px 0; }
strong { color: #0b3d66; }
ul, ol { padding-left: 24px; }
li { margin: 3px 0; }
h2, h3 { page-break-after: avoid; }
table, pre, blockquote { page-break-inside: avoid; }
"""

html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<style>{CSS}</style></head><body>{body}</body></html>"""

html_path = md_path.with_suffix(".html")
html_path.write_text(html, encoding="utf-8")

url = "file:///" + urllib.parse.quote(str(html_path).replace("\\", "/"))
subprocess.run([edge, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}", url], check=True, timeout=120)
print("PDF_DONE", pdf_path, pdf_path.stat().st_size, "bytes")
