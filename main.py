#!/usr/bin/env python3
"""Travel poster for Velmara, Isle of the Glass Light.

Draws one invented travel poster (1024x1024 PNG): a sunset over a
shimmering sea, a dark cliff with a tall lighthouse, and the place
name VELMARA set large across the upper sky. Text on the poster is
only the place name, one descriptor line, and one tiny footer line.

Deterministic: no network, no clock reads, no randomness. Drawn at
2x and downscaled for smooth edges. Standard library only: a
hand-rolled RGB pixel buffer with a built-in 5x7 bitmap font and a
struct+zlib PNG encoder, so it runs in a bare python3.13 image.
"""

import math
import os
import struct
import zlib

S = 2  # supersample factor; final image is 1024x1024
W, H = 1024, 1024
OUT = os.path.join(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"), "entry.png")

# Palette (6 main colours + 2 tints used for sea and waves).
INDIGO = (26, 28, 74)    # deep sky, top
VIOLET = (74, 52, 118)   # mid sky
ROSE = (178, 82, 100)    # low sky
AMBER = (242, 168, 84)   # horizon glow
SUN = (255, 222, 150)    # sun disc and lamp
SEA_TOP = (56, 88, 140)  # sea at the horizon
SEA_DEEP = (16, 26, 58)  # sea at the bottom
CLIFF = (14, 16, 40)     # cliff and lighthouse silhouette
CREAM = (250, 240, 214)  # poster text and frame
WAVE = (96, 126, 176)    # wave lines


def sc(v):
    return int(v * S)


def lerp(c0, c1, t):
    return (round(c0[0] + (c1[0] - c0[0]) * t),
            round(c0[1] + (c1[1] - c0[1]) * t),
            round(c0[2] + (c1[2] - c0[2]) * t))


def band_color(y, anchors):
    """Piecewise-linear colour at height y from (y, colour) anchors."""
    for i in range(len(anchors) - 1):
        y0, c0 = anchors[i]
        y1, c1 = anchors[i + 1]
        if y0 <= y <= y1:
            t = (y - y0) / float(y1 - y0) if y1 > y0 else 0.0
            return lerp(c0, c1, t)
    return anchors[-1][1]


# ---------------------------------------------------------------------------
# Built-in 5x7 bitmap font. Each glyph is 7 rows of 5 bits ("1" = ink).
# Covers A-Z, 0-9, space and every punctuation the poster uses.
# ---------------------------------------------------------------------------
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "\u00b7": ("00000", "00000", "00000", "01100", "00000", "00000", "00000"),
}
FONT_BITS = {}
for _ch, _rows in FONT.items():
    _bits = []
    for _r, _row in enumerate(_rows):
        for _c, _bit in enumerate(_row):
            if _bit == "1":
                _bits.append((_c, _r))
    FONT_BITS[_ch] = _bits
FONT_FALLBACK = FONT_BITS["?"] if "?" in FONT_BITS else FONT_BITS["A"]


# ---------------------------------------------------------------------------
# Pixel buffer canvas (RGB bytearray)
# ---------------------------------------------------------------------------
class Canvas:
    def __init__(self, w, h, fill=None):
        self.w = w
        self.h = h
        if fill is None:
            self.px = bytearray(w * h * 3)
        else:
            self.px = bytearray(bytes(fill) * w * h)

    def put(self, x, y, color, alpha=255):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            if alpha == 255:
                self.px[i] = color[0]
                self.px[i + 1] = color[1]
                self.px[i + 2] = color[2]
            else:
                ia = 255 - alpha
                self.px[i] = (color[0] * alpha + self.px[i] * ia) // 255
                self.px[i + 1] = (color[1] * alpha + self.px[i + 1] * ia) // 255
                self.px[i + 2] = (color[2] * alpha + self.px[i + 2] * ia) // 255

    def fill_rect(self, x0, y0, x1, y1, color, alpha=255):
        """Inclusive corners; clipped to the canvas."""
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w - 1, x1)
        y1 = min(self.h - 1, y1)
        if x1 < x0 or y1 < y0:
            return
        n = x1 - x0 + 1
        if alpha == 255:
            row = bytes(color) * n
            for y in range(y0, y1 + 1):
                base = (y * self.w + x0) * 3
                self.px[base:base + 3 * n] = row
        else:
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    self.put(x, y, color, alpha)

    def rect_outline(self, x0, y0, x1, y1, color, width=1, alpha=255):
        for k in range(width):
            self.fill_rect(x0 + k, y0 + k, x1 - k, y0 + k, color, alpha)
            self.fill_rect(x0 + k, y1 - k, x1 - k, y1 - k, color, alpha)
            self.fill_rect(x0 + k, y0 + k, x0 + k, y1 - k, color, alpha)
            self.fill_rect(x1 - k, y0 + k, x1 - k, y1 - k, color, alpha)

    def line(self, x0, y0, x1, y1, color, width=1, alpha=255):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        r = width // 2
        x, y = x0, y0
        while True:
            if r == 0:
                self.put(x, y, color, alpha)
            else:
                self.filled_circle(x, y, r, color, alpha)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def filled_circle(self, cx, cy, r, color, alpha=255):
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.fill_rect(cx - dx, cy + dy, cx + dx, cy + dy, color, alpha)

    def fill_polygon(self, pts, color, alpha=255):
        n = len(pts)
        if n < 3:
            return
        ymin = max(0, int(min(p[1] for p in pts)))
        ymax = min(self.h - 1, int(max(p[1] for p in pts)))
        for y in range(ymin, ymax + 1):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / float(y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.fill_rect(int(math.ceil(xs[i])), y,
                               int(math.floor(xs[i + 1])), y, color, alpha)


# ---------------------------------------------------------------------------
# Text (1024-space coordinates)
# ---------------------------------------------------------------------------
def scale_for(size):
    return max(1, round(size * S / 7))


def text_width(text, scale, tracking=0):
    if not text:
        return 0
    return len(text) * 6 * scale + (len(text) - 1) * tracking


def _fit_scale(text, size, max_w, tracking=0):
    s = scale_for(size)
    while s > 1 and text_width(text, s, tracking) > max_w:
        s -= 1
    return s


def draw_text(cv, x, y, text, scale, color, tracking=0, alpha=255):
    cx = x
    for ch in text:
        bits = FONT_BITS.get(ch, FONT_FALLBACK)
        for c, r in bits:
            cv.fill_rect(cx + c * scale, y + r * scale,
                         cx + c * scale + scale - 1,
                         y + r * scale + scale - 1, color, alpha)
        cx += 6 * scale + tracking


def ctext(cv, cx, y, text, size, color, tracking=0, max_w=None, alpha=255):
    """Horizontally centred text; cx, y, size, max_w in 1024-space units."""
    tr = sc(tracking)
    s = scale_for(size)
    if max_w is not None:
        s = _fit_scale(text, size, sc(max_w), tr)
    w = text_width(text, s, tr)
    draw_text(cv, sc(cx) - w // 2, sc(y), text, s, color, tr, alpha)


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------
def draw_sky(cv):
    anchors = [(0, INDIGO), (300, VIOLET), (480, ROSE), (640, AMBER)]
    for y in range(0, 640):
        cv.fill_rect(0, sc(y), sc(W) - 1, sc(y + 1) - 1, band_color(y, anchors))


def draw_sun(cv):
    cx, cy = sc(640), sc(520)
    # glow halo, fading outward
    cv.filled_circle(cx, cy, sc(172), (255, 200, 110), 36)
    cv.filled_circle(cx, cy, sc(140), (255, 205, 120), 60)
    cv.filled_circle(cx, cy, sc(118), (255, 212, 132), 100)
    cv.filled_circle(cx, cy, sc(100), SUN)


def draw_sea(cv):
    anchors = [(640, SEA_TOP), (1024, SEA_DEEP)]
    for y in range(640, 1024):
        cv.fill_rect(0, sc(y), sc(W) - 1, sc(y + 1) - 1, band_color(y, anchors))
    # sun reflection path: widening dashes down from the horizon
    for y in range(660, 1000, 26):
        w = 70 + (y - 660) * 0.55
        cv.fill_rect(sc(int(640 - w / 2)), sc(y),
                     sc(int(640 + w / 2)), sc(y + 7), AMBER, 150)
    # calm wave lines, broken into segments
    for y in (700, 770, 840, 910, 970):
        for x0, x1 in ((40, 300), (380, 700), (760, 990)):
            cv.fill_rect(sc(x0), sc(y), sc(x1), sc(y + 2), WAVE, 110)


def draw_cliff_and_lighthouse(cv):
    # dark cliff silhouette, left side, rising out of the sea
    cliff = [(0, 1024), (0, 660), (80, 610), (170, 575), (260, 600),
             (340, 660), (380, 720), (400, 1024)]
    cv.fill_polygon([(sc(x), sc(y)) for x, y in cliff], CLIFF)
    # lighthouse tower, tapered, standing on the cliff top
    tower = [(150, 580), (190, 580), (184, 402), (156, 402)]
    cv.fill_polygon([(sc(x), sc(y)) for x, y in tower], CLIFF)
    # gallery rail
    cv.fill_rect(sc(146), sc(394), sc(194), sc(402), CLIFF)
    # lamp room glow + lamp
    cv.filled_circle(sc(170), sc(384), sc(42), SUN, 60)
    cv.fill_rect(sc(156), sc(368), sc(184), sc(394), CLIFF)
    cv.fill_rect(sc(160), sc(374), sc(180), sc(388), SUN)
    # roof
    roof = [(152, 368), (188, 368), (170, 352)]
    cv.fill_polygon([(sc(x), sc(y)) for x, y in roof], CLIFF)
    # faint beam from the lamp across the evening sky
    beam = [(192, 378), (760, 330), (760, 442), (192, 394)]
    cv.fill_polygon([(sc(x), sc(y)) for x, y in beam], SUN, 22)


def draw_birds(cv):
    for bx, by in ((880, 300), (930, 342), (832, 352)):
        cv.line(sc(bx - 12), sc(by), sc(bx), sc(by + 8), CLIFF, sc(3))
        cv.line(sc(bx), sc(by + 8), sc(bx + 12), sc(by), CLIFF, sc(3))


def draw_text_block(cv):
    # hero name, large across the upper sky
    ctext(cv, 512, 84, "VELMARA", 120, CREAM, tracking=6, max_w=920)
    # one short descriptor, flanked by thin rules
    ctext(cv, 512, 232, "ISLE OF THE GLASS LIGHT", 26, CREAM,
          tracking=4, max_w=880)
    cv.fill_rect(sc(150), sc(244), sc(190), sc(246), CREAM, 180)
    cv.fill_rect(sc(834), sc(244), sc(874), sc(246), CREAM, 180)
    # tiny footer: invented coordinates / region
    ctext(cv, 512, 972, "62 N \u00b7 THE SHIMMERING SEA", 18, CREAM,
          tracking=2, max_w=900, alpha=230)


def downsample(px, sw, sh):
    """Box-average 2x2 downsample of an RGB bytearray to half size."""
    w, h = sw // 2, sh // 2
    out = bytearray(w * h * 3)
    for y in range(h):
        r0 = (2 * y) * sw * 3
        r1 = (2 * y + 1) * sw * 3
        o = y * w * 3
        for x in range(w):
            s = 2 * x * 3
            out[o] = (px[r0 + s] + px[r0 + s + 3] + px[r1 + s] + px[r1 + s + 3] + 2) // 4
            out[o + 1] = (px[r0 + s + 1] + px[r0 + s + 4] + px[r1 + s + 1] + px[r1 + s + 4] + 2) // 4
            out[o + 2] = (px[r0 + s + 2] + px[r0 + s + 5] + px[r1 + s + 2] + px[r1 + s + 5] + 2) // 4
            o += 3
    return out


def _png_chunk(ctype, data):
    chunk = struct.pack(">I", len(data)) + ctype + data
    chunk += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
    return chunk


def write_png(path, rgb, w, h):
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + _png_chunk(b"IHDR", ihdr)
           + _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + _png_chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    cv = Canvas(sc(W), sc(H))
    draw_sky(cv)
    draw_sun(cv)
    draw_sea(cv)
    draw_cliff_and_lighthouse(cv)
    draw_birds(cv)
    draw_text_block(cv)
    # thin poster frame
    cv.rect_outline(sc(24), sc(24), sc(1000), sc(1000), CREAM, sc(3), 200)
    small = downsample(cv.px, sc(W), sc(H))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    size = write_png(OUT, small, W, H)
    print("wrote", OUT, size, "bytes")


if __name__ == "__main__":
    main()
