#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用 Markdown -> 中文 PDF 渲染器（审美迭代报告专用）

把一份审美分析 markdown 报告渲染成内嵌效果图、带中文字体的 PDF。
脱胎于 408 项目里硬编码的 gen_pdf.py，改为「解析任意 markdown」。

支持的 markdown 语法：
  # 标题            -> 居中大标题（仅首个 H1 视为封面主标题，其余 H1 当章节标题）
  ## 章节            -> H2（带下划线）
  ### 小节           -> H3
  **加粗**段首        -> 段落内行内加粗（简单处理：整段视情况加粗）
  - / * / • 列表项    -> 项目符号
  > 引用             -> 灰底引用块
  | 表格 |           -> 表格（首行表头）
  ![说明](图片路径)   -> 居中图片 + 图注（路径相对 --base 解析）
  ---               -> 分隔线
  普通文字            -> 正文段落

用法：
  python md_to_pdf.py 报告.md -o 报告.pdf --base 图片所在目录

  --base 不给时默认取 markdown 文件所在目录（图片通常和 md 放一起）。
"""
import argparse
import os
import re
import sys

from fpdf import FPDF

# ---- 中文字体（Windows 自带）。缺失时回退到任一存在的 ttf ----
FONT_CANDIDATES = {
    'msyh':   r'C:\Windows\Fonts\msyh.ttc',
    'msyhbd': r'C:\Windows\Fonts\msyhbd.ttc',
    'simhei': r'C:\Windows\Fonts\simhei.ttf',
    'simsun': r'C:\Windows\Fonts\simsun.ttc',
}


def _first_existing(*paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


class ReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        reg = FONT_CANDIDATES['msyh'] or _first_existing(*FONT_CANDIDATES.values())
        bold = FONT_CANDIDATES['msyhbd'] or reg
        hei = FONT_CANDIDATES['simhei'] or reg
        sun = FONT_CANDIDATES['simsun'] or reg
        if not reg:
            sys.exit('未找到任何中文字体，请在 FONT_CANDIDATES 中补充字体路径。')
        self.add_font('msyh', '', reg)
        self.add_font('msyh', 'B', bold if os.path.exists(bold) else reg)
        self.add_font('simhei', '', hei if os.path.exists(hei) else reg)
        self.add_font('simsun', '', sun if os.path.exists(sun) else reg)

    def footer(self):
        self.set_y(-15)
        self.set_font('msyh', '', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'- {self.page_no()} -', align='C')

    # ---- 文档块 ----
    def add_title(self, text):
        self.set_font('simhei', '', 18)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 12, text, align='C')
        self.ln(3)

    def add_meta(self, text):
        self.set_font('msyh', '', 10)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 6, text.strip(), align='C')
        self.ln(2)

    def add_separator(self):
        y = self.get_y()
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(6)

    def add_h2(self, text):
        if self.get_y() + 24 > self.h - self.b_margin:
            self.add_page()
        self.ln(4)
        self.set_font('simhei', '', 14)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 9, text)
        y = self.get_y()
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(4)

    def add_h3(self, text):
        if self.get_y() + 16 > self.h - self.b_margin:
            self.add_page()
        self.ln(2)
        self.set_font('msyh', 'B', 12)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 8, text)
        self.ln(1)

    def add_paragraph(self, text, bold=False):
        self.set_font('msyh', 'B' if bold else '', 10.5)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 6.5, text.strip())
        self.ln(1.5)

    def add_bullet(self, text):
        self.set_font('msyh', '', 10.5)
        self.set_text_color(30, 30, 30)
        # 缩进项目符号 + 悬挂对齐
        bullet_w = 6
        x0 = self.get_x()
        self.cell(bullet_w, 6.5, '•')
        self.set_x(x0 + bullet_w)
        self.multi_cell(0, 6.5, text.strip())
        self.ln(0.5)

    def add_quote(self, text):
        self.ln(1)
        self.set_font('msyh', '', 10.5)
        self.set_text_color(70, 70, 70)
        x0, y0 = self.l_margin, self.get_y()
        # 先量文字高度
        self.set_left_margin(self.l_margin + 6)
        self.set_x(self.l_margin + 6)
        self.multi_cell(0, 6.5, text.strip())
        y1 = self.get_y()
        self.set_left_margin(x0)
        # 左侧引用竖条
        self.set_draw_color(150, 150, 150)
        self.set_line_width(1.2)
        self.line(x0 + 1.5, y0, x0 + 1.5, y1)
        self.set_line_width(0.2)
        self.ln(2)

    def add_image_block(self, img_path, caption=None, max_w=170, max_h=115):
        from PIL import Image
        if not os.path.exists(img_path):
            self.add_paragraph(f'[缺失图片] {os.path.basename(img_path)}', bold=True)
            return
        try:
            img = Image.open(img_path)
            iw, ih = img.size
        except Exception as e:
            self.add_paragraph(f'[图片无法读取] {os.path.basename(img_path)}: {e}')
            return
        ratio = min(max_w / iw, max_h / ih)
        w, h = iw * ratio, ih * ratio
        if self.get_y() + h + 14 > self.h - self.b_margin:
            self.add_page()
        x = (self.w - w) / 2
        self.image(img_path, x=x, y=self.get_y(), w=w, h=h)
        self.set_y(self.get_y() + h + 2)
        if caption:
            self.set_font('msyh', '', 9)
            self.set_text_color(110, 110, 110)
            self.multi_cell(0, 5.5, caption, align='C')
        self.ln(3)

    def add_table(self, headers, rows):
        self.ln(2)
        n = max(len(headers), max((len(r) for r in rows), default=0))
        avail = self.w - self.l_margin - self.r_margin
        # 第一列略宽，其余均分
        if n <= 1:
            widths = [avail]
        else:
            first_w = min(40, avail * 0.28)
            other = (avail - first_w) / (n - 1)
            widths = [first_w] + [other] * (n - 1)
        line_h = 7

        def draw_row(cells, header=False):
            # 计算本行需要的最大行数（按字符宽度粗略估算换行）
            self.set_font('msyh', 'B' if header else '', 8.5)
            heights = []
            for i in range(n):
                txt = cells[i] if i < len(cells) else ''
                # 估算：每个字符宽度约 字号*0.5 (中文按全宽)，简单按文字宽度分行
                w = widths[i] - 2
                sw = self.get_string_width(txt) if txt else 0
                lines = max(1, int(sw / w) + (1 if sw % w else 0)) if w > 0 else 1
                heights.append(lines * line_h)
            row_h = max(heights) if heights else line_h
            if self.get_y() + row_h > self.h - self.b_margin:
                self.add_page()
            y0 = self.get_y()
            x = self.l_margin
            for i in range(n):
                txt = cells[i] if i < len(cells) else ''
                if header:
                    self.set_fill_color(238, 238, 238)
                    self.set_text_color(20, 20, 20)
                else:
                    self.set_fill_color(255, 255, 255)
                    self.set_text_color(35, 35, 35)
                self.set_draw_color(120, 120, 120)
                self.rect(x, y0, widths[i], row_h)
                # 文字垂直居中近似
                self.set_xy(x + 1, y0 + (row_h - line_h) / 2 if row_h > line_h else y0)
                self.multi_cell(widths[i] - 2, line_h, txt, align='C')
                x += widths[i]
            self.set_y(y0 + row_h)

        draw_row(headers, header=True)
        for r in rows:
            draw_row(r, header=False)
        self.ln(4)


# ---------------- Markdown 解析 ----------------
IMG_RE = re.compile(r'^!\[(.*?)\]\((.*?)\)\s*$')
TABLE_SEP_RE = re.compile(r'^\s*\|?[\s:|-]+\|?\s*$')


def strip_inline(text):
    """去掉行内 markdown 修饰符，保留纯文字（PDF 不渲染 **/`/[]()）。"""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'\1', text)
    text = text.replace('🟢', '[优]').replace('🟡', '[待改]').replace('🔴', '[问题]')
    text = text.replace('✅', '[符合]').replace('⚠️', '[偏差]').replace('❌', '[不符]')
    text = text.replace('★', '*').replace('☆', '·')
    text = text.replace('↔', '<->').replace('→', '->').replace('←', '<-')
    return text.strip()


def parse_table_cells(line):
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    return [strip_inline(c.strip()) for c in line.split('|')]


def render(md_path, pdf, base_dir):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.read().split('\n')

    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    i = 0
    first_h1_seen = False
    n = len(lines)
    while i < n:
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        # 空行
        if not stripped:
            i += 1
            continue

        # 分隔线
        if stripped in ('---', '***', '___'):
            pdf.add_separator()
            i += 1
            continue

        # 图片
        m = IMG_RE.match(stripped)
        if m:
            alt, path = m.group(1), m.group(2)
            if not os.path.isabs(path):
                path = os.path.join(base_dir, path)
            pdf.add_image_block(path, caption=strip_inline(alt) or None)
            i += 1
            continue

        # 表格：当前行像表格行且下一行是分隔行
        if stripped.startswith('|') and i + 1 < n and TABLE_SEP_RE.match(lines[i + 1].strip()) \
                and '|' in lines[i + 1]:
            headers = parse_table_cells(stripped)
            rows = []
            j = i + 2
            while j < n and lines[j].strip().startswith('|'):
                rows.append(parse_table_cells(lines[j].strip()))
                j += 1
            pdf.add_table(headers, rows)
            i = j
            continue

        # 标题
        if stripped.startswith('#'):
            level = len(stripped) - len(stripped.lstrip('#'))
            text = strip_inline(stripped[level:].strip())
            if level == 1:
                if not first_h1_seen:
                    pdf.add_title(text)
                    first_h1_seen = True
                else:
                    # 连续 H1（如副标题）也当大标题处理
                    pdf.add_title(text)
            elif level == 2:
                pdf.add_h2(text)
            else:
                pdf.add_h3(text)
            i += 1
            continue

        # 引用
        if stripped.startswith('>'):
            quote_lines = []
            while i < n and lines[i].strip().startswith('>'):
                quote_lines.append(strip_inline(lines[i].strip().lstrip('>').strip()))
                i += 1
            pdf.add_quote('\n'.join([q for q in quote_lines if q]))
            continue

        # 列表
        if re.match(r'^\s*[-*•]\s+', raw) or re.match(r'^\s*\d+\.\s+', raw):
            text = re.sub(r'^\s*([-*•]|\d+\.)\s+', '', raw)
            pdf.add_bullet(strip_inline(text))
            i += 1
            continue

        # 元信息行（**项目**: ...）整段当正文；段首加粗的整段加粗
        bold = stripped.startswith('**') and stripped.count('**') >= 2 and \
            stripped.endswith('**') and stripped.count('**') == 2
        pdf.add_paragraph(strip_inline(stripped), bold=bold)
        i += 1

    return pdf


def main():
    ap = argparse.ArgumentParser(description='Markdown -> 中文 PDF（审美迭代报告）')
    ap.add_argument('md', help='输入 markdown 文件')
    ap.add_argument('-o', '--out', help='输出 PDF 路径（默认同名 .pdf）')
    ap.add_argument('--base', help='图片基准目录（默认 markdown 所在目录）')
    args = ap.parse_args()

    md_path = os.path.abspath(args.md)
    if not os.path.exists(md_path):
        sys.exit(f'找不到文件：{md_path}')
    base_dir = os.path.abspath(args.base) if args.base else os.path.dirname(md_path)
    out = args.out or os.path.splitext(md_path)[0] + '.pdf'

    pdf = ReportPDF()
    render(md_path, pdf, base_dir)
    pdf.output(out)
    print(f'已生成 PDF：{out}')


if __name__ == '__main__':
    main()
