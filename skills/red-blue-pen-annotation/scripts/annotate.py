"""
红蓝笔批注渲染器 / Red-Blue pen annotation renderer.

Reads an input PDF and an annotations JSON, renders每页为图像并叠加
红/蓝/橙色批注框, 输出单一 PDF。修改页含批注, 其余页保持原样。

颜色语义 (semantic convention — keep consistent):
  blue   = 已按意见改好, 经核对确认 (✓ 已改 / ✓ 复核)
  red    = 仍需处理 / 意见未落实 / 内容缺失 (⚠ 需复核 / ⚠ 缺失)
  orange = 需人工确认的提示, 非硬性结论 (复核提示)

Usage:
  python annotate.py --pdf IN.pdf --annotations ann.json --out OUT.pdf [--dpi 150]

annotations JSON schema:
{
  "<page_number>": [
    {
      "color": "blue" | "red" | "orange",
      "title": "✓ 已改",
      "body": "多行文本\n用 \\n 换行",
      "position": [x_rel, y_rel, w_rel, h_rel]   # 0-1 相对页面比例
    },
    ...
  ],
  ...
}
"""
import sys, os, io, json, argparse
sys.stdout.reconfigure(encoding="utf-8")
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

# ---- Colors (semantic) -------------------------------------------------
COLORS = {
    "red":    (200, 25, 25),    # 仍需处理 / 未落实 / 缺失
    "blue":   (20, 60, 200),    # 已改好, 已核对
    "orange": (235, 115, 20),   # 人工复核提示
}

# ---- CJK font auto-detection (Windows first, then Linux) ---------------
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def find_font():
    for fp in FONT_CANDIDATES:
        if os.path.exists(fp):
            return fp
    raise SystemExit("No CJK-capable font found. Install msyh/simhei or wqy-zenhei.")


def draw_annotation(img, ann, font_path):
    """Draw one annotation box on a PIL image (proven layout)."""
    draw = ImageDraw.Draw(img, "RGBA")
    W, H = img.size

    x_rel, y_rel, w_rel, h_rel = ann["position"]
    x, y = int(W * x_rel), int(H * y_rel)
    w, h = int(W * w_rel), int(H * h_rel)

    color = COLORS.get(ann.get("color", "red"), COLORS["red"])
    fill_bg = (255, 255, 255, 236)   # near-opaque white note ground for legibility over photos
    border = color + (255,)

    # Box
    draw.rectangle([x, y, x + w, y + h], fill=fill_bg, outline=border, width=4)

    # Title bar
    title = ann.get("title", "")
    body = ann.get("body", "")
    title_h = max(28, int(h * 0.18))
    draw.rectangle([x, y, x + w, y + title_h], fill=border)

    title_font = ImageFont.truetype(font_path, size=max(16, int(title_h * 0.65)))
    draw.text((x + 8, y + 3), title, font=title_font, fill=(255, 255, 255))

    # Body text (manual \n line breaks)
    body_font = ImageFont.truetype(font_path, size=max(14, int(h * 0.075)))
    line_h = max(18, int(h * 0.085))
    for i, line in enumerate(body.split("\n")):
        draw.text((x + 8, y + title_h + 6 + i * line_h), line, font=body_font, fill=border)

    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, help="input PDF path")
    ap.add_argument("--annotations", required=True, help="annotations JSON path")
    ap.add_argument("--out", required=True, help="output PDF path")
    ap.add_argument("--dpi", type=int, default=150, help="render DPI (150 default, 200 for sharper)")
    args = ap.parse_args()

    font_path = find_font()
    print(f"Using font: {font_path}")

    with open(args.annotations, "r", encoding="utf-8-sig") as f:
        raw = json.load(f)
    annotations = {int(k): v for k, v in raw.items()}

    doc = fitz.open(args.pdf)
    n_pages = len(doc)
    print(f"Total pages: {n_pages}")

    out_doc = fitz.open()
    for pg_idx in range(n_pages):
        page_num = pg_idx + 1
        page = doc[pg_idx]
        pix = page.get_pixmap(dpi=args.dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

        if page_num in annotations:
            print(f"  Annotating page {page_num}  ({len(annotations[page_num])} note(s))")
            for ann in annotations[page_num]:
                img = draw_annotation(img, ann, font_path)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        rect = page.rect
        new_page = out_doc.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, stream=buf.getvalue())

        if page_num % 20 == 0:
            print(f"  progress: {page_num}/{n_pages}")

    out_doc.save(args.out, garbage=4, deflate=True)
    out_doc.close()
    doc.close()

    sz = os.path.getsize(args.out) / 1024 / 1024
    print(f"\n[OK] Output: {args.out}  ({sz:.1f} MB)")
    print(f"     Annotated pages: {sorted(annotations.keys())}")


if __name__ == "__main__":
    main()
