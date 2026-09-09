# arch-skills

**Give your agent a design studio's workflow.** / **把设计院的工作流，装进你的 Agent。**

Hand-built agent skills for architecture, engineering and construction (AEC), written by architect and interior designer [Gu Jun](https://www.chodo.ai) and proven on real projects. Registry, scores and safety levels: **https://arch-skills.com**

建筑与室内设计（AEC）领域的 Agent 技能集，由建筑师顾骏亲手编写，全部在真实项目里跑通过。技能注册表、六维质量分与安全等级见 **https://arch-skills.com**。

## Install / 安装

```bash
# one skill
npx skills add gujun1502/arch-skills --skill red-blue-pen-annotation

# everything
npx skills add gujun1502/arch-skills --all

# or plain git
git clone https://github.com/gujun1502/arch-skills ~/.claude/skills/arch-skills
```

Works with Claude Code, Codex and Cursor — a skill is just a folder with a `SKILL.md`.
Run `python skills/skill-safety-audit/audit.py skills/<name>` before installing anything, ours included.

## Skills / 技能

| Skill | 一句话 | Level |
|---|---|---|
| [`red-blue-pen-annotation`](skills/red-blue-pen-annotation) | 红蓝笔批注：主文档 + 修改意见 → 逐条核销的批注版 PDF，带跨轮台账 | L2 |
| [`moodboard-aesthetic-iteration`](skills/moodboard-aesthetic-iteration) | Moodboard 审美打分：意向板锚定、多框架量化评分、跨轮整改追踪 | L2 |
| [`create-draw`](skills/create-draw) | 概念图解：创意总监式评图圈注 + 关键词 → 概念图解，SVG / Excalidraw 输出 | L2 |
| [`bid-pricing-engine`](skills/bid-pricing-engine) | 报价博弈引擎：密封投标最优报价的蒙特卡洛求解，含 React 交互引擎 | L1 |
| [`asset-management-interior`](skills/asset-management-interior) | 资管办公十六条：克制美学宪章、基准案例、构思 / 平面 / Moodboard 三条工作流 | L1 |
| [`building-services-electrical`](skills/building-services-electrical) | 建筑师该懂的机电：HVAC / 给排水 / 电气 / 竖向交通 / 消防对空间的影响速查 | L1 |
| [`tender-bid-review`](skills/tender-bid-review) | 招标陷阱审计：招投标全生命周期复盘、评分反算、规则性倾斜挖掘 | L2 |
| [`article-academic`](skills/article-academic) | 学术深度文章：考据型非虚构的七幕结构与语调十律 | L1 |
| [`design-text-typst`](skills/design-text-typst) | 设计文本 Typst 排版：A3 横版设计提案的网格版式与样张 | L2 |
| [`skill-safety-audit`](skills/skill-safety-audit) | Skill 安全审计器：密钥 / 个人信息 / 联网 / 删文件 / 执行 / 注入扫描，定级 L1–L4，脱敏 | L1 |

Safety levels — L1 read-only · L2 writes locally · L3 network · L4 executes / sends. See the spec at https://arch-skills.com/#docs.

Related repositories by the same author / 同作者的其他仓库:
[`software`](https://github.com/gujun1502/software) daily tender radar ·
[`daily_stock_analysis`](https://github.com/gujun1502/daily_stock_analysis) multi-market stock analysis ·
[`content-pipeline`](https://github.com/gujun1502/content-pipeline) bilingual topic research pack ·
[`Bid-Pricing-Engine`](https://github.com/gujun1502/Bid-Pricing-Engine) standalone engine repo.

## Field notes / 验证

Every skill here was used on at least one real project before it was published. Project and client names are anonymised in this repository; the site lists the anonymised verification record for each skill.

本仓库里所有技能都先在真实项目里用过再发布；项目与业主名称已脱敏。

## License

Code: [MIT](LICENSE). Documentation (`SKILL.md`, `references/`, `templates/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — attribute to Gu Jun / arch-skills.com.

## Links

- Registry, scores, safety auditor: https://arch-skills.com
- Author: https://www.chodo.ai · Studio: https://t4-design.com · X: [@Gujun07783805](https://x.com/Gujun07783805)
- Newsletter: https://arch-skills.com/#subscribe
