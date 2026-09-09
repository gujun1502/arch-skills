# -*- coding: utf-8 -*-
"""
drawkit.py — create-draw skill 的核心绘图库。

一个元素模型，两个后端：
  - SVG  -> PNG (cairosvg 优先, PyMuPDF 兜底)   —— 可直接发团队/业主的成品图
  - .excalidraw JSON                            —— 可在 VS Code / excalidraw.com 继续拖改

坐标系：始终以底图 PNG 的像素为准（1 SVG 单位 = 1 底图像素），
模型用 Read 工具看底图 PNG 时估的坐标可直接使用。

用法（批注脚本模式，推荐——脚本本身就是可编辑的参数文件）:

    from drawkit import Canvas, prep
    base, w, h = prep("plan.pdf", page=0, dpi=150, out="base.png")
    c = Canvas(base)
    c.circle(420, 310, 60, color=c.RED)
    c.bubble(1, 480, 250, color=c.RED)
    c.note(1, "此处承重墙被隔断打断，需复核结构")
    c.arrow(700, 500, 900, 400, color=c.BLUE, dashed=True)
    c.save("annotated")   # -> annotated.svg / annotated.png / annotated.excalidraw

CLI:
    python drawkit.py prep <input.pdf|jpg|png> [--page N] [--dpi 150] [--out base.png]
    python drawkit.py info <file.excalidraw>        # 读回用户手改的画布
    python drawkit.py rasterize <file.svg> [--out x.png] [--scale 2]
"""

import base64
import json
import math
import os
import random
import sys
import time

# ---------------------------------------------------------------- 颜色语义
RED = "#D0342C"      # 问题 / 拆除 / 否定
BLUE = "#1A56DB"     # 方案 / 新建 / 动线 / 肯定的改法
ORANGE = "#E8890C"   # 待确认 / 需业主或结构复核
GREEN = "#0E9F6E"    # 保留 / 做得好的部分
GRAY = "#6B7280"     # 现状 / 中性参考线

_FONT = "Microsoft YaHei, Noto Sans SC, sans-serif"


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _text_w(s, fs):
    """估算字符串像素宽（CJK 全宽，其余按 0.55 em）。"""
    w = 0.0
    for ch in str(s):
        w += fs * (1.0 if ord(ch) > 0x2E80 else 0.55)
    return w


def _wrap(s, fs, max_w):
    """按估算宽度折行，返回行列表。"""
    lines, cur, cw = [], "", 0.0
    for ch in str(s):
        w = fs * (1.0 if ord(ch) > 0x2E80 else 0.55)
        if ch == "\n" or cw + w > max_w:
            lines.append(cur)
            cur, cw = ("" if ch == "\n" else ch), (0 if ch == "\n" else w)
        else:
            cur += ch
            cw += w
    if cur:
        lines.append(cur)
    return lines or [""]


def _svg_text(x, y, s, size, color, anchor="start", bold=False, halo=True):
    """SVG 文字，halo=True 时加白色描边光晕（照片底图上保证可读）。"""
    fw = ' font-weight="bold"' if bold else ""
    out = []
    for i, line in enumerate(str(s).split("\n")):
        ly = y + i * size * 1.3
        common = (f'x="{x}" y="{ly}" font-size="{size}" '
                  f'font-family="{_FONT}" text-anchor="{anchor}"{fw}')
        if halo:
            out.append(f'<text {common} fill="none" stroke="#FFFFFF" '
                       f'stroke-width="{size * 0.22:.1f}" stroke-linejoin="round" '
                       f'opacity="0.85">{_esc(line)}</text>')
        out.append(f'<text {common} fill="{color}">{_esc(line)}</text>')
    return "".join(out)


def _circled(n):
    """1 -> ①  … 20 -> ⑳，超出则返回 (n)。"""
    return chr(0x2460 + n - 1) if 1 <= n <= 20 else f"({n})"


# ---------------------------------------------------------------- 底图准备
def prep(src, page=0, dpi=150, out="base.png", max_px=2200):
    """把 PDF 的某一页 / JPG / PNG 统一转成 PNG 底图。

    返回 (png_path, width, height)。宽高即批注坐标系的边界。
    max_px: 底图最长边上限，过大的图会等比缩小（坐标系随之缩小，先 prep 再看图再定位）。
    """
    ext = os.path.splitext(src)[1].lower()
    if ext == ".pdf":
        import fitz
        doc = fitz.open(src)
        pg = doc[page]
        pix = pg.get_pixmap(dpi=dpi)
        if max(pix.width, pix.height) > max_px:
            zoom = (dpi / 72.0) * max_px / max(pix.width, pix.height)
            pix = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        pix.save(out)
        return out, pix.width, pix.height
    else:
        from PIL import Image
        im = Image.open(src)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        if max(im.size) > max_px:
            r = max_px / max(im.size)
            im = im.resize((round(im.width * r), round(im.height * r)))
        im.save(out)
        return out, im.width, im.height


def rasterize(svg_path, out=None, scale=2.0):
    """SVG -> PNG。cairosvg 优先（pattern/虚线支持完整），PyMuPDF 兜底。"""
    out = out or os.path.splitext(svg_path)[0] + ".png"
    data = open(svg_path, "rb").read()
    try:
        import cairosvg
        import re
        m = re.search(rb'width="(\d+)', data)
        w = int(m.group(1)) if m else 1000
        cairosvg.svg2png(bytestring=data, write_to=out, output_width=round(w * scale))
    except Exception:
        import fitz
        d = fitz.open(svg_path)
        d[0].get_pixmap(matrix=fitz.Matrix(scale, scale)).save(out)
    return out


# ---------------------------------------------------------------- 画布
class Canvas:
    RED, BLUE, ORANGE, GREEN, GRAY = RED, BLUE, ORANGE, GREEN, GRAY

    def __init__(self, base=None, width=None, height=None, bg="#FFFFFF",
                 notes_panel=True, panel_width=380):
        """base: 底图 PNG 路径（None = 空白画布，用于概念推演）。
        notes_panel: save 时是否在右侧自动排版编号意见栏。"""
        self._svg = []        # svg 片段
        self._ex = []         # excalidraw 元素
        self._files = {}      # excalidraw 内嵌图片
        self._notes = []      # (编号, 颜色, 文字)
        self._patterns = set()
        self._n = 0
        self._rng = random.Random(20260707)
        self.bg = bg
        self.notes_panel = notes_panel
        self.panel_width = panel_width
        if base:
            from PIL import Image
            im = Image.open(base)
            self.w, self.h = im.size
            self._embed_image(base, 0, 0, self.w, self.h)
        else:
            self.w = width or 1600
            self.h = height or 900

    # ------------------------------------------------------------ 内部
    def _id(self):
        self._n += 1
        return f"cd{self._n:04d}"

    def _base(self, typ, x, y, w, h, color=GRAY, bgc="transparent",
              fill="solid", sw=2, ss="solid", extra=None):
        el = {
            "id": self._id(), "type": typ, "x": round(x, 1), "y": round(y, 1),
            "width": round(w, 1), "height": round(h, 1), "angle": 0,
            "strokeColor": color, "backgroundColor": bgc, "fillStyle": fill,
            "strokeWidth": sw, "strokeStyle": ss, "roughness": 1, "opacity": 100,
            "groupIds": [], "frameId": None, "roundness": None,
            "seed": self._rng.randint(1, 2 ** 31), "version": 1,
            "versionNonce": self._rng.randint(1, 2 ** 31), "isDeleted": False,
            "boundElements": None, "updated": int(time.time() * 1000),
            "link": None, "locked": False,
        }
        if extra:
            el.update(extra)
        self._ex.append(el)
        return el

    def _ex_text(self, x, y, s, fs, color, align="left"):
        lines = str(s).split("\n")
        tw = max(_text_w(l, fs) for l in lines)
        th = fs * 1.25 * len(lines)
        if align == "middle":
            x -= tw / 2
        self._base("text", x, y, tw, th, color=color, extra={
            "text": str(s), "fontSize": fs, "fontFamily": 2,
            "textAlign": "center" if align == "middle" else "left",
            "verticalAlign": "top", "containerId": None,
            "originalText": str(s), "autoResize": True, "lineHeight": 1.25,
        })

    def _ex_line(self, pts, color, sw=2, ss="solid", arrow_end=False,
                 bgc="transparent", fill="solid"):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, y0 = min(xs), min(ys)
        rel = [[round(p[0] - x0, 1), round(p[1] - y0, 1)] for p in pts]
        self._base("arrow" if arrow_end else "line", x0, y0,
                   max(xs) - x0, max(ys) - y0, color=color, sw=sw, ss=ss,
                   bgc=bgc, fill=fill, extra={
                       "points": rel, "lastCommittedPoint": None,
                       "startBinding": None, "endBinding": None,
                       "startArrowhead": None,
                       "endArrowhead": "arrow" if arrow_end else None,
                   })

    def _embed_image(self, path, x, y, w, h):
        b64 = base64.b64encode(open(path, "rb").read()).decode()
        mime = "image/jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "image/png"
        self._svg.append(
            f'<image href="data:{mime};base64,{b64}" x="{x}" y="{y}" '
            f'width="{w}" height="{h}"/>')
        fid = f"f{self._id()}"
        ts = int(time.time() * 1000)
        self._files[fid] = {"mimeType": mime, "id": fid,
                            "dataURL": f"data:{mime};base64,{b64}",
                            "created": ts, "lastRetrieved": ts}
        self._base("image", x, y, w, h, color="transparent", extra={
            "status": "saved", "fileId": fid, "scale": [1, 1]})

    def _dash(self, dashed):
        return ' stroke-dasharray="12 7"' if dashed else ""

    # ------------------------------------------------------------ 图元
    def image(self, path, x, y, w=None, h=None):
        """向画布追加一张图（概念推演 V1→V2→V3 横排、意向图对照用）。"""
        from PIL import Image
        im = Image.open(path)
        if w and not h:
            h = round(w * im.height / im.width)
        if h and not w:
            w = round(h * im.width / im.height)
        w, h = w or im.width, h or im.height
        self._embed_image(path, x, y, w, h)
        return w, h

    def circle(self, cx, cy, r, ry=None, color=RED, sw=3, dashed=False):
        """圈注。ry 给出时为椭圆。红实线圈=问题；蓝虚线圈=建议范围。"""
        ry = ry or r
        self._svg.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{ry}" fill="none" '
            f'stroke="{color}" stroke-width="{sw}"{self._dash(dashed)}/>')
        self._base("ellipse", cx - r, cy - ry, 2 * r, 2 * ry, color=color,
                   sw=sw, ss="dashed" if dashed else "solid")

    def box(self, x, y, w, h, color=RED, sw=3, dashed=False):
        """矩形框选。"""
        self._svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" '
            f'stroke="{color}" stroke-width="{sw}"{self._dash(dashed)}/>')
        self._base("rectangle", x, y, w, h, color=color, sw=sw,
                   ss="dashed" if dashed else "solid",
                   extra={"roundness": {"type": 3}})

    def xmark(self, cx, cy, size=26, color=RED, sw=3):
        """X 叉 = 拆除 / 取消。"""
        s = size / 2
        self._svg.append(
            f'<g stroke="{color}" stroke-width="{sw}" stroke-linecap="round">'
            f'<line x1="{cx-s}" y1="{cy-s}" x2="{cx+s}" y2="{cy+s}"/>'
            f'<line x1="{cx+s}" y1="{cy-s}" x2="{cx-s}" y2="{cy+s}"/></g>')
        self._ex_line([(cx - s, cy - s), (cx + s, cy + s)], color, sw)
        self._ex_line([(cx + s, cy - s), (cx - s, cy + s)], color, sw)

    def arrow(self, x1, y1, x2, y2, color=BLUE, sw=3, dashed=True,
              curve=0, label=None):
        """箭头 = 动线 / 移位方向 / 视线。curve: 正值向左弯的弧度像素偏移。
        默认蓝虚线（方案语义）；红实线箭头用于指出问题指向。"""
        if curve:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            L = math.hypot(x2 - x1, y2 - y1) or 1
            nx, ny = -(y2 - y1) / L, (x2 - x1) / L
            cx_, cy_ = mx + nx * curve, my + ny * curve
            path = f"M {x1} {y1} Q {cx_} {cy_} {x2} {y2}"
            ang = math.atan2(y2 - cy_, x2 - cx_)
        else:
            path = f"M {x1} {y1} L {x2} {y2}"
            ang = math.atan2(y2 - y1, x2 - x1)
        a, sp = 13 + sw * 1.5, 0.46
        p1 = (x2 - a * math.cos(ang - sp), y2 - a * math.sin(ang - sp))
        p2 = (x2 - a * math.cos(ang + sp), y2 - a * math.sin(ang + sp))
        self._svg.append(
            f'<path d="{path}" fill="none" stroke="{color}" '
            f'stroke-width="{sw}"{self._dash(dashed)}/>'
            f'<polygon points="{x2},{y2} {p1[0]:.1f},{p1[1]:.1f} '
            f'{p2[0]:.1f},{p2[1]:.1f}" fill="{color}"/>')
        if curve:
            pts = []
            for i in range(9):
                t = i / 8
                bx = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx_ + t ** 2 * x2
                by = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy_ + t ** 2 * y2
                pts.append((bx, by))
        else:
            pts = [(x1, y1), (x2, y2)]
        self._ex_line(pts, color, sw, "dashed" if dashed else "solid",
                      arrow_end=True)
        if label:
            # 标签放在线的实际中点（曲线取贝塞尔 t=0.5 顶点）向上方法线偏移 20px
            L = math.hypot(x2 - x1, y2 - y1) or 1
            nx, ny = -(y2 - y1) / L, (x2 - x1) / L
            if ny > 0:
                nx, ny = -nx, -ny
            if curve:
                mx = 0.25 * x1 + 0.5 * cx_ + 0.25 * x2
                my = 0.25 * y1 + 0.5 * cy_ + 0.25 * y2
            else:
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            self.text(mx + nx * 22, my + ny * 22, label, size=17,
                      color=color, align="middle")

    def leader(self, tx, ty, lx, ly, s, color=RED, size=17):
        """引线标注：从目标点 (tx,ty) 拉线到 (lx,ly)，接水平短横线 + 文字。
        文字自动放在横线端；lx > tx 时文字向右展开，反之向左。"""
        d = 1 if lx >= tx else -1
        ex = lx + d * 26
        self._svg.append(
            f'<g stroke="{color}" stroke-width="2" fill="none">'
            f'<circle cx="{tx}" cy="{ty}" r="4" fill="{color}"/>'
            f'<path d="M {tx} {ty} L {lx} {ly} L {ex} {ly}"/></g>')
        anchor = "start" if d > 0 else "end"
        self._svg.append(_svg_text(ex + d * 6, ly + size * 0.35, s, size,
                                   color, anchor=anchor))
        self._base("ellipse", tx - 4, ty - 4, 8, 8, color=color, bgc=color)
        self._ex_line([(tx, ty), (lx, ly), (ex, ly)], color, 2)
        w = _text_w(s, size)
        self._ex_text(ex + d * 6 - (0 if d > 0 else w), ly - size * 0.62,
                      s, size, color)

    def bubble(self, n, cx, cy, color=RED, r=15):
        """编号泡 ①②③ —— 与 note(n, ...) 的文字意见一一挂接。"""
        self._svg.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#FFFFFF" '
            f'fill-opacity="0.92" stroke="{color}" stroke-width="2.5"/>'
            f'<text x="{cx}" y="{cy + r * 0.42}" font-size="{r * 1.25}" '
            f'fill="{color}" font-family="{_FONT}" text-anchor="middle" '
            f'font-weight="bold">{n}</text>')
        self._base("ellipse", cx - r, cy - r, 2 * r, 2 * r, color=color,
                   bgc="#FFFFFF", sw=2)
        self._ex_text(cx, cy - r * 0.66, str(n), round(r * 1.1), color,
                      align="middle")

    def note(self, n, s, color=None):
        """登记编号 n 的文字意见，save 时排进右侧意见栏。"""
        self._notes.append((n, color or (self._ex and RED) or RED, s))

    def hatch(self, points, color=RED, opacity=0.85):
        """剖面线填充多边形 = 拆除范围(红) / 新建范围(蓝)。points: [(x,y),...]"""
        key = color.lstrip("#")
        if key not in self._patterns:
            self._patterns.add(key)
        pstr = " ".join(f"{x},{y}" for x, y in points)
        self._svg.append(
            f'<polygon points="{pstr}" fill="url(#hatch-{key})" '
            f'fill-opacity="{opacity}" stroke="{color}" stroke-width="2"/>')
        pts = list(points) + [points[0]]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        rel = [[p[0] - min(xs), p[1] - min(ys)] for p in pts]
        self._base("line", min(xs), min(ys), max(xs) - min(xs),
                   max(ys) - min(ys), color=color, bgc=color, fill="hachure",
                   extra={"points": rel, "lastCommittedPoint": None,
                          "startBinding": None, "endBinding": None,
                          "startArrowhead": None, "endArrowhead": None})

    def zone(self, cx, cy, rx, ry, label, color=BLUE):
        """分区气泡：半透明椭圆 + 居中区名（平面功能分区用）。"""
        self._svg.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{color}" '
            f'fill-opacity="0.13" stroke="{color}" stroke-width="2" '
            f'stroke-dasharray="8 6"/>')
        self._base("ellipse", cx - rx, cy - ry, 2 * rx, 2 * ry, color=color,
                   bgc=color, fill="solid", ss="dashed",
                   extra={"opacity": 30})
        self.text(cx, cy, label, size=max(15, min(rx, ry) // 3),
                  color=color, align="middle", bold=True)

    def dim(self, x1, y1, x2, y2, s, color=GRAY, size=15):
        """尺寸线：两端带垂直短刻度，中间上方标文字。"""
        ang = math.atan2(y2 - y1, x2 - x1)
        nx, ny = -math.sin(ang) * 7, math.cos(ang) * 7
        self._svg.append(
            f'<g stroke="{color}" stroke-width="1.6">'
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'
            f'<line x1="{x1-nx}" y1="{y1-ny}" x2="{x1+nx}" y2="{y1+ny}"/>'
            f'<line x1="{x2-nx}" y1="{y2-ny}" x2="{x2+nx}" y2="{y2+ny}"/></g>')
        mx, my = (x1 + x2) / 2 + nx * 2.2, (y1 + y2) / 2 + ny * 2.2
        self.text(mx, my, s, size=size, color=color, align="middle")
        self._ex_line([(x1, y1), (x2, y2)], color, 2)
        self._ex_line([(x1 - nx, y1 - ny), (x1 + nx, y1 + ny)], color, 2)
        self._ex_line([(x2 - nx, y2 - ny), (x2 + nx, y2 + ny)], color, 2)

    def text(self, x, y, s, size=18, color=RED, align="left", bold=False):
        """自由文字。align: left | middle。y 为文字基线附近的中心。"""
        anchor = "middle" if align == "middle" else "start"
        self._svg.append(_svg_text(x, y + size * 0.35, s, size, color,
                                   anchor=anchor, bold=bold))
        self._ex_text(x, y - size * 0.62, s, size, color, align=align)

    def title(self, s, sub=None):
        """画布顶部标题条（概念推演 / 无底图场景用）。"""
        self.text(self.w / 2, 34, s, size=26, color="#111827",
                  align="middle", bold=True)
        if sub:
            self.text(self.w / 2, 64, sub, size=16, color=GRAY, align="middle")

    # ------------------------------------------------------------ 输出
    def _panel_svg(self):
        """右侧意见栏，返回 (svg片段, 面板高度)。"""
        if not self._notes:
            return "", 0
        px = self.w + 24
        pw = self.panel_width - 48
        y = 46
        frag = [f'<text x="{px}" y="{y}" font-size="20" fill="#111827" '
                f'font-family="{_FONT}" font-weight="bold">批注说明</text>']
        self._ex_text(px, y - 14, "批注说明", 20, "#111827")
        y += 18
        for n, color, s in self._notes:
            y += 14
            lines = _wrap(s, 15, pw - 44)
            frag.append(
                f'<circle cx="{px + 13}" cy="{y + 7}" r="12" fill="#FFFFFF" '
                f'stroke="{color}" stroke-width="2"/>'
                f'<text x="{px + 13}" y="{y + 12}" font-size="14" fill="{color}" '
                f'font-family="{_FONT}" text-anchor="middle" '
                f'font-weight="bold">{n}</text>')
            self._ex_text(px + 13, y - 1, str(n), 13, color, align="middle")
            for i, line in enumerate(lines):
                frag.append(
                    f'<text x="{px + 34}" y="{y + 12 + i * 21}" font-size="15" '
                    f'fill="#1F2937" font-family="{_FONT}">{_esc(line)}</text>')
            self._ex_text(px + 34, y - 1, "\n".join(lines), 15, "#1F2937")
            y += 12 + len(lines) * 21
        return "".join(frag), y + 30

    def save(self, stem, png_scale=2.0):
        """输出 stem.svg + stem.png + stem.excalidraw，返回 png 路径。"""
        panel, ph = self._panel_svg()
        total_w = self.w + (self.panel_width if panel else 0)
        total_h = max(self.h, ph)
        defs = ""
        if self._patterns:
            pats = []
            for key in self._patterns:
                pats.append(
                    f'<pattern id="hatch-{key}" patternUnits="userSpaceOnUse" '
                    f'width="9" height="9" patternTransform="rotate(45)">'
                    f'<line x1="0" y1="0" x2="0" y2="9" stroke="#{key}" '
                    f'stroke-width="1.6"/></pattern>')
            defs = f"<defs>{''.join(pats)}</defs>"
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" '
               f'height="{total_h}" viewBox="0 0 {total_w} {total_h}">{defs}'
               f'<rect width="{total_w}" height="{total_h}" fill="{self.bg}"/>'
               + "".join(self._svg) + panel + "</svg>")
        with open(f"{stem}.svg", "w", encoding="utf-8") as f:
            f.write(svg)
        doc = {"type": "excalidraw", "version": 2,
               "source": "create-draw-skill",
               "elements": self._ex,
               "appState": {"gridSize": None,
                            "viewBackgroundColor": self.bg},
               "files": self._files}
        with open(f"{stem}.excalidraw", "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False)
        png = rasterize(f"{stem}.svg", f"{stem}.png", scale=png_scale)
        self._png = png
        self._png_scale = png_scale
        return png

    def crop(self, x, y, w, h, out):
        """从最近 save 的 PNG 裁一块局部（坐标仍用底图像素），用于放大复看。"""
        from PIL import Image
        s = self._png_scale
        im = Image.open(self._png)
        box = (max(0, round(x * s)), max(0, round(y * s)),
               min(im.width, round((x + w) * s)),
               min(im.height, round((y + h) * s)))
        im.crop(box).save(out)
        return out


# ---------------------------------------------------------------- 读回画布
def info(path):
    """解析 .excalidraw，把用户手改/手画的元素还原成可读的坐标语义清单。"""
    doc = json.load(open(path, encoding="utf-8"))
    out = []
    for el in doc.get("elements", []):
        if el.get("isDeleted"):
            continue
        t = el["type"]
        x, y = round(el["x"]), round(el["y"])
        w, h = round(el.get("width", 0)), round(el.get("height", 0))
        col = el.get("strokeColor", "")
        sem = {RED: "红/问题", BLUE: "蓝/方案", ORANGE: "橙/待确认",
               GREEN: "绿/保留", GRAY: "灰/现状"}.get(col.upper(), col)
        if t == "text":
            out.append(f'text "{el.get("text", "")}" @({x},{y}) {sem}')
        elif t == "image":
            out.append(f"image @({x},{y}) {w}x{h}")
        elif t in ("arrow", "line", "freedraw"):
            pts = el.get("points", [])
            if pts:
                seg = (f"({x + round(pts[0][0])},{y + round(pts[0][1])}) -> "
                       f"({x + round(pts[-1][0])},{y + round(pts[-1][1])})")
                closed = len(pts) > 2 and pts[0] == pts[-1]
                out.append(f"{t} {seg}{' [闭合多边形]' if closed else ''} "
                           f"{sem} {el.get('strokeStyle', '')}")
            else:
                out.append(f"{t} @({x},{y}) {sem}")
        else:
            out.append(f"{t} @({x},{y}) {w}x{h} {sem} "
                       f"{el.get('strokeStyle', '')}")
    return out


# ---------------------------------------------------------------- CLI
if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    cmd = args[0]
    if cmd == "prep":
        src = args[1]
        kw = {}
        if "--page" in args:
            kw["page"] = int(args[args.index("--page") + 1])
        if "--dpi" in args:
            kw["dpi"] = int(args[args.index("--dpi") + 1])
        out = (args[args.index("--out") + 1] if "--out" in args
               else "base.png")
        p, w, h = prep(src, out=out, **kw)
        print(f"{p} {w}x{h}")
    elif cmd == "info":
        for line in info(args[1]):
            print(line)
    elif cmd == "rasterize":
        out = args[args.index("--out") + 1] if "--out" in args else None
        scale = float(args[args.index("--scale") + 1]) if "--scale" in args else 2.0
        print(rasterize(args[1], out, scale))
    else:
        print(f"unknown command: {cmd}")
        sys.exit(1)
