---
name: design-text-typst
description: >-
  设计文本 Typst 排版：用 Typst 代替 InDesign 排 A3 横版的建筑 / 室内设计提案文本——封面双栏网格、
  三格关键数据条、左栏定位右栏叙事、页眉页脚贯穿全册、Microsoft YaHei 中英混排不乱码。
  当用户要"排一本设计文本 / 方案文本 / 设计提案 / 画册 / 介绍册"、把 Markdown 或 Word 稿变成 A3 横版 PDF、
  或说"用 Typst 排版"时使用。
  Typeset A3-landscape architecture / interior design booklets with Typst instead of InDesign:
  cover grid, key-figure strip, label/narrative columns, running heads, CJK-safe fonts.
---

# 设计文本 Typst 排版 / Design Booklet Typesetter

设计院的方案文本一直靠 InDesign 手排：改一处文字，整册重新对版。Typst 把版式写成代码，
文本改一处，整册重排，`typst compile` 几秒出 PDF。本技能提供一套经真实项目验证的 A3 横版网格与样张。

## 版式约定 / Layout conventions

- **页面**：A3 横排 420 × 297 mm，边距 x 28 mm / y 24 mm。
- **字体**：Microsoft YaHei（Windows）或 Noto Sans SC，正文 10.5 pt，色 `#2b2b2b`；灰色标签 `#8a8a8a` 8.5 pt，字距 3 pt，全大写英文。
- **强调色**：一处正红 `#b3272d`，只用于短横线与关键数字，其余全灰阶。
- **封面网格**：左右两栏 `1fr : 2.2fr`，栏距 18 mm。左栏 = 英文小标签 → 红短线 → 大标题（30 pt 粗）→ 阶段说明 → 底部落款；右栏 = DESIGN STATEMENT 段落 + 三格关键数据条（细灰线 / 小标签 / 16 pt 红色数字）。
- **内页**：左栏定位（章节名、编号、图纸说明），右栏叙事与图；页眉页脚贯穿全册。
- **节奏**：一页只讲一件事；数据用数字说话；留白是版式的一部分。

## 用法 / Usage

1. 安装 Typst（`winget install typst` 或 https://typst.app）。
2. 复制 `样张.typ` 为你的文本，替换标题、说明、数据与落款；字体名按本机实际改。
3. 编译：
   ```bash
   typst compile 样张.typ 样张.pdf
   ```
4. 内页照封面网格延伸：`#grid(columns:(1fr, 2.2fr), column-gutter:18mm, [左栏], [右栏])`；
   图片用 `#image("xx.jpg", width:100%)`，跨页大图单独一页。
5. 要中英双语时，英文标签走 `tracking: 3pt` 的灰色小字，中文走正文字重。

## 在 Agent 里 / With an agent

把 Markdown 或 Word 稿交给 Claude Code，说"按 design-text-typst 排成 A3 横版文本"。
它会：读稿 → 按章节拆页 → 套网格生成 `.typ` → 编译 → 抽首页文字自检乱码 → 交付 PDF。

## 文件 / Files

- `样张.typ` — 封面样张源码（Typst）。
- `样张.png` — 样张渲染效果。

## 验证 / Field notes

已用于三本文本：一本老青旅酒店裙房改造提案、一本上市集团总部画册、一本资管公司介绍册。
三本的封面与版式都从这一页样张长出来。
