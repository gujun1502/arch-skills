"""
提取主 PDF 每页文本 → JSON, 供"意见核对"步骤检索关键词使用。
Extract per-page text of the main PDF to JSON for the cross-audit step.

Usage:
  python extract_pdf.py --pdf IN.pdf --out pages.json
"""
import sys, json, argparse
sys.stdout.reconfigure(encoding="utf-8")
import fitz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    pages = []
    for i, page in enumerate(doc):
        pages.append({"page": i + 1, "text": page.get_text()})
    doc.close()

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)

    print(f"[OK] {len(pages)} pages -> {args.out}")


if __name__ == "__main__":
    main()
