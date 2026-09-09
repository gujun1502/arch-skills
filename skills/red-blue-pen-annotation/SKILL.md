---
name: red-blue-pen-annotation
description: |
  红蓝笔批注 Skill。把一份主文档(设计导则/规范/手册等 PDF)与若干修改意见文件
  对照核对后, 在原始页面上用“红笔 / 蓝笔”双色标注落实情况, 输出单一批注版 PDF。
  蓝笔=已按意见改好并经核对确认; 红笔=意见尚未落实/内容缺失/需复核; 橙色=需人工确认的提示。
  内置机器可读核销台账(ledger.json), 逐条意见带稳定编号, 支持跨轮追踪:
  第 N 轮只需新版 PDF + 旧台账即可自动重审、记录解决/未落实/回退迁移。
  Trigger whenever the user mentions: "红蓝笔批注", "红蓝笔", "红笔修改", "蓝笔", "批注",
  "修改意见", "意见核对", "导则修订", "核销台账", "台账", "第N轮核对", "跨轮追踪",
  "redline PDF", "markup PDF", "annotate PDF",
  或当文件夹里有 1 份主 PDF + 若干意见文件(.docx/.pdf/.txt/图片) 需要合并成一份批注版时,
  或文件夹里已有 ledger.json + 新版主 PDF 需要做第 N 轮核对时。
  全流程: 识别主文档与意见 → 提取双方文本 → 逐条核对意见是否落实 → 按红/蓝语义定色定位
  → 渲染批注 → 记入核销台账 → 输出批注版 PDF + 核对汇总。
license: MIT (code) · CC BY 4.0 (docs) — attribution: Gu Jun / arch-skills.com
author: Gu Jun (gujun1502)
homepage: https://arch-skills.com/#skill/red-blue-pen-annotation
source: https://github.com/gujun1502/arch-skills
---

# 红蓝笔批注 Skill

把"主文档 + 修改意见"对照核对, 在原页面上用红/蓝双色笔标出每条意见的落实情况,
产出一份**言简意赅、针对性强**的批注版 PDF, 让执行者照着改即可。

## 核心理念:颜色即结论

批注的价值不在"画框", 而在**先核对、再下结论**。每条意见都要回答"改了没有":

| 颜色 | 语义 | 触发条件 | 标题示例 |
|------|------|----------|----------|
| 🔵 **蓝笔** | 已落实, 经核对确认 | 要求的修改在主文档中已生效(该删的删了/新值已出现) | `✓ 已改` `✓ 复核` |
| 🔴 **红笔** | 未落实 / 缺失 / 需复核 | 旧内容仍在、新内容缺失、或多处不一致(如主表已改但附表未同步) | `⚠ 需复核` `⚠ 缺失` |
| 🟠 **橙色** | 人工确认提示 | 字面相似但非同一目标、需人来拍板的情况 | `复核提示` |

**这是 Skill 最关键的判断**。不要把所有意见都标红或都标蓝 —— 必须逐条去主文档里查,
查到"已改"才给蓝, 查到"没改/不一致"才给红。红蓝对比一眼就能看出"还剩哪些要做"。

批注正文要短(每行约 14 字, 总 3–6 行), 写清:意见出处、当前状态、建议动作。
位置落在对应表格/段落附近的空白处, 不遮挡原文。

## 环境依赖

```
pip install pymupdf pillow python-docx
```
PyMuPDF(`fitz`)负责渲染与文本提取, Pillow 负责画批注。中文字体自动检测
(Windows: 微软雅黑/黑体; Linux: wqy-zenhei/NotoSansCJK)。

## 执行步骤

### Step 1 — 识别主文档与意见文件
扫描文件夹。**主文档**通常是体积最大、命名含"导则/规范/手册/标准"的 PDF;
其余 PDF/DOCX/TXT/图片均为**意见文件**。若用户已指明, 直接采用。
意见若是图片(扫描的手写批注), 用 Read 工具读图获取文字。

### Step 2 — 提取双方文本
- 主文档逐页文本:
  ```
  python scripts/extract_pdf.py --pdf "主文档.pdf" --out pages.json
  ```
- 意见文件文本:docx 用 python-docx, pdf 用 fitz, txt 直接读, 图片用 Read 工具。
  把所有意见汇总成一份"意见清单"(逐条:出处/原文/要求动作/目标位置)。

### Step 3 — 逐条核对意见是否落实(本 Skill 的灵魂)
把每条意见拆成可检索的**关键词**, 写成 `keywords.json`:`{ "关键词": "期望状态备注" }`,
然后:
```
python scripts/audit_keywords.py --pages pages.json --keywords keywords.json --out audit.json
```
脚本会去空格检索(规避 PDF 抽取出的字间空格, 如把"标准"抽成"标 准"), 返回每个关键词的命中页与次数。

**判定准则(与具体文档无关, 据此把意见映射成颜色)**:

| 意见类型 | 检索结果 | 结论 | 颜色 |
|----------|----------|------|------|
| 删除某内容 | 旧词 `count == 0` | 已删净 | 🔵 蓝 |
| 删除某内容 | 旧词 `count > 0` | 没删干净, 列出残留页 | 🔴 红 |
| 改为新值 | 新值命中 且 旧值 `count == 0` | 已替换 | 🔵 蓝 |
| 改为新值 | 旧值仍在 或 新值缺失 | 未替换 | 🔴 红 |
| 新增内容 | 新内容命中 | 已新增 | 🔵 蓝 |
| 新增内容 | 缺失 | 未新增 | 🔴 红 |
| 多处一致性 | 所有出现位置都已改 | 全部一致 | 🔵 蓝 |
| 多处一致性 | 任一位置未跟上 | 不一致, 列出差异处 | 🔴 红 |
| 字面相似非同目标 / 无法机械判定 | —— | 需人来拍板 | 🟠 橙 |

- 命中页码即批注应落的页码。
- 一致性意见要把该内容在**所有出现位置**(主表/各附表/正文/附录)逐处检索, 只要有一处没跟上就整条标红。
- 不能机械检索的(如"图片是否补全""排版是否调整"), 用 Read 渲染页图像人工判断, 通常落红或橙。

**逻辑自洽规则(下结论前自检, 避免自相矛盾)**:
1. **无证据不标蓝** —— 蓝笔代表"已核对确认", 必须有 audit 命中/未命中作支撑; 凡是没查证的, 只能标红(待办)或橙(待人工确认), 绝不臆断为已改。
2. **红蓝互斥** —— 同一条意见的同一目标, 要么蓝要么红, 不能既说已改又说未改; 若证据冲突(部分位置改了部分没改), 按"未完全落实"整条标红并写明差异。
3. **橙是兜底** —— 只在"自动检索无法判定"或"字面相似但非同一对象"时用, 不要拿橙当默认。
4. **正文与批注一致** —— 批注里写的页码、数值、状态必须与 audit.json 的实际命中结果对得上, 不照搬意见原文的假设。
5. **可复核** —— 每条红/蓝结论都能回指到 audit.json 里的命中页与次数; 汇总时若被追问"凭什么标蓝", 答得出依据。

### Step 3.5 — 记入核销台账(首轮建账)
把 Step 3 的逐条结论登记进机器可读台账 `ledger.json`(与主文档同文件夹, 跨轮追踪的唯一事实来源):
```
# 1) 把意见清单写成 items.json (每条: source/opinion/action/keywords), 建账:
python scripts/ledger.py init --ledger ledger.json --items items.json --doc "主文档.pdf" --project "项目名"
# 2) 把本轮结论写成 results JSON (每条: id/color/pages/evidence/note), 记账:
python scripts/ledger.py update --ledger ledger.json --results round1.json --doc "主文档.pdf" --annotated "批注版.pdf"
```
- `action` 取值: `delete`(删除) / `replace`(改值) / `add`(新增) / `consistency`(多处一致) / `manual`(需人工)。
- `keywords` 是机器可重审的关键: `{"expect_absent": ["旧值"], "expect_present": ["新值"]}`
  —— 应消失的词与应出现的词。写得越准, 下一轮自动重审越省事。
- Step 3 已生成 audit 证据的, 直接填入 results 的 `evidence` 字段, 保证台账可回指。

### Step 4 — 构建批注 JSON
据核对结论生成 `annotations.json`(schema 见下)。每条批注定:`color`、`title`、
`body`(用 `\n` 分行)、`position`([x,y,w,h] 相对比例 0–1)。
**body 首行写台账编号**(如 `[OPN-003] 附表二 · 指标X:`), 让 PDF 批注与台账互相可回指。
位置经验:右侧表格批注多用 `x≈0.55–0.62, w≈0.36–0.43`;顶部说明用 `y≈0.05`;
同页多条批注错开 `y`, 避免重叠。

### Step 5 — 渲染输出
```
python scripts/annotate.py --pdf "主文档.pdf" --annotations annotations.json --out "主文档_红蓝批注版.pdf"
```
未批注页保持原样, 批注页叠加红/蓝/橙框。大文件可加 `--dpi 150`(默认)平衡清晰度与体积,
精细场景用 `--dpi 200`。

### Step 6 — 抽样自检 + 汇总
渲染后用 Read 打开 2–3 个批注页图像确认:框没遮原文、文字未截断、颜色语义正确。
最后给用户一份**核对汇总**:总页数、批注页清单、红笔项(待办)、蓝笔项(已确认)各几条,
红笔项逐条列出让用户优先处理。跨轮汇总直接用 `ledger.py report`(见下)。

## 跨轮模式(第 N 轮核对)

**触发条件**: 文件夹里已有 `ledger.json` + 一份新版主 PDF。此时**不要重新建账**,
走增量流程 —— 这是台账的价值所在:

```
# 1) 提取新版 PDF 文本
python scripts/extract_pdf.py --pdf "新版.pdf" --out pages.json
# 2) 机器重审台账全部条目(自动给建议色, 并用 !! 标出疑似回退项)
python scripts/ledger.py check --ledger ledger.json --pages pages.json --out round_check.json
# 3) 人工复核: 橙色项与 !! 项逐条用 Read 读页图判断, 修改 round_check.json 里的 color/note;
#    本轮有新增意见的, 在 round_check.json 追加无 id 但含 opinion/action/keywords 的条目
# 4) 记账(自动记录本轮迁移: 解决/仍未落实/回退/新增, 并存文档 SHA1)
python scripts/ledger.py update --ledger ledger.json --results round_check.json --doc "新版.pdf" --annotated "批注版R2.pdf"
# 5) 跨轮汇总(终端表格 + markdown 矩阵, 可再转 PDF 交付)
python scripts/ledger.py report --ledger ledger.json --md 台账汇总.md
```

**跨轮批注取舍**: 第 N 轮的 annotations.json 只标 ①仍未落实的红项 ②**本轮新解决**的蓝项
(展示进度) ③橙色人工项 ④回退项(红, 且 body 里写明"上轮已改好, 本轮又出现")。
前几轮就已解决的旧蓝项不再重复批注, 避免噪音 —— 它们的历史在台账里。

**回退项(regressed)是最高优先级发现**: 上轮核对为蓝、本轮又不满足, 说明改稿时把改好的
内容覆盖回去了。update 会单独列出, 汇报时必须置顶提醒。

## ledger.json schema(机器可读核销台账)

```json
{
  "schema_version": 1,
  "project": "XX设计导则修订",
  "master_doc": "导则V1.pdf",
  "rounds": [
    { "round": 1, "date": "2026-07-07 15:00", "doc": "导则V2.pdf", "doc_sha1": "a1b2c3",
      "annotated_pdf": "导则_红蓝批注版.pdf",
      "stats": { "resolved": 5, "still_open": 3, "regressed": 0, "manual": 2, "new": 0, "unchecked": 0 },
      "transitions": { "resolved": ["OPN-002"], "regressed": [], "still_open": ["OPN-001"], "manual": ["OPN-003"], "new": [] } }
  ],
  "items": [
    {
      "id": "OPN-001",
      "source": "专家意见.docx#1",
      "opinion": "取消指标X上限200, 改为'按需设置'",
      "action": "replace",
      "keywords": { "expect_absent": ["上限200"], "expect_present": ["按需设置"] },
      "status": "open",
      "current_color": "red",
      "pages": [26],
      "history": [
        { "round": 1, "color": "red", "pages": [26],
          "evidence": { "上限200": { "count": 1, "pages": [26], "expect": "absent" } },
          "note": "附表二未同步" }
      ]
    }
  ]
}
```

- `status`: `open`(红/待办) / `resolved`(蓝/已核销) / `manual`(橙/需人工) / `dropped`(作废, 不再核)。
- 每轮 `history` 条目都带证据(关键词命中页与次数)与当轮文档 SHA1, 任何结论可回溯到"哪一版文档、凭什么"。
- 台账是唯一事实来源: 批注 PDF、汇总报告都从它生成, 不要手改批注却不记账。

## annotations.json schema

```json
{
  "26": [
    {
      "color": "red",
      "title": "⚠ 需复核",
      "body": "附表二 · 指标 X:\n仍为旧值'上限 200'\n意见: 取消上限, 改为'按需设置'\n建议: 按需设置 / -\n(主表 P23、附表一 P30 已改, 唯附表二未同步)",
      "position": [0.55, 0.78, 0.43, 0.20]
    }
  ],
  "30": [
    {
      "color": "blue",
      "title": "✓ 已改",
      "body": "附表一 · 指标 X:\n已改为'按需设置' ✓\n(上限已取消, 旧值全文 0 处命中)",
      "position": [0.55, 0.78, 0.43, 0.14]
    }
  ],
  "102": [
    {
      "color": "orange",
      "title": "复核提示",
      "body": "此处'A 区接待室'与意见指向的\n'B 区接待区'名称相似但非同一对象,\n请人工确认是否需统一表述。",
      "position": [0.05, 0.05, 0.42, 0.20]
    }
  ]
}
```

## 要点速记
- **先核对再下色** —— 红蓝不是装饰, 是结论。查到才标。
- **言简意赅** —— 每条 3–6 行, 首行带台账编号, 写清"原状态 → 建议动作"。
- **位置避让原文**, 落在对应内容旁的空白处。
- **一致性意见要全查** —— 同一改动在所有出现位置(主表/各附表/正文/附录)逐处核对。
- **每轮必记账** —— 结论进 ledger.json 才算数; 有旧台账就走跨轮模式, 别重新建账。
- **回退项置顶汇报** —— 上轮蓝、本轮红 = 改稿改丢了, 比普通红项更急。
- 最终交付:批注版 PDF + 红笔待办清单 + 台账跨轮汇总, 让手下照着做。

## 常见问题
- **意见无页码** → 用 audit 的命中页定位;实在定不了的放第 1 页并在汇总里列出。
- **主 PDF 是扫描件取不到文字** → 先 OCR, 或意见改人工录入, 核对步骤靠人读图。
- **批注框遮挡原文** → 调 `position` 或升 `--dpi` 后再标。
- **字间有空格命中不到** → audit/ledger 已自动去空格, 关键词也尽量取短稳定子串。
- **意见作废不想再核** → 把台账里该条 `status` 改为 `dropped`, check/report 会自动跳过。
- **check 建议色不对** → 建议色只是机器初判, 人工复核后直接改 round_check.json 的 `color` 再 update; 台账以 update 记的为准。
