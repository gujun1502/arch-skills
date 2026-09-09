// 设计文本样张 —— Typst 排版验证
#set page(width: 420mm, height: 297mm, margin: (x: 28mm, y: 24mm)) // A3 横排
#set text(font: ("Microsoft YaHei",), size: 10.5pt, fill: rgb("#2b2b2b"))

// ———— 封面区 ————
#grid(
  columns: (1fr, 2.2fr),
  column-gutter: 18mm,
  [
    #v(30mm)
    #text(size: 8.5pt, tracking: 3pt, fill: rgb("#8a8a8a"))[URBAN REGENERATION]
    #v(4mm)
    #line(length: 22mm, stroke: 0.6pt + rgb("#b3272d"))
    #v(6mm)
    #text(size: 30pt, weight: "bold")[历史街区\ 城市更新设计文本]
    #v(8mm)
    #text(size: 11pt, fill: rgb("#666"))[方案设计阶段 · 第一册]
    #v(1fr)
    #text(size: 9pt, fill: rgb("#8a8a8a"))[STUDIO NAME\ 2026.07]
  ],
  [
    #v(30mm)
    #text(size: 8.5pt, tracking: 3pt, fill: rgb("#8a8a8a"))[DESIGN STATEMENT]
    #v(4mm)
    #par(justify: true, leading: 0.9em)[
      本设计以"针灸式更新"为核心策略，在保留街区历史肌理的前提下，
      通过对院落单元的逐一梳理，植入文化展陈、社区服务与轻商业功能。
      排版逻辑遵循网格系统：左栏定位，右栏叙事，页眉页脚贯穿全册，
      形成理性、克制而富有节奏感的阅读秩序。
    ]
    #v(8mm)
    #grid(
      columns: (1fr, 1fr, 1fr),
      row-gutter: 3mm, column-gutter: 8mm,
      ..(
        ([保护建筑], [12 栋]),
        ([更新院落], [27 处]),
        ([新增公共空间], [8,400 ㎡]),
      ).map(((k, num)) => [
        #line(length: 100%, stroke: 0.4pt + rgb("#ccc"))
        #v(2mm)
        #text(size: 8.5pt, fill: rgb("#8a8a8a"))[#k]
        #v(1mm)
        #text(size: 16pt, weight: "bold", fill: rgb("#b3272d"))[#num]
      ])
    )
  ],
)

