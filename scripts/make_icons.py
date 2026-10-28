#!/usr/bin/env python3
"""Draws RoHub's app icons (a three-tone cube on black) as PNG files, without any image library.

  python3 scripts/make_icons.py site/icons
"""
import math
import os
import struct
import sys
import zlib

BG = (0, 0, 0)
FACES = ((245, 245, 247), (180, 192, 255), (66, 99, 235))  # top, left, right
SS = 3  # samples per pixel, per axis, for smooth edges


def write_png(path, size, pixels):
    raw = b''.join(b'\x00' + bytes(pixels[y * size * 3:(y + 1) * size * 3]) for y in range(size))

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)

    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def span(poly, y):
    """Where the horizontal line at y crosses a convex polygon, as a half-open [start, end)."""
    xs = []
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if min(y1, y2) <= y < max(y1, y2):
            xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    return (min(xs), max(xs)) if len(xs) >= 2 else None


def render(size, scale):
    cx = cy = size / 2
    s = size * scale
    c = math.cos(math.pi / 6) * s
    cy += s * 0.04  # optical centering: the cube's top face reads as lighter
    top = [(cx, cy - s), (cx + c, cy - s / 2), (cx, cy), (cx - c, cy - s / 2)]
    left = [(cx - c, cy - s / 2), (cx, cy), (cx, cy + s), (cx - c, cy + s / 2)]
    right = [(cx, cy), (cx + c, cy - s / 2), (cx + c, cy + s / 2), (cx, cy + s)]
    acc = [0] * (size * size * 3)
    for j in range(size * SS):
        y = (j + 0.5) / SS
        row = (j // SS) * size
        for poly, color in zip((top, left, right), FACES):
            sp = span(poly, y)
            if not sp:
                continue
            first = max(0, math.ceil(sp[0] * SS - 0.5))
            last = min(size * SS, math.ceil(sp[1] * SS - 0.5))
            for i in range(first, last):
                p = (row + i // SS) * 3
                acc[p] += color[0] - BG[0]
                acc[p + 1] += color[1] - BG[1]
                acc[p + 2] += color[2] - BG[2]
    n = SS * SS
    return [min(255, BG[k % 3] + round(v / n)) for k, v in enumerate(acc)]


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'site/icons'
    os.makedirs(out, exist_ok=True)
    for name, size, scale in (('icon-192.png', 192, .30), ('icon-512.png', 512, .30),
                              ('icon-maskable-512.png', 512, .24), ('apple-touch-icon.png', 180, .30)):
        write_png(os.path.join(out, name), size, render(size, scale))
        print('wrote', name)
