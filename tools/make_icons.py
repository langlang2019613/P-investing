# -*- coding: utf-8 -*-
"""生成 PWA 图标：暗色圆角底 + 金色「飘」字。运行一次即可。"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path(__file__).parent.parent / "docs" / "icons"
OUT.mkdir(parents=True, exist_ok=True)
FONT = "C:/Windows/Fonts/msyhbd.ttc"  # 微软雅黑粗体

def make(size, name, pad_ratio=0.0):
    img = Image.new("RGB", (size, size), "#0b0e14")
    d = ImageDraw.Draw(img)
    # 金色渐变感：简单用两层圆角矩形
    m = int(size * 0.06)
    d.rounded_rectangle([m, m, size - m, size - m], radius=int(size * 0.18), fill="#12161f", outline="#d4af37", width=max(2, size // 90))
    font = ImageFont.truetype(FONT, int(size * 0.52))
    bbox = d.textbbox((0, 0), "飘", font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1]), "飘", font=font, fill="#d4af37")
    img.save(OUT / name)
    print("wrote", OUT / name)

make(192, "icon-192.png")
make(512, "icon-512.png")
make(180, "icon-180.png")
