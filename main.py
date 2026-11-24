#!/usr/bin/env python3
"""Draw the 24 November 2026 world-news image (1024x1024 PNG).

Pure Python 3 standard library only: the PNG encoder is hand-written
(zlib + struct) and the text uses a tiny 5x7 bitmap font embedded below.
Fully deterministic: two runs produce byte-identical files.

Layout: header band with the date, hero panel (NATO space defence),
two rows of three story panels, footer strip (FIFA 2031 + US House).
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
NAVY      = (14, 26, 43)     # page background
HEADER    = (232, 185, 60)   # gold header band
HEADER_TX = (14, 26, 43)     # dark text on gold
PANEL     = (26, 46, 71)     # panel fill
PANEL_BD  = (61, 106, 158)   # panel border
WHITE     = (255, 255, 255)
SOFT      = (203, 220, 238)  # secondary text
GOLD      = (232, 185, 60)
CYAN      = (86, 199, 232)
GREEN     = (96, 205, 122)
ORANGE    = (245, 158, 66)
RED       = (235, 87, 87)
BLUE      = (80, 140, 220)
EARTH_GRN = (86, 176, 110)
EARTH_BLU = (52, 120, 200)

# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 bits, '1' = on.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '*': ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
}


def text_width(text, scale):
    return len(text) * 6 * scale - scale


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, color)

    def rect_outline(self, x, y, w, h, color, t=2):
        self.rect(x, y, w, t, color)
        self.rect(x, y + h - t, w, t, color)
        self.rect(x, y, t, h, color)
        self.rect(x + w - t, y, t, h, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        while True:
            for a in range(t):
                for b in range(t):
                    self.set(x + a, y + b, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, color)

    def circle_outline(self, cx, cy, r, color, t=2):
        for yy in range(cy - r - t, cy + r + t + 1):
            for xx in range(cx - r - t, cx + r + t + 1):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if (r - t) ** 2 <= d2 <= (r + t) ** 2:
                    self.set(xx, yy, color)

    def triangle(self, pts, color):
        (x0, y0), (x1, y1), (x2, y2) = pts
        ymin, ymax = min(y0, y1, y2), max(y0, y1, y2)
        for yy in range(ymin, ymax + 1):
            xs = []
            for (xa, ya), (xb, yb) in (((x0, y0), (x1, y1)),
                                       ((x1, y1), (x2, y2)),
                                       ((x2, y2), (x0, y0))):
                if ya == yb:
                    continue
                if min(ya, yb) <= yy <= max(ya, yb):
                    xs.append(xa + (xb - xa) * (yy - ya) / (yb - ya))
            if len(xs) >= 2:
                for xx in range(int(min(xs)), int(max(xs)) + 1):
                    self.set(xx, yy, color)

    def text(self, x, y, s, scale, color):
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[' '])
            for row in range(7):
                for col in range(5):
                    if glyph[row][col] == '1':
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, color)
            cx += 6 * scale

    def text_centered(self, cx, y, s, scale, color):
        self.text(cx - text_width(s, scale) // 2, y, s, scale, color)


# ---------------------------------------------------------------- icons
def draw_stars(c, x0, y0, x1, y1):
    # fixed deterministic star field
    pts = [(0.05, 0.15), (0.2, 0.07), (0.35, 0.2), (0.5, 0.08),
           (0.65, 0.18), (0.8, 0.06), (0.92, 0.22), (0.12, 0.35),
           (0.45, 0.3), (0.75, 0.35), (0.88, 0.45), (0.28, 0.5)]
    for fx, fy in pts:
        c.set(int(x0 + fx * (x1 - x0)), int(y0 + fy * (y1 - y0)), WHITE)


def icon_hero(c, x, y, w, h):
    """Earth + satellite in orbit, hero panel."""
    draw_stars(c, x, y, x + w, y + h)
    # Earth, lower left
    ex, ey, er = x + 150, y + h - 55, 78
    c.circle(ex, ey, er, EARTH_BLU)
    c.circle(ex - 28, ey - 18, 26, EARTH_GRN)
    c.circle(ex + 30, ey + 22, 20, EARTH_GRN)
    c.circle(ex + 22, ey - 34, 12, EARTH_GRN)
    c.circle_outline(ex, ey, er, CYAN, 3)
    # satellite, upper right
    sx, sy = x + w - 260, y + 45
    c.rect(sx - 70, sy + 18, 62, 26, GOLD)          # left panel
    c.rect(sx + 62, sy + 18, 62, 26, GOLD)          # right panel
    c.rect(sx - 26, sy + 8, 52, 44, WHITE)          # body
    c.rect(sx - 10, sy + 20, 20, 20, RED)           # core
    c.line(sx + 26, sy + 30, sx + 62, sy + 30, WHITE, 3)
    c.line(sx - 26, sy + 30, sx - 62, sy + 30, WHITE, 3)
    c.line(sx, sy + 8, sx, sy - 14, WHITE, 3)       # antenna
    c.circle(sx, sy - 18, 5, RED)
    # shield badge
    hx, hy = x + w - 120, y + h - 95
    c.rect(hx - 34, hy - 30, 68, 56, CYAN)
    c.triangle([(hx - 34, hy + 26), (hx + 34, hy + 26), (hx, hy + 58)], CYAN)
    c.rect(hx - 22, hy - 18, 44, 34, NAVY)
    c.triangle([(hx - 22, hy + 16), (hx + 22, hy + 16), (hx, hy + 40)], NAVY)
    c.text_centered(hx, hy - 12, "N", 3, CYAN)


def icon_chip(c, x, y, w, h):
    cx, cy = x + w // 2, y + h // 2 - 6
    for i in range(-1, 2):
        c.rect(cx - 52, cy - 26 + i * 26, 14, 8, GREEN)
        c.rect(cx + 38, cy - 26 + i * 26, 14, 8, GREEN)
    for i in range(-1, 2):
        c.rect(cx - 26 + i * 26, cy - 52, 8, 14, GREEN)
        c.rect(cx - 26 + i * 26, cy + 38, 8, 14, GREEN)
    c.rect(cx - 38, cy - 38, 76, 76, GREEN)
    c.rect(cx - 24, cy - 24, 48, 48, PANEL)
    c.text_centered(cx, cy - 12, "AI", 3, GREEN)
    # rising arrow
    c.line(cx + 52, cy + 34, cx + 92, cy - 6, GOLD, 4)
    c.line(cx + 92, cy - 6, cx + 74, cy - 6, GOLD, 4)
    c.line(cx + 92, cy - 6, cx + 92, cy + 12, GOLD, 4)


def icon_warship(c, x, y, w, h):
    cx, cy = x + w // 2, y + h // 2 + 4
    # hull (trapezoid: flat deck, tapered bow)
    c.triangle([(cx - 95, cy), (cx + 95, cy), (cx + 75, cy + 30)], BLUE)
    c.triangle([(cx - 95, cy), (cx + 75, cy + 30), (cx - 75, cy + 30)], BLUE)
    # deck + mast
    c.rect(cx - 30, cy - 28, 60, 28, WHITE)
    c.line(cx, cy - 28, cx, cy - 52, WHITE, 4)
    c.circle(cx, cy - 56, 5, RED)
    # drone above, right
    dx, dy = cx + 78, cy - 40
    c.rect(dx - 16, dy - 6, 32, 12, GOLD)
    c.line(dx - 24, dy - 8, dx - 10, dy - 8, GOLD, 3)
    c.line(dx + 10, dy - 8, dx + 24, dy - 8, GOLD, 3)
    # explosion star, left
    ex, ey = cx - 78, cy - 36
    for ang in range(8):
        import math
        a = ang * math.pi / 4
        c.line(ex, ey, ex + int(16 * math.cos(a)),
               ey + int(16 * math.sin(a)), ORANGE, 4)
    c.circle(ex, ey, 7, ORANGE)
    # waves
    for i, wy in enumerate((cy + 44, cy + 58)):
        for k in range(5):
            wx = cx - 100 + k * 44
            c.line(wx, wy, wx + 22, wy - 6 if i == 0 else wy + 4, CYAN, 3)


def icon_globe_cracked(c, x, y, w, h):
    cx, cy = x + w // 2, y + h // 2 - 6
    c.circle(cx, cy, 62, EARTH_BLU)
    c.circle(cx - 20, cy - 16, 22, EARTH_GRN)
    c.circle(cx + 24, cy + 20, 16, EARTH_GRN)
    c.circle_outline(cx, cy, 62, WHITE, 3)
    # crack
    pts = [(cx - 6, cy - 62), (cx + 8, cy - 34), (cx - 10, cy - 8),
           (cx + 12, cy + 18), (cx - 4, cy + 44), (cx + 6, cy + 62)]
    for a, b in zip(pts, pts[1:]):
        c.line(a[0], a[1], b[0], b[1], RED, 4)


def icon_radar_plane(c, x, y, w, h):
    cx, cy = x + w // 2, y + h // 2 - 6
    # radar arcs
    for r in (26, 44, 62):
        c.circle_outline(cx - 88, cy - 40, r, CYAN, 2)
    # plane (side view, pointing right)
    c.triangle([(cx - 70, cy + 6), (cx + 80, cy - 2), (cx - 70, cy + 22)], WHITE)
    c.triangle([(cx - 20, cy + 4), (cx + 10, cy - 34), (cx + 30, cy + 4)], WHITE)
    c.triangle([(cx - 60, cy + 14), (cx - 30, cy + 34), (cx - 10, cy + 14)], WHITE)
    c.circle(cx + 58, cy + 2, 5, RED)
    c.line(cx - 70, cy + 14, cx - 92, cy + 14, WHITE, 4)


def icon_jet_alert(c, x, y, w, h):
    cx, cy = x + w // 2, y + h // 2 - 6
    # warning triangle
    c.triangle([(cx - 6, cy - 66), (cx + 62, cy + 26), (cx - 74, cy + 26)], GOLD)
    c.triangle([(cx - 6, cy - 50), (cx + 48, cy + 16), (cx - 60, cy + 16)], PANEL)
    c.text_centered(cx - 6, cy - 40, "!", 4, GOLD)
    # jet
    jx, jy = cx - 8, cy + 52
    c.triangle([(jx - 78, jy), (jx + 78, jy - 6), (jx - 78, jy + 12)], WHITE)
    c.triangle([(jx - 10, jy - 2), (jx + 18, jy - 30), (jx + 34, jy - 2)], WHITE)
    c.line(jx - 78, jy + 6, jx - 96, jy + 6, ORANGE, 4)


def icon_handcuffs(c, x, y, w, h):
    cx, cy = x + w // 2, y + h // 2 - 6
    c.circle_outline(cx - 48, cy, 34, GOLD, 6)
    c.circle_outline(cx + 48, cy, 34, GOLD, 6)
    c.circle_outline(cx - 48, cy, 18, GOLD, 4)
    c.circle_outline(cx + 48, cy, 18, GOLD, 4)
    c.line(cx - 16, cy - 8, cx + 16, cy - 8, GOLD, 6)
    c.line(cx - 16, cy + 8, cx + 16, cy + 8, GOLD, 6)
    # drone overhead
    dx, dy = cx, cy - 50
    c.rect(dx - 14, dy - 5, 28, 10, CYAN)
    c.line(dx - 26, dy - 6, dx - 12, dy - 6, CYAN, 3)
    c.line(dx + 12, dy - 6, dx + 26, dy - 6, CYAN, 3)


# ---------------------------------------------------------------- panels
def panel(c, x, y, w, h, icon, lines, sub=None):
    c.rect(x, y, w, h, PANEL)
    c.rect_outline(x, y, w, h, PANEL_BD, 2)
    icon(c, x, y, w, 132)
    ly = y + 140
    for line in lines:
        c.text_centered(x + w // 2, ly, line, 3, WHITE)
        ly += 26
    if sub:
        c.text_centered(x + w // 2, ly + 2, sub, 2, SOFT)


def draw():
    c = Canvas(W, H, NAVY)

    # header band
    c.rect(0, 0, W, 100, HEADER)
    c.text_centered(W // 2, 14, "THE WORLD TODAY", 5, HEADER_TX)
    c.text_centered(W // 2, 60, "TUESDAY 24 NOVEMBER 2026", 3, HEADER_TX)

    # hero panel
    hx, hy, hw, hh = 16, 112, 992, 280
    c.rect(hx, hy, hw, hh, PANEL)
    c.rect_outline(hx, hy, hw, hh, GOLD, 3)
    icon_hero(c, hx, hy, hw, 190)
    c.text_centered(W // 2, hy + 196, "NATO VOWS SPACE DEFENCE", 4, WHITE)
    c.text_centered(W // 2, hy + 232,
                    "RUSSIA MAY LAUNCH NUCLEAR-ARMED SATELLITE", 2, SOFT)

    # panel rows
    pw, ph = 324, 248
    xs = (16, 350, 684)
    row1 = [
        (icon_chip, ["NVIDIA BRINGS BACK", "CEO JENSEN HUANG"],
         "STOCKS SURGE"),
        (icon_warship, ["UKRAINE SINKS", "RUSSIAN WARSHIP"],
         "DRONES STRIKE OFF LIBYA"),
        (icon_globe_cracked, ["COP31 COLLAPSES", "NO CLIMATE DEAL"],
         "TALKS END WITHOUT A DEAL"),
    ]
    row2 = [
        (icon_radar_plane, ["RUSSIAN MISSILES", "LAND IN POLAND"],
         "NATO SENDS AWACS PLANE"),
        (icon_jet_alert, ["SOUTH KOREA", "AIRSPACE ALERT"],
         "RUSSIAN JET ENTERS"),
        (icon_handcuffs, ["MEXICO NABS DRUG", "LORD CHAPO ISIDRO"],
         "CAPTURED IN SINALOA"),
    ]
    for (icon, lines, sub), x in zip(row1, xs):
        panel(c, x, 404, pw, ph, icon, lines, sub)
    for (icon, lines, sub), x in zip(row2, xs):
        panel(c, x, 664, pw, ph, icon, lines, sub)

    # footer strip
    fy = 924
    c.rect(0, fy, W, H - fy, HEADER)
    c.text_centered(W // 2, fy + 16,
                    "FIFA 2031 WOMEN'S CUP: USA, MEXICO, COSTA RICA, JAMAICA",
                    2, HEADER_TX)
    c.text_centered(W // 2, fy + 48,
                    "DEMOCRATS' BIGGEST HOUSE MAJORITY SINCE 1992",
                    2, HEADER_TX)

    return c


# ---------------------------------------------------------------- PNG encode
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(c):
    raw = bytearray()
    for y in range(c.h):
        raw.append(0)  # filter: none
        raw += c.px[y * c.w * 3:(y + 1) * c.w * 3]
    ihdr = struct.pack(">IIBBBBB", c.w, c.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return png


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    png = encode_png(draw())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)
    print(f"wrote {path}: {len(png)} bytes, {W}x{H}")


if __name__ == "__main__":
    main()
