# arch-skills

**Give your agent a design studio's workflow.** / **把设计院的工作流，装进你的 Agent。**

One AI operating system for architecture, engineering and construction (AEC) studios — not a pile of loose skills, but a set organised along the studio's business chain: **leads → bids → design → review → delivery**. Every skill is hand-built by architect and interior designer [Gu Jun](https://www.chodo.ai), proven on real projects, and states who uses it, what it delivers and how it is accepted. Registry, scores, safety levels and the full system map: **https://arch-skills.com**

一套面向设计院的 AI 工作系统：按业务链 **商机 → 投标 → 设计 → 审核 → 交付** 组织，每个技能写明谁用、交什么、怎么验收。全部由建筑师顾骏亲手编写并在真实项目里跑通。三层架构、六维质量分、安全等级与落地流程见 **https://arch-skills.com**。

## The system / 三层架构

| Layer | What it is | On this repo / site |
|---|---|---|
| **L3 Applications · 业务应用** | Where the studio's money and work come from | The skills below, grouped by stage |
| **L2 Runtime · 运行底座** | Tasks, context, decision responsibility, long-term memory | `SKILL.md` triggers & flow · the project folder as context · safety levels + human in the loop · ledgers (`ledger.json`, cross-round deltas) |
| **L1 Ground truth · 目标与约束** | Goals, constraints, permissions, company facts | `tender-bid-review/company-profile/` (qualifications, track record, cost bands) · `asset-management-interior/references/aesthetic-canon.md` (design charter) · safety levels L1–L4 |

## Skills by stage / 按业务链分段

| Stage · 业务段 | Skill | 一句话 | Who · 谁用 | Level |
|---|---|---|---|---|
| 01 Leads · 商机 | [`software`](https://github.com/gujun1502/software) (separate repo) | 每日商机雷达：招标公告按设计费 / 业主 / 地区 / 资质口径自动筛 | 经营负责人 / 市场部 | L3 |
| 02 Bids · 投标 | [`tender-bid-review`](skills/tender-bid-review) | 招标陷阱审计：全生命周期复盘、评分反算、"能排第几"、投 / 不投 | 投标经理 / 经营负责人 | L2 |
| 02 Bids · 投标 | [`bid-pricing-engine`](skills/bid-pricing-engine) | 报价博弈引擎：密封投标最优报价的蒙特卡洛求解，含 React 交互引擎 | 投标经理 | L1 |
| 03 Design · 设计 | [`asset-management-interior`](skills/asset-management-interior) | 资管办公十六条：克制美学宪章、基准案例、构思 / 平面 / Moodboard 三条工作流 | 主创 / 方案组 | L1 |
| 03 Design · 设计 | [`create-draw`](skills/create-draw) | 概念图解：创意总监式评图圈注 + 关键词 → 概念图解，SVG / Excalidraw 输出 | 主创 / 创意总监 | L2 |
| 03 Design · 设计 | [`moodboard-aesthetic-iteration`](skills/moodboard-aesthetic-iteration) | Moodboard 审美打分：意向板锚定、多框架量化评分、跨轮整改追踪 | 主创 / 方案组 | L2 |
| 03 Design · 设计 | [`building-services-electrical`](skills/building-services-electrical) | 建筑师该懂的机电：HVAC / 给排水 / 电气 / 竖向交通 / 消防对空间的影响速查 | 建筑师 | L1 |
| 04 Review · 审核 | [`red-blue-pen-annotation`](skills/red-blue-pen-annotation) | 红蓝笔批注：主文档 + 修改意见 → 逐条核销的批注版 PDF，带跨轮台账 | 审图负责人 / 项目经理 | L2 |
| 05 Delivery · 交付 | [`design-text-typst`](skills/design-text-typst) | 设计文本 Typst 排版：A3 横版设计提案的网格版式与样张 | 文本组 / 项目经理 | L2 |
| S1 Base · 底座 | [`skill-safety-audit`](skills/skill-safety-audit) | Skill 安全审计器：密钥 / 个人信息 / 联网 / 删文件 / 执行 / 注入扫描，定级 L1–L4，脱敏 | 所有人，装之前 | L1 |
| S2 Knowledge · 知识 | [`article-academic`](skills/article-academic) | 学术深度文章：考据型非虚构的七幕结构与语调十律 | 作者 / 内容组 | L1 |

Each skill's `SKILL.md` states its trigger, flow, deliverable and pitfalls. The site card adds the acceptance rule and the anonymised verification record.

## Deploy in four steps / 装 → 配 → 跑 → 验

The forward-deployed way: prototype fast, iterate on real projects, keep safety and permissions as the floor.

```bash
# 1  装 · Install — pull, then audit before use
npx skills add gujun1502/arch-skills --all          # or --skill red-blue-pen-annotation
python skills/skill-safety-audit/audit.py skills/<name>

# 2  配 · Configure — write down the company facts once; every skill judges by them
#    skills/tender-bid-review/company-profile/company-profile.md   (资质 · 业绩口径 · 造价档位 · 团队)
#    skills/asset-management-interior/references/aesthetic-canon.md (审美宪章 = 设计约束)

# 3  跑 · Run — put the project in a folder, ask in plain words
#    project/ ├── 导则_v3.pdf  ├── 意见_业主.docx  └── ledger.json (上一轮台账, 可选)
#    › 做第二轮红蓝笔核对，用上一轮台账

# 4  验 · Accept — deliverable on disk, ledger updated, human in the loop for L3 / L4
#    output/ ├── 导则_v3_批注版.pdf  ├── ledger.json  └── 第2轮_核对汇总.md
```

Plain git works too: `git clone https://github.com/gujun1502/arch-skills ~/.claude/skills/arch-skills`. A skill is just a folder with a `SKILL.md`; Claude Code, Codex and Cursor all read it.

## Supply chain / 技能从哪里来，怎么保持一致

The author's local `~/.claude/skills` is the working copy (with real project files); this repository is the release copy. A sync script aligns the two before every release: strip project files, unify `name / license / author / homepage / source` front matter, replace the company name with "本单位", run every skill through the auditor, then push here and update the site registry. **What you install is what the author runs.**

本地工作副本 → 脱敏与统一（sync 脚本）→ 安全审计定级 → GitHub 托管 → 注册表打分上架。

## Safety levels / 安全等级

L1 read-only · L2 writes locally · L3 network · L4 executes / sends. The level says what a skill touches, not how good it is. L3 / L4 skills count as done only after a person checks. Spec: https://arch-skills.com/#docs

Related repositories by the same author / 同作者的其他仓库:
[`software`](https://github.com/gujun1502/software) daily tender radar ·
[`daily_stock_analysis`](https://github.com/gujun1502/daily_stock_analysis) multi-market stock analysis ·
[`content-pipeline`](https://github.com/gujun1502/content-pipeline) bilingual topic research pack ·
[`Bid-Pricing-Engine`](https://github.com/gujun1502/Bid-Pricing-Engine) standalone engine repo.

## Field notes / 验证

Every skill here was used on at least one real project before it was published. Project and client names are anonymised in this repository; the site lists the anonymised verification record, the deliverable and the acceptance rule for each skill.

本仓库里所有技能都先在真实项目里用过再发布；项目与业主名称已脱敏。

## License

Code: [MIT](LICENSE). Documentation (`SKILL.md`, `references/`, `templates/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — attribute to Gu Jun / arch-skills.com.

## Links

- System map, registry, scores, safety auditor: https://arch-skills.com
- Author: https://www.chodo.ai · Studio: https://t4-design.com · X: [@Gujun07783805](https://x.com/Gujun07783805)
- Newsletter: https://arch-skills.com/#subscribe
