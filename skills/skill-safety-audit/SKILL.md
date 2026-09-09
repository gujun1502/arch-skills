---
name: skill-safety-audit
description: >-
  Skill 安全审计器。在安装任何 Claude Code / Codex / Cursor skill 之前，扫描其 SKILL.md 与脚本：
  密钥与明文口令、邮箱 / 手机 / 证件号、联网请求、写 / 删文件、执行命令、外发 / 下单 / 推送、
  调用外部模型平台、提示注入与"对用户隐瞒"指令；推断安全等级 L1–L4；生成把敏感内容替换成占位符的脱敏版。
  当用户说"审计这个 skill / 这个技能安全吗 / 装之前检查一下 / 帮我脱敏 / 把项目名去掉再开源"，
  或准备把一个 skill 文件夹开源、分享、提交到注册表时使用。
  Skill safety auditor: scan a skill folder for secrets, personal data, network / filesystem / execution
  behaviour and prompt injection, infer an L1–L4 safety level, and produce a redacted copy. Use before
  installing, sharing or open-sourcing any skill.
license: MIT (code) · CC BY 4.0 (docs) — attribution: Gu Jun / arch-skills.com
author: Gu Jun (gujun1502)
homepage: https://arch-skills.com/#skill/skill-safety-audit
source: https://github.com/gujun1502/arch-skills
---

# Skill 安全审计器 / Skill Safety Auditor

装之前先审计。一个 skill 就是一个会被 Agent 自动执行的文件夹——它能读什么、写什么、连哪里、跑什么命令，
装之前应该一目了然。本技能用十四条规则把这些问题变成一份清单和一个等级。

## 安全等级 / Safety levels

| 等级 | 含义 | 判定 |
|---|---|---|
| **L1** 只读分析 | 只读输入文件，不落盘、不联网 | 无写盘 / 联网 / 执行痕迹 |
| **L2** 本地写文件 | 会在项目目录生成 PDF / 图 / 表 / 台账 | 出现写文件调用 |
| **L3** 联网抓取 | 会访问外部网站或接口 | 出现 URL 或请求库 |
| **L4** 执行外部动作 | 运行外部命令、发送消息或下单，需要人在环 | 出现命令执行、外发、下单 |

等级描述技能**会碰到什么**，不描述它好不好。删除文件、明文密钥、提示注入不改变等级，但会被标为 **CRIT** 高危项。

## 十四条规则 / The rules

| 类别 | 命中 | 严重度 |
|---|---|---|
| secret | OpenAI / Anthropic / AWS / GitHub / Slack / Google / Vercel 令牌、JWT、私钥、`api_key = …` 明文赋值 | CRIT |
| pii | 邮箱、中国大陆手机号、身份证号 | WARN / CRIT |
| fs | `rm -rf` `shutil.rmtree` `os.remove` 等删除 | CRIT |
| fs | `open(…,'w')` `to_csv` `savefig` 等写文件 | INFO |
| net | `http(s)://` 地址；`requests` `fetch` `curl` `WebFetch` 等 | WARN |
| exec | `subprocess` `os.system` `exec(` `eval(` `Invoke-Expression` 等 | CRIT |
| ext | `smtplib` `twilio` `webhook` `下单` `转账` `推送到微信` 等外发 | CRIT |
| ext | `openai` `anthropic` `gemini` `deepseek` 等外部模型平台 | INFO |
| inj | "ignore previous instructions" "忽略以上指令" "从现在起你是" | CRIT |
| inj | "do not tell the user" "不要告诉用户" "悄悄地" | WARN |
| word | 用户自填的项目名、客户名、人名 | WARN |

## 用法 / Usage

**命令行**（离线，不上传任何文件）：

```bash
python audit.py ~/.claude/skills/some-skill
python audit.py ~/.claude/skills/some-skill --words "某项目,某客户" --redact ./redacted
python audit.py path/to/SKILL.md --json
```

退出码：0 = 无高危项；2 = 有 CRIT 项。`--redact` 会把每个文件的脱敏副本写到目标目录：
密钥 → `[REDACTED-KEY]`，邮箱 → `[email]`，手机 → `[phone]`，证件号 → `[id]`，敏感词 → `[REDACTED]`。

**浏览器版**：https://arch-skills.com/#audit — 选文件夹或粘贴文本即可，规则与本脚本一致。

**Agent 里怎么用**：对 Claude Code 说"审计一下 ~/.claude/skills/xxx 安不安全"，本技能会跑脚本、解释每一条高危项、给出等级，并在你要开源或分享时先产出脱敏版。

## 工作流 / Workflow

1. 跑 `audit.py` 得到等级与清单。
2. 逐条看 CRIT：明文密钥必须移到环境变量；删除操作必须限定在临时目录并在 SKILL.md 里写明；注入指令直接删除。
3. 看 WARN 里的联网域名清单，确认每一个都是技能确实需要的。
4. 要开源 / 分享：`--words` 填上真实项目名与客户名，用 `--redact` 产出的副本发布。
5. 把等级写进 SKILL.md 的 frontmatter（例如 `safety: L2`），方便下一个人不用再审。

## 局限 / Limits

- 正则规则，不做数据流分析：能抓住"写了什么"，抓不住"绕着写"。高危技能仍需人读一遍脚本。
- 中文手机号 / 证件号规则只覆盖中国大陆格式。
- 二进制文件（图片、PDF、docx）不扫描。
