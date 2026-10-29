# -*- coding: utf-8 -*-
"""生成应用图标 app.ico"""
from PIL import Image, ImageDraw

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 圆角底板（渐变蓝）
r = int(S * 0.22)
bg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
bd = ImageDraw.Draw(bg)
for y in range(S):
    t = y / S
    c = (int(47 + (36 - 47) * t), int(111 + (78 - 111) * t), int(237 + (216 - 237) * t), 255)
    bd.line([(0, y), (S, y)], fill=c)
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=r, fill=255)
img.paste(bg, (0, 0), mask)
d = ImageDraw.Draw(img)

W = 255
# 向下的箭头
cx = S // 2
top, bot = int(S * 0.20), int(S * 0.60)
stem_w = int(S * 0.105)
d.rounded_rectangle([cx - stem_w // 2, top, cx + stem_w // 2, bot - int(S * 0.06)],
                    radius=stem_w // 3, fill=(W, W, W, 255))
d.polygon([(cx - int(S * 0.155), bot - int(S * 0.16)),
           (cx + int(S * 0.155), bot - int(S * 0.16)),
           (cx, bot + int(S * 0.04))], fill=(W, W, W, 255))

# 承接的托盘（U 形）
t = int(S * 0.085)
y0 = int(S * 0.735)
d.rounded_rectangle([int(S * 0.20), y0, int(S * 0.80), y0 + t], radius=t // 2, fill=(W, W, W, 255))
d.rounded_rectangle([int(S * 0.20), int(S * 0.60), int(S * 0.20) + t, y0], radius=t // 2, fill=(W, W, W, 255))
d.rounded_rectangle([int(S * 0.80) - t, int(S * 0.60), int(S * 0.80), y0], radius=t // 2, fill=(W, W, W, 255))

img.save("app.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.resize((256, 256), Image.LANCZOS).save("app.png")       # macOS / Linux 用
img.resize((512, 512), Image.LANCZOS).save("docs/icon-512.png")
print("icon ok: app.ico / app.png / docs/icon-512.png")
