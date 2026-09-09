# 四个场景模板

坐标全部是示意值——真实坐标来自"看底图立判断"那一步，不要照抄。
写脚本前先读 `creative-language.md`（评图五维、大师锚点、方向句式都在那里）。
公共开头：

```python
import sys; sys.path.insert(0, r"C:\Users\Jun\.claude\skills\create-draw\scripts")
sys.stdout.reconfigure(encoding="utf-8")   # Windows 控制台打印中文防乱码
from drawkit import Canvas, prep
```

## 场景一：效果图创意评图（旗舰）

目标：创意总监在图上画的那几笔 + 成体系的方向意见。只画不评是半成品。

```python
base, w, h = prep(r"D:\proj\客厅效果图.jpg", out=r"D:\proj\base.png")
c = Canvas(base)

# 1) 焦点之争：红圈争夺焦点的两个元素之一
c.circle(550, 430, 190, ry=130, color=c.RED)
c.bubble(1, 740, 320, color=c.RED)
c.note(1, "沙发体量偏大且色值过重，与背景墙争夺焦点，画面无主")

# 2) 光的动作：橙色带标出建议的光走向（洗墙/光缝/聚焦）
c.hatch([(300,90),(1180,90),(1180,130),(300,130)], color=c.ORANGE, opacity=0.5)
c.bubble(2, 240, 110, color=c.ORANGE)
c.note(2, "顶面加一道洗墙光，让背景墙肌理接管焦点", color=c.ORANGE)

# 3) 视线：入户视点 → 视觉焦点，蓝虚线箭头
c.arrow(150, 750, 900, 350, color=c.BLUE, dashed=True, label="入户视线")

# 4) 材质替换：蓝引线（写"A→B"，情绪理由放 note）
c.leader(980, 620, 760, 720, "大理石→暖灰微水泥", color=c.BLUE, size=16)
c.bubble(3, 560, 720, color=c.BLUE)
c.note(3, "地面反光过强与静态氛围冲突，转向哑光的安静", color=c.BLUE)

# 5) 亮点：绿圈（有肯定，意见才有公信力）
c.circle(950, 335, 170, ry=200, color=c.GREEN)
c.bubble(4, 1120, 150, color=c.GREEN)
c.note(4, "窗洞比例与框景处理到位，是这张图最值得放大的特质", color=c.GREEN)

png = c.save(r"D:\proj\评图_v1")
```

**回复中必附的文字意见（结构照抄，内容按 creative-language.md 的纪律写）：**

```
## 这张图的志向
一句话：它想成为什么（意见全部相对志向给）

## 评图五维
- 构图 / 材质 / 光影 / 色彩 / 风格锚点：每维一句有判断的话

## 创意方向（三条拉开档位：收 / 进 / 破，各用轮盘里不同的方法生成）
1. 改法 + 大师参照（具体手法）+ 预期效应 ｜ 死穴：一句
2. … ｜ 死穴：…
3. … ｜ 死穴：…

## 方向自评（三分制，禁止同分）
张力解决度 / 落地性 / 被讲述的潜力 → 推荐哪条 + 这条赌的是什么
```

需要量化打分或多轮迭代时，衔接 moodboard-aesthetic-iteration。

### 场景一补充：方向板（方向确定后的修改表达，图主文辅）

评图定了方向之后，修改建议不写长文——做一块**方向板**：
每行 = `现状局部（从底图 crop 放大）→ 蓝箭头 → 方向示意`。
方向示意优先用 `references/anchors/<谱系>/` 里的参考图（先 Glob 扫一眼有没有图），
没有图就用图元画抽象草图。文字只留一句引领语。

```python
from PIL import Image
im = Image.open(r"D:\proj\base.png")
im.crop((360, 300, 940, 700)).save(r"D:\proj\局部_沙发区.png")   # 现状局部

c = Canvas(width=1900, height=640, notes_panel=False)
c.title("方向板 01 · 沙发区：从'满'走向'静'")

c.image(r"D:\proj\局部_沙发区.png", 60, 100, w=760)              # 左：现状
c.text(440, 560, "现状：体量重、焦点争", size=17, color=c.RED, align="middle")

c.arrow(860, 330, 1030, 330, color=c.BLUE, dashed=False, sw=4)   # 中：一根箭头
c.text(945, 295, "换低背+洗墙光", size=16, color=c.BLUE, align="middle")

# 右：方向——锚点库有图用图，没图用图元画抽象示意
c.image(r"C:\Users\Jun\.claude\skills\create-draw\references\anchors"
        r"\van-duysen-pawson\01-天光洗墙.jpg", 1080, 100, w=760)
c.text(1460, 560, "锚点：Van Duysen 静默天花", size=17, color=c.BLUE, align="middle")

c.save(r"D:\proj\方向板_01")
```

一块板只讲一条方向；多条方向就出多块板（方向板_01/02/03），比一张大图塞满更有力。

## 场景二：概念生成（从零起，餐巾纸草图的精确化）

目标：用户给"空间类型 + 关键词/情绪"，产出一张概念图解板。
先按 creative-language.md 第六节走完思考骨架（关键词→主张→原型→三策略→锚点），再画。

```python
c = Canvas(width=2000, height=900, notes_panel=True, panel_width=420)
c.title("地下酒窖品鉴室 · 概念图解", sub="概念主张：这不是酒窖，是一座往下走的教堂")

# 空间原型区（左 2/3）：纯图元画抽象原型
c.box(80, 110, 1180, 640, color=c.GRAY, sw=2)                      # 场地框
c.arrow(160, 200, 400, 430, color=c.BLUE, curve=-40, label="下行序列")  # 动线=身体经验
c.zone(560, 520, 150, 100, "品鉴厅", color=c.BLUE)
c.zone(950, 300, 120, 85, "藏酒廊", color=c.BLUE)
c.hatch([(700,110),(730,110),(730,470),(700,470)], color=c.ORANGE, opacity=0.5)  # 光缝
c.leader(715, 180, 880, 150, "唯一天光缝：光的动作=切", color=c.ORANGE, size=15)
c.circle(560, 520, 40, color=c.RED)                                 # 张力点
c.bubble(1, 640, 460, color=c.RED)
c.note(1, "张力点：长桌尽端唯一被光点亮的位置，仪式的锚")
c.bubble(2, 340, 280, color=c.BLUE)
c.note(2, "动线策略：先压低（2.1m 洞口）再向下释放，参照 Zumthor 序列压缩", color=c.BLUE)
c.bubble(3, 760, 130, color=c.ORANGE)
c.note(3, "光策略：全程烛级照度，只给一道天光缝，参照安藤的光缝语言", color=c.ORANGE)
c.bubble(4, 1000, 380, color=c.GREEN)
c.note(4, "材质策略：火山岩+夯土+做旧黄铜，重量与时间的情绪", color=c.GREEN)

png = c.save(r"D:\proj\概念图解_v1")
```

要点：
- 原型必须能被一句话复述（"一条下行轴 + 一道光缝 + 一个被点亮的尽端"）；
- 概念主张写进 title 副标题，让图自己会说话；
- 交付时文字部分给：主张、三策略、锚点声明（站在谁肩上、差异在哪）、推演钩子。

## 场景三：概念推演（无限画布 V1→V2→V3）

目标：方案演化排成一屏——比的是关系与演化逻辑，不是渲染质量。

```python
c = Canvas(width=2000, height=760, notes_panel=False)
c.title("入口空间概念推演", sub="V1 对称仪式感 → V2 偏轴引导 → V3 光缝切入")

# 三个版本横排：有图用 image()，没图就用图元画抽象小图
c.image(r"D:\proj\v1.png", 60, 110, w=560)     # 或 c.box + zone + arrow 画抽象版
c.image(r"D:\proj\v2.png", 720, 110, w=560)
c.image(r"D:\proj\v3.png", 1380, 110, w=560)

# 版本间演化箭头 + 演化要点（蓝=方案语义）
c.arrow(630, 380, 712, 380, color=c.BLUE, dashed=False)
c.arrow(1290, 380, 1372, 380, color=c.BLUE, dashed=False)
c.text(671, 340, "打破对称", size=16, color=c.BLUE, align="middle")
c.text(1331, 340, "引入天光", size=16, color=c.BLUE, align="middle")

# 每版结论：红=放弃原因，橙=部分保留，蓝=推进方向
c.text(340, 660, "V1：仪式感足但太酒店化", size=17, color=c.RED, align="middle")
c.text(1000, 660, "V2：动线活了，界面仍平", size=17, color=c.ORANGE, align="middle")
c.text(1660, 660, "V3：推荐深化方向", size=17, color=c.BLUE, align="middle")

png = c.save(r"D:\proj\概念推演_v1-v3")
```

横排间距 ≥60px；演化要点一律蓝色；推荐版本的结论句要给出"为什么是它"。

## 场景四：平面概念图解（附带能力）

目标：把 PDF 平面当**概念底图**讲空间叙事——分区、动线、视线序列、光的进入。
不做施工图纠错（墙体拆改、规范审查交给 red-blue-pen-annotation 和审图流程）。

```python
base, w, h = prep(r"D:\proj\平面.pdf", page=0, dpi=150, out=r"D:\proj\base.png")
c = Canvas(base)

c.zone(300, 480, 140, 95, "静区", color=c.BLUE)
c.zone(760, 420, 110, 80, "动区", color=c.BLUE)
c.arrow(180, 620, 520, 460, color=c.BLUE, curve=50, label="进入序列")
c.arrow(520, 460, 850, 420, color=c.BLUE, curve=-30)
c.arrow(400, 500, 900, 300, color=c.BLUE, dashed=True, label="对角视线")
c.hatch([(860,200),(900,200),(900,500),(860,500)], color=c.ORANGE, opacity=0.5)
c.bubble(1, 940, 180, color=c.ORANGE)
c.note(1, "东侧引入一条光带，动区获得时间感", color=c.ORANGE)

png = c.save(r"D:\proj\平面概念_v1")
```

要点：
- 动线箭头穿越墙体处必须有洞（门洞/开口），箭头穿实墙是语义错误，复看时专项检查；
- 图面密集处用 `leader` 把文字引到空白区；
- 若用户真正要的是施工问题批注，说明本技能的边界并建议对应流程。
