"""
核销台账 / Machine-readable reconciliation ledger for red-blue-pen annotation.

把每条修改意见登记为带稳定 ID 的台账条目, 逐轮(round)记录核对结论与证据,
支持跨轮追踪: 本轮解决了几条、还剩几条、有没有"改回去了"的回退项。

台账文件 (ledger.json) 与主文档放同一文件夹, 是唯一事实来源:
  - items[].id            稳定编号 OPN-001, 批注正文首行应回写该编号
  - items[].keywords      机器可检关键词 {expect_absent: [...], expect_present: [...]}
  - items[].history       逐轮记录 {round, color, pages, evidence, note}
  - items[].status        open(红) / resolved(蓝) / manual(橙) / dropped(作废)
  - rounds[]              每轮的文档名、SHA1、日期、统计与迁移清单

Subcommands:
  init            首轮建账:  python ledger.py init --ledger ledger.json --items items.json --doc 主文档.pdf
  check           机器重审:  python ledger.py check --ledger ledger.json --pages pages.json --out round_check.json
  update          记账一轮:  python ledger.py update --ledger ledger.json --results round_check.json --doc 新版.pdf
  report          跨轮汇总:  python ledger.py report --ledger ledger.json [--md report.md]

items.json (init 输入) 每条:
  { "id": "OPN-001"(可省略自动编号), "source": "意见文件#序号", "opinion": "意见原文",
    "action": "delete|replace|add|consistency|manual",
    "keywords": { "expect_absent": ["旧值"], "expect_present": ["新值"] }, "note": "" }

round_check.json (check 输出 = update 输入) 每条:
  { "id": "OPN-001", "color": "blue|red|orange", "pages": [26], "evidence": {...}, "note": "" }
  update 时也可附带新增意见: 无匹配 id 但含 opinion 字段的条目会作为新条目入账。
"""
import sys, os, json, re, argparse, hashlib
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8")

VALID_COLORS = ("blue", "red", "orange")
STATUS_FROM_COLOR = {"blue": "resolved", "red": "open", "orange": "manual"}
COLOR_MARK = {"blue": "B", "red": "R", "orange": "O", None: "-"}


def load(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sha1_of(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def next_id(items):
    mx = 0
    for it in items:
        m = re.match(r"OPN-(\d+)$", it.get("id", ""))
        if m:
            mx = max(mx, int(m.group(1)))
    return f"OPN-{mx + 1:03d}"


def search_pages(pages, kw):
    """去空白检索(规避 PDF 字间空格), 返回 {count, pages, snippets}。"""
    kw_clean = re.sub(r"\s+", "", kw)
    hit_pages, snippets = [], []
    for p in pages:
        text_clean = re.sub(r"\s+", "", p["text"])
        n = text_clean.count(kw_clean)
        if n:
            hit_pages.append(p["page"])
            if len(snippets) < 10:
                idx = text_clean.find(kw_clean)
                snippets.append({"page": p["page"],
                                 "snippet": text_clean[max(0, idx - 25): idx + len(kw_clean) + 35]})
    return {"count": len(hit_pages), "pages": hit_pages, "snippets": snippets}


# ---------------------------------------------------------------- init ----
def cmd_init(args):
    if os.path.exists(args.ledger) and not args.force:
        raise SystemExit(f"[ERR] {args.ledger} 已存在, 跨轮请用 check/update, 覆盖重建加 --force")
    raw = load(args.items)
    items = []
    for it in raw:
        iid = it.get("id") or next_id(items)
        items.append({
            "id": iid,
            "source": it.get("source", ""),
            "opinion": it.get("opinion", ""),
            "action": it.get("action", "manual"),
            "keywords": it.get("keywords", {}),
            "note": it.get("note", ""),
            "status": "open",
            "current_color": None,
            "pages": [],
            "history": [],
        })
    ledger = {
        "schema_version": 1,
        "project": args.project or "",
        "master_doc": os.path.basename(args.doc) if args.doc else "",
        "created": now_str(),
        "rounds": [],
        "items": items,
    }
    save(args.ledger, ledger)
    print(f"[OK] 建账 {len(items)} 条 -> {args.ledger}")
    for it in items:
        print(f"  {it['id']}  [{it['action']:<11}] {it['opinion'][:40]}")


# --------------------------------------------------------------- check ----
def suggest(item, pages):
    """按关键词机器重审一条: 返回 (suggested_color, pages, evidence)。"""
    kws = item.get("keywords", {})
    absent = kws.get("expect_absent", [])
    present = kws.get("expect_present", [])
    evidence = {}
    for kw in absent:
        evidence[kw] = dict(search_pages(pages, kw), expect="absent")
    for kw in present:
        evidence[kw] = dict(search_pages(pages, kw), expect="present")

    if item.get("action") == "manual" or (not absent and not present):
        color = "orange"
    else:
        ok = all(evidence[k]["count"] == 0 for k in absent) and \
             all(evidence[k]["count"] > 0 for k in present)
        color = "blue" if ok else "red"

    if color == "red":
        pg = sorted({p for k in absent for p in evidence[k]["pages"]}) or \
             sorted({p for k in present for p in evidence[k]["pages"]}) or item.get("pages", [])
    else:
        pg = sorted({p for k in present for p in evidence[k]["pages"]}) or item.get("pages", [])
    return color, pg, evidence


def cmd_check(args):
    ledger = load(args.ledger)
    pages = load(args.pages)
    results = []
    for it in ledger["items"]:
        if it["status"] == "dropped":
            continue
        if args.scope == "open" and it["status"] == "resolved":
            continue
        color, pg, ev = suggest(it, pages)
        results.append({"id": it["id"], "color": color, "pages": pg,
                        "evidence": ev, "note": ""})
        flag = "!!" if (it["current_color"] == "blue" and color != "blue") else "  "
        print(f"{flag} {it['id']}  {COLOR_MARK[it['current_color']]} -> {COLOR_MARK[color]}"
              f"  p{pg[:8]}  {it['opinion'][:32]}")
    save(args.out, results)
    n = {c: sum(1 for r in results if r["color"] == c) for c in VALID_COLORS}
    print(f"\n[OK] 机器重审 {len(results)} 条 -> {args.out}"
          f"  (建议 蓝{n['blue']} 红{n['red']} 橙{n['orange']})")
    print("     橙色与 '!!'(疑似回退) 项需人工复核后再 update。")


# -------------------------------------------------------------- update ----
def cmd_update(args):
    ledger = load(args.ledger)
    results = load(args.results)
    rnd = len(ledger["rounds"]) + 1
    by_id = {it["id"]: it for it in ledger["items"]}
    trans = {"resolved": [], "regressed": [], "still_open": [], "manual": [], "new": []}

    for r in results:
        color = r.get("color")
        if color not in VALID_COLORS:
            raise SystemExit(f"[ERR] {r.get('id','?')} 颜色非法: {color}")
        it = by_id.get(r.get("id", ""))
        if it is None:
            if not r.get("opinion"):
                raise SystemExit(f"[ERR] 未知 id 且无 opinion, 无法入账: {r}")
            it = {"id": r.get("id") or next_id(ledger["items"]),
                  "source": r.get("source", ""), "opinion": r["opinion"],
                  "action": r.get("action", "manual"),
                  "keywords": r.get("keywords", {}), "note": r.get("note", ""),
                  "status": "open", "current_color": None, "pages": [], "history": []}
            ledger["items"].append(it)
            by_id[it["id"]] = it
            trans["new"].append(it["id"])

        prev = it["current_color"]
        if prev == "blue" and color != "blue":
            trans["regressed"].append(it["id"])
        elif color == "blue" and prev != "blue":
            if it["id"] not in trans["new"]:
                trans["resolved"].append(it["id"])
        elif color == "red":
            trans["still_open"].append(it["id"])
        elif color == "orange":
            trans["manual"].append(it["id"])

        it["history"].append({"round": rnd, "color": color,
                              "pages": r.get("pages", []),
                              "evidence": r.get("evidence", {}),
                              "note": r.get("note", "")})
        it["current_color"] = color
        it["status"] = STATUS_FROM_COLOR[color]
        it["pages"] = r.get("pages", [])

    checked = {r.get("id") for r in results}
    unchecked = [it["id"] for it in ledger["items"]
                 if it["id"] not in checked and it["status"] not in ("dropped",)]

    ledger["rounds"].append({
        "round": rnd, "date": now_str(),
        "doc": os.path.basename(args.doc) if args.doc else "",
        "doc_sha1": sha1_of(args.doc) if args.doc and os.path.exists(args.doc) else "",
        "annotated_pdf": os.path.basename(args.annotated) if args.annotated else "",
        "stats": {k: len(v) for k, v in trans.items()} | {"unchecked": len(unchecked)},
        "transitions": trans,
    })
    save(args.ledger, ledger)

    print(f"[OK] 第 {rnd} 轮已记账 -> {args.ledger}")
    print(f"  本轮解决 : {len(trans['resolved'])}  {trans['resolved']}")
    print(f"  仍未落实 : {len(trans['still_open'])}  {trans['still_open']}")
    print(f"  需人工   : {len(trans['manual'])}  {trans['manual']}")
    print(f"  新增意见 : {len(trans['new'])}  {trans['new']}")
    if trans["regressed"]:
        print(f"  !! 回退  : {len(trans['regressed'])}  {trans['regressed']}  (上轮已改好, 本轮又不满足)")
    if unchecked:
        print(f"  本轮未核 : {len(unchecked)}  {unchecked}")


# -------------------------------------------------------------- report ----
def cmd_report(args):
    ledger = load(args.ledger)
    rounds = ledger["rounds"]
    items = [it for it in ledger["items"] if it["status"] != "dropped"]
    n_r = len(rounds)

    print(f"项目: {ledger.get('project') or ledger.get('master_doc')}   共 {n_r} 轮 / {len(items)} 条")
    header = "ID       " + " ".join(f"R{r['round']}" for r in rounds) + "  状态      页码           意见"
    print(header); print("-" * min(100, len(header) + 20))
    lines_md = []
    for it in items:
        marks = {h["round"]: COLOR_MARK[h["color"]] for h in it["history"]}
        row = " ".join(f"{marks.get(r['round'], '.'):>2}" for r in rounds)
        pg = ",".join(map(str, it["pages"][:6])) or "-"
        print(f"{it['id']}  {row}  {it['status']:<9} p{pg:<12} {it['opinion'][:36]}")
        emoji = {"B": "🔵", "R": "🔴", "O": "🟠", ".": "·"}
        row_md = " | ".join(emoji[marks.get(r["round"], ".")] for r in rounds)
        lines_md.append(f"| {it['id']} | {row_md} | {it['status']} | {pg} | {it['opinion'][:50]} |")

    open_ids = [it["id"] for it in items if it["status"] == "open"]
    manual_ids = [it["id"] for it in items if it["status"] == "manual"]
    print(f"\n未落实(红): {len(open_ids)} {open_ids}\n需人工(橙): {len(manual_ids)} {manual_ids}")

    if args.md:
        md = [f"# 核销台账跨轮汇总 — {ledger.get('project') or ledger.get('master_doc')}", "",
              f"共 {n_r} 轮, {len(items)} 条意见; 未落实 {len(open_ids)} 条, 需人工 {len(manual_ids)} 条。", "",
              "| ID | " + " | ".join(f"R{r['round']}" for r in rounds) + " | 状态 | 页码 | 意见 |",
              "|----|" + "----|" * (n_r + 3)]
        md += lines_md
        md += ["", "## 轮次记录", "",
               "| 轮 | 日期 | 文档 | SHA1 | 解决 | 未落实 | 回退 | 新增 |",
               "|----|------|------|------|------|--------|------|------|"]
        for r in rounds:
            s = r["stats"]
            md.append(f"| {r['round']} | {r['date']} | {r['doc']} | {r['doc_sha1']} "
                      f"| {s.get('resolved',0)} | {s.get('still_open',0)} "
                      f"| {s.get('regressed',0)} | {s.get('new',0)} |")
        with open(args.md, "w", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")
        print(f"[OK] markdown -> {args.md}")


def main():
    ap = argparse.ArgumentParser(description="红蓝笔核销台账")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init");   p.add_argument("--ledger", required=True)
    p.add_argument("--items", required=True); p.add_argument("--doc")
    p.add_argument("--project"); p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("check");  p.add_argument("--ledger", required=True)
    p.add_argument("--pages", required=True); p.add_argument("--out", required=True)
    p.add_argument("--scope", choices=["all", "open"], default="all",
                   help="all=全部重审(能发现回退); open=只审未落实项")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("update"); p.add_argument("--ledger", required=True)
    p.add_argument("--results", required=True); p.add_argument("--doc")
    p.add_argument("--annotated")
    p.set_defaults(fn=cmd_update)

    p = sub.add_parser("report"); p.add_argument("--ledger", required=True)
    p.add_argument("--md")
    p.set_defaults(fn=cmd_report)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
