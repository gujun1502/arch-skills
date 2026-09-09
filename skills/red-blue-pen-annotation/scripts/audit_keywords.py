"""
意见核对 / Cross-audit: 在主 PDF 文本中检索每条意见的关键词,
统计命中页与次数, 用来判断该意见是"已落实"(蓝) 还是"未落实"(红)。

判断逻辑约定 (let the model interpret per instruction):
  - 要求"删除某词" → count == 0 即已落实(蓝); count > 0 即未删干净(红)
  - 要求"改为新值" → 新值命中(蓝) 且 旧值 count == 0; 否则(红)
  - 要求"新增" → 新内容命中(蓝); 缺失(红)
  - 命中位置(page)即批注应落的页码

关键词搜索会去除空白字符, 以规避 PDF 抽取出的字间空格(如把"标准"抽成"标 准")。

Usage:
  python audit_keywords.py --pages pages.json --keywords kw.json --out audit.json

keywords JSON schema:  { "<keyword>": "<note / 期望状态>", ... }
"""
import sys, json, re, argparse
sys.stdout.reconfigure(encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True, help="pages.json from extract_pdf.py")
    ap.add_argument("--keywords", required=True, help="keywords JSON {kw: note}")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.pages, "r", encoding="utf-8-sig") as f:
        pages = json.load(f)
    with open(args.keywords, "r", encoding="utf-8-sig") as f:
        keywords = json.load(f)

    results = {}
    for kw, note in keywords.items():
        kw_clean = kw.replace(" ", "")
        hits = []
        for p in pages:
            text_clean = re.sub(r"\s+", "", p["text"])
            if kw_clean in text_clean:
                idx = text_clean.find(kw_clean)
                snippet = text_clean[max(0, idx - 30): idx + len(kw_clean) + 40]
                hits.append({"page": p["page"], "snippet": snippet})
        results[kw] = {"note": note, "count": len(hits), "hits": hits}

    print("=" * 80)
    for kw, r in results.items():
        print(f"\n[{kw}] ({r['note']}) - {r['count']} 处")
        for h in r["hits"][:15]:
            print(f"   p{h['page']:>3}: ...{h['snippet']}...")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] audit -> {args.out}")


if __name__ == "__main__":
    main()
