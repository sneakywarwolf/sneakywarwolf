#!/usr/bin/env python3
"""Generate assets/banner-{dark,light}.svg (terminal-style profile card).

Edit INFO below and re-run:  python3 scripts/banner.py
The VISUAL.MAP portrait comes from assets/portrait-points.json (scripts/portrait.py).
Its dots loop: static noise -> shield with keyhole -> network mesh -> portrait.
"""
import json
import math
import random
from html import escape

W, H = 848, 428

# (key, value) rows for the SYSTEM.INFO panel
INFO = [
    ("Subject", "Nirmal Chakraborty"),
    ("Handle", "sneakywarwolf"),
    ("Role", "Technical Team Lead · Offensive Security"),
    ("Focus", "Web · API · Mobile · Network VAPT"),
    ("Certs", "CRTE · eWPTXv2 · CEH(P) · CC · DIAT"),
    ("Status", "Testing + Learning + Evolving"),
    ("Leads.With", "People · Communication · Delivery"),
    ("Tool.Recon", "ReconCraft · SFAC"),
    ("Tool.Mobile", "PinSlayer (Frida)"),
    ("Core.Lang", "Python"),
    ("Core.GUI", "PyQt5"),
    ("Grid.Blog", "sneakywarwolf.github.io"),
    ("Grid.LinkedIn", "/in/nirmalchak"),
    ("Grid.GitHub", "sneakywarwolf"),
]

THEMES = {
    "dark": dict(bg="#0b1220", panel="#0f1a2e", stroke="#1e2d47", title="#7d8aa5",
                 key="#7d8aa5", val="#f2f6ff", accent="#22d3ee", dots="#00e5a0",
                 live="#ff4d6d", ok="#00e5a0", dim="#5b6a86", dot_op=0.9),
    "light": dict(bg="#f3f6fb", panel="#ffffff", stroke="#d0d7de", title="#57606a",
                  key="#57606a", val="#0d1117", accent="#0b7a8f", dots="#0a8f68",
                  live="#cf222e", ok="#0a8f68", dim="#8c959f", dot_op=0.9),
}

BAYER = [[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
         [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
         [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
         [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]]


BOX_W, BOX_H = 250, 254     # VISUAL.MAP drawing area (matches scripts/portrait.py)
LOOP = 18                   # seconds per animation cycle
# keyTimes for: noise, shield, shield, mesh, mesh, portrait, portrait, noise
KEYTIMES = "0;.08;.24;.32;.46;.56;.94;1"


def hilbert(x, y, n=256):
    """Hilbert-curve index; sorting every stage by it keeps each dot's path short."""
    d, s = 0, n // 2
    x, y = int(max(0, min(n - 1, x))), int(max(0, min(n - 1, y)))
    while s:
        rx, ry = int(x & s > 0), int(y & s > 0)
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                x, y = s - 1 - x, s - 1 - y
            x, y = y, x
        s //= 2
    return d


def ordered(pts):
    return sorted(pts, key=lambda p: hilbert(p[0] * 255 / BOX_W, p[1] * 255 / BOX_H))


def resample(pts, n):
    """Return exactly n points from pts, evenly picked along the Hilbert order."""
    pts = ordered(pts)
    return [pts[int(i * len(pts) / n)] for i in range(n)]


def mesh_dots():
    """Network graph: hub, inner ring, outer ring, joined by dotted links."""
    cx, cy = BOX_W / 2, BOX_H / 2
    nodes = [(cx, cy)]
    nodes += [(cx + 62 * math.cos(a), cy + 62 * math.sin(a)) for a in (math.pi / 3 * k + math.pi / 6 for k in range(6))]
    nodes += [(cx + 112 * math.cos(a), cy + 112 * math.sin(a)) for a in (math.pi / 3 * k for k in range(6))]
    links = [(0, i) for i in range(1, 7)]
    links += [(i, i % 6 + 1) for i in range(1, 7)]
    links += [(7 + k, 1 + k) for k in range(6)] + [(7 + k, 1 + (k - 1) % 6) for k in range(6)]
    pts = []
    for a, b in links:
        (x0, y0), (x1, y1) = nodes[a], nodes[b]
        steps = int(math.hypot(x1 - x0, y1 - y0) / 3.2)
        pts += [(x0 + (x1 - x0) * t / steps, y0 + (y1 - y0) * t / steps) for t in range(steps + 1)]
    for i, (x, y) in enumerate(nodes):
        r = 11 if i == 0 else 7
        for gx in range(-r, r + 1, 2):
            for gy in range(-r, r + 1, 2):
                if gx * gx + gy * gy <= r * r:
                    pts.append((x + gx, y + gy))
    return pts


def noise_dots(n, seed=7):
    rnd = random.Random(seed)
    return [(rnd.uniform(0, BOX_W), rnd.uniform(0, BOX_H)) for _ in range(n)]


def shield_dots(w, h, step=3.4):
    """Dithered shield with a keyhole cut-out. Returns [(x, y)] in 0..w, 0..h."""
    pts = []
    cols, rows = int(w / step), int(h / step)
    for j in range(rows):
        for i in range(cols):
            u = (i / (cols - 1)) * 2 - 1          # -1..1
            v = j / (rows - 1)                     # 0..1
            half = 1.0 if v < 0.5 else max(0.0, 1 - ((v - 0.5) / 0.5) ** 1.7)
            if v < 0.04:                           # slight top notch
                half *= 0.9 + abs(u) * 0.0
            if abs(u) > half * 0.92:
                continue
            # keyhole
            if math.hypot(u, (v - 0.40) * 1.15) < 0.17:
                continue
            if abs(u) < 0.07 + (v - 0.45) * 0.12 and 0.45 <= v < 0.68:
                continue
            edge = 1 - abs(u) / (half * 0.92 + 1e-9)
            light = 0.35 + 0.45 * (1 - (u + 1) / 2) * (1 - v * 0.6) + 0.3 * (edge < 0.08)
            if light * 64 > BAYER[j % 8][i % 8]:
                pts.append((i * step, j * step))
    return pts


def build(name, t):
    left_x, left_y, left_w, left_h = 24, 60, 300, 336
    right_x, right_w = 338, 486
    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,\'DejaVu Sans Mono\',monospace">')
    a('<style>@keyframes b{0%,60%{opacity:1}61%,100%{opacity:.15}}.live{animation:b 1.4s infinite}</style>')
    a(f'<rect width="{W}" height="{H}" rx="14" fill="{t["bg"]}"/>')
    a(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{t["stroke"]}"/>')
    # title bar
    for cx, c in ((22, "#ff5f57"), (42, "#febc2e"), (62, "#28c840")):
        a(f'<circle cx="{cx}" cy="22" r="6" fill="{c}"/>')
    a(f'<text x="{W/2}" y="26" text-anchor="middle" font-size="11" fill="{t["title"]}">profile.sh --live</text>')
    a(f'<line x1="0" y1="42" x2="{W}" y2="42" stroke="{t["stroke"]}"/>')
    # panels
    for x, w in ((left_x - 4, left_w + 8), (right_x - 4, right_w + 8)):
        a(f'<rect x="{x}" y="58" width="{w}" height="340" rx="6" fill="{t["panel"]}" stroke="{t["stroke"]}"/>')
    a(f'<text x="{left_x+6}" y="80" font-size="11" font-weight="700" fill="{t["accent"]}">VISUAL.MAP</text>')
    a(f'<text x="{left_x+left_w-2}" y="80" text-anchor="end" font-size="9" fill="{t["dim"]}">250×254 / 1-BIT</text>')
    # morphing dots: static fallback is the portrait; transforms carry the other stages
    ox, oy = left_x + (left_w - BOX_W) / 2, left_y + 36
    portrait = ordered([tuple(p) for p in json.load(open("assets/portrait-points.json"))[name]])
    n = len(portrait)
    sw, sh = 190, 215
    shield = resample([(x + (BOX_W - sw) / 2, y + (BOX_H - sh) / 2) for x, y in shield_dots(sw, sh)], n)
    stages = [resample(noise_dots(n), n), shield, resample(mesh_dots(), n)]
    a(f'<g fill="{t["dots"]}" fill-opacity="{t["dot_op"]}">')
    for i, (px, py) in enumerate(portrait):
        nz, sd, ms = (st[i] for st in stages)
        d = lambda q: f"{q[0]-px:.0f} {q[1]-py:.0f}"
        vals = f"{d(nz)};{d(sd)};{d(sd)};{d(ms)};{d(ms)};0 0;0 0;{d(nz)}"
        a(f'<circle cx="{ox+px:.1f}" cy="{oy+py:.1f}" r="1.05"><animateTransform attributeName="transform" '
          f'type="translate" dur="{LOOP}s" repeatCount="indefinite" keyTimes="{KEYTIMES}" values="{vals}"/></circle>')
    a('</g>')
    pts = portrait
    # corner brackets
    bx0, by0, bx1, by1, L = left_x + 8, left_y + 36, left_x + left_w - 8, left_y + left_h - 38, 14
    a(f'<g stroke="{t["accent"]}" stroke-width="1.5" fill="none">'
      f'<path d="M{bx0} {by0+L}V{by0}H{bx0+L}"/><path d="M{bx1-L} {by0}H{bx1}V{by0+L}"/>'
      f'<path d="M{bx0} {by1-L}V{by1}H{bx0+L}"/><path d="M{bx1-L} {by1}H{bx1}V{by1-L}"/></g>')
    a(f'<text x="{left_x+6}" y="{left_y+left_h-8}" font-size="9" fill="{t["dim"]}">PTS {len(pts)} · FS/HILBERT</text>')
    # right header
    a(f'<text x="{right_x+6}" y="80" font-size="11" font-weight="700" fill="{t["accent"]}">SYSTEM.INFO</text>')
    a(f'<circle class="live" cx="{right_x+300}" cy="76" r="3" fill="{t["live"]}"/>')
    a(f'<text x="{right_x+310}" y="80" font-size="10" font-weight="700" fill="{t["live"]}">LIVE</text>')
    a(f'<rect x="{right_x+366}" y="64" width="116" height="22" rx="11" fill="{t["bg"]}" stroke="{t["stroke"]}"/>')
    a(f'<text x="{right_x+424}" y="79" text-anchor="middle" font-size="11" font-weight="700" fill="{t["accent"]}">@sneakywarwolf</text>')
    # rows
    y = 106
    for k, v in INFO:
        a(f'<text x="{right_x+6}" y="{y}" font-size="11" fill="{t["key"]}">{escape(k)}</text>')
        a(f'<text x="{right_x+right_w-6}" y="{y}" text-anchor="end" font-size="11.5" font-weight="700" fill="{t["val"]}">{escape(v)}</text>')
        kx = right_x + 6 + len(k) * 6.9 + 10
        vx = right_x + right_w - 6 - len(v) * 7.1 - 10
        if vx > kx:
            a(f'<line x1="{kx:.0f}" y1="{y-3}" x2="{vx:.0f}" y2="{y-3}" stroke="{t["dim"]}" stroke-opacity=".5" stroke-dasharray="1 4"/>')
        y += 17.5
    # footer
    a(f'<line x1="{right_x+4}" y1="368" x2="{right_x+right_w-4}" y2="368" stroke="{t["stroke"]}"/>')
    a(f'<circle cx="{right_x+8}" cy="383" r="2.5" fill="{t["ok"]}"/>')
    a(f'<text x="{right_x+16}" y="386" font-size="9" font-weight="700" fill="{t["ok"]}">EVERY EXPERT WAS ONCE A BEGINNER</text>')
    a(f'<text x="{right_x+right_w-6}" y="386" text-anchor="end" font-size="9" fill="{t["dim"]}">UTC+5:30 · IST</text>')
    a('</svg>')
    open(f"assets/banner-{name}.svg", "w").write("".join(o))


for n, t in THEMES.items():
    build(n, t)
