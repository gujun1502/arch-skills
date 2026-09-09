#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill-safety-audit — scan a skill folder (or any files) for secrets, personal data,
network / filesystem / execution behaviour and prompt-injection, infer a safety level
(L1 read-only · L2 writes locally · L3 network · L4 executes / sends), and optionally
write a redacted copy.

Usage:
  python audit.py <path> [<path> ...] [--words "ProjectA,ClientB"] [--redact OUT_DIR] [--json]

Runs fully offline. Same rule set as the in-browser auditor at https://arch-skills.com/#audit
"""
import argparse, json, os, re, sys

RULES = [
    # (category, severity, regex, reason)
    ("secret", "crit", r"\b(sk-(?:ant-)?[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}|vercel_blob_rw_[A-Za-z0-9_]{10,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})", "API key / token"),
    ("secret", "crit", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
    ("secret", "crit", r"\b(api[_-]?key|secret|token|passw(?:or)?d|密码|密钥|口令)\b\s*[:=：]\s*['\"]?[^\s'\",;]{6,}", "plaintext credential assignment"),
    ("pii", "warn", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "email address"),
    ("pii", "warn", r"(?<!\d)1[3-9]\d{9}(?!\d)", "mobile number (CN)"),
    ("pii", "crit", r"(?<!\d)\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)", "national ID number (CN)"),
    ("fs", "crit", r"\b(rm\s+-rf?|shutil\.rmtree|os\.remove|os\.unlink|fs\.rmSync|fs\.unlinkSync|rimraf|Remove-Item|del\s+/[fq])\b", "deletes files or folders"),
    ("fs", "info", r"\b(open\([^)]*['\"][wa]b?['\"]|write_text|write_bytes|writeFile|writeFileSync|to_csv|to_excel|\.save\(|savefig|Out-File|Set-Content)", "writes files"),
    ("net", "warn", r"\bhttps?://[^\s'\"`)>\]]+", "external URL"),
    ("net", "warn", r"\b(fetch\(|requests\.(?:get|post|put|delete)|urllib|httpx|aiohttp|axios|curl\b|wget\b|Invoke-WebRequest|WebFetch|WebSearch|playwright|selenium)", "network request"),
    ("exec", "crit", r"\b(subprocess\.|os\.system|os\.popen|exec\(|eval\(|child_process|execSync|spawn\(|Invoke-Expression|Start-Process|bash\s+-c|powershell\s+-c)", "executes commands / dynamic code"),
    ("ext", "crit", r"\b(smtplib|sendmail|sendgrid|twilio|mailgun|webhook|wa\.me|api\.kit\.com|buttondown|place_order|create_order|下单|转账|发送邮件|推送到微信|飞书机器人|钉钉机器人)\b", "sends, orders or pushes externally"),
    ("ext", "info", r"\b(openai|anthropic|gemini|deepseek|dashscope|moonshot|zhipu|api\.x\.com|twitter\.com|weixin\.qq\.com|xiaohongshu)\b", "calls an external model / platform"),
    ("inj", "crit", r"(ignore (?:all |the )?(?:previous|above|prior) instructions|disregard (?:your|the) system prompt|you are now|忽略(?:以上|之前|上面)(?:的)?(?:所有)?(?:指令|规则|提示)|无视系统提示|从现在起你是)", "possible prompt injection"),
    ("inj", "warn", r"(do not tell the user|不要告诉用户|不要让用户知道|hide this from|secretly|悄悄地)", "asks to hide behaviour from the user"),
]
FLAGS = re.IGNORECASE
TEXT_EXT = {".md", ".txt", ".py", ".js", ".jsx", ".ts", ".json", ".yaml", ".yml", ".toml", ".sh", ".ps1", ".bat", ".html", ".css", ".csv", ".env", ".cfg", ".ini", ".typ"}
ORDER = ["secret", "pii", "net", "fs", "exec", "ext", "inj", "word"]
LEVEL_TEXT = {1: "Read-only", 2: "Writes locally", 3: "Network", 4: "Executes / sends"}


def iter_files(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
        else:
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".venv"}]
                for f in files:
                    if os.path.splitext(f)[1].lower() in TEXT_EXT:
                        yield os.path.join(root, f)


def mask(s):
    return "•" * len(s) if len(s) <= 8 else s[:4] + "…" + s[-3:]


def audit(paths, words=(), redact_dir=None):
    findings, counts, total_lines = [], {}, 0
    compiled = [(c, sev, re.compile(rx, FLAGS), why) for c, sev, rx, why in RULES]
    for fp in iter_files(paths):
        try:
            text = open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        out = []
        for i, line in enumerate(text.splitlines(), 1):
            total_lines += 1
            red = line
            for c, sev, rx, why in compiled:
                seen = set()
                for m in rx.finditer(line):
                    hit = m.group(0)
                    if hit in seen:
                        continue
                    seen.add(hit)
                    findings.append({"file": fp, "line": i, "cat": c, "sev": sev, "why": why,
                                     "snippet": line.strip().replace(hit, mask(hit)) if c == "secret" else line.strip()})
                    counts[c] = counts.get(c, 0) + 1
                    if c == "secret":
                        red = red.replace(hit, "[REDACTED-KEY]")
                    elif c == "pii":
                        red = red.replace(hit, "[email]" if "@" in hit else ("[id]" if len(hit) >= 15 else "[phone]"))
            for w in words:
                if w and w in line:
                    findings.append({"file": fp, "line": i, "cat": "word", "sev": "warn", "why": "sensitive word", "snippet": line.strip()})
                    counts["word"] = counts.get("word", 0) + 1
                    red = red.replace(w, "[REDACTED]")
            out.append(red)
        if redact_dir:
            dst = os.path.join(redact_dir, os.path.relpath(fp, os.path.commonpath([os.path.abspath(p) for p in paths])) if len(paths) > 1 or os.path.isdir(paths[0]) else os.path.basename(fp))
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            open(dst, "w", encoding="utf-8").write("\n".join(out))
    level = 1
    if counts.get("fs"):
        level = 2
    if counts.get("net") or counts.get("ext"):
        level = max(level, 3)
    if counts.get("exec") or any(f["cat"] == "ext" and f["sev"] == "crit" for f in findings):
        level = 4
    crit = any(f["sev"] == "crit" for f in findings)
    rank = {"crit": 0, "warn": 1, "info": 2}
    findings.sort(key=lambda f: (rank[f["sev"]], f["file"], f["line"]))
    return {"level": level, "level_text": LEVEL_TEXT[level], "critical": crit, "lines": total_lines,
            "counts": {k: counts.get(k, 0) for k in ORDER}, "findings": findings}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--words", default="", help="comma-separated sensitive words (project / client / person names)")
    ap.add_argument("--redact", metavar="OUT_DIR", help="write redacted copies here")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args()
    words = [w.strip() for w in re.split(r"[,，、]", a.words) if len(w.strip()) >= 2]
    r = audit(a.paths, words, a.redact)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return
    print(f"Safety level: L{r['level']} · {r['level_text']}" + ("  !! CRITICAL items found" if r["critical"] else ""))
    print("Counts: " + "  ".join(f"{k}={v}" for k, v in r["counts"].items()) + f"  (lines scanned: {r['lines']})")
    for f in r["findings"]:
        print(f"[{f['sev'].upper():4}] {f['file']}:{f['line']}  {f['cat']} · {f['why']}\n        {f['snippet'][:160]}")
    if not r["findings"]:
        print("✓ no risk items found")
    if a.redact:
        print(f"Redacted copies written to {a.redact}")
    sys.exit(2 if r["critical"] else 0)


if __name__ == "__main__":
    main()
