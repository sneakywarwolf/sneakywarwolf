#!/usr/bin/env python3
"""Generate assets/banner-{dark,light}.svg (terminal-style profile card).

Edit INFO below and re-run:  python3 scripts/banner.py
The VISUAL.MAP portrait comes from assets/portrait-points.json (scripts/portrait.py).
Its dots follow a finding through vulnerability management, then settle on the portrait:
noise -> crosshair (discover) -> bug (find) -> severity bars (assess)
      -> shield with keyhole -> shield with checkmark (fix) -> portrait.
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
    ("Role", "Technical Team Lead"),
    ("Domain", "Security Testing · Risk Advisory · Vuln Mgmt"),
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
LOOP = 26                   # seconds per animation cycle
# (arrive, leave) for each shape, as fractions of LOOP; the portrait holds ~36% of the loop
TIMELINE = [("crosshair", .045, .12), ("bug", .165, .24), ("bars", .285, .36),
            ("shield", .405, .46), ("check", .49, .55), ("portrait", .60, .96)]
KEYTIMES = ";".join(["0"] + [f"{k:g}" for _, a, b in TIMELINE for k in (a, b)] + ["1"])


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


def fill(inside, step=3.4, density=lambda x, y: 1.0):
    """Grid points inside a region, thinned by an ordered dither of density(x, y)."""
    pts = []
    for j in range(int(BOX_H / step) + 1):
        for i in range(int(BOX_W / step) + 1):
            x, y = i * step, j * step
            if inside(x, y) and density(x, y) * 64 > BAYER[j % 8][i % 8]:
                pts.append((x, y))
    return pts


def line(x0, y0, x1, y1, gap=3.2):
    n = max(1, int(math.hypot(x1 - x0, y1 - y0) / gap))
    return [(x0 + (x1 - x0) * t / n, y0 + (y1 - y0) * t / n) for t in range(n + 1)]


def ring(cx, cy, r, gap=3.2):
    n = max(8, int(2 * math.pi * r / gap))
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def crosshair_dots():
    """Recon reticle: three rings, cross hairs with a centre gap, tick marks and a target blip."""
    cx, cy = BOX_W / 2, BOX_H / 2
    pts = ring(cx, cy, 112) + ring(cx, cy, 76, 4) + ring(cx, cy, 40, 4.5)
    for d in (1, -1):
        pts += line(cx + d * 18, cy, cx + d * 118, cy) + line(cx, cy + d * 18, cx, cy + d * 118)
    for k in range(24):
        a = 2 * math.pi * k / 24
        pts += line(cx + 104 * math.cos(a), cy + 104 * math.sin(a), cx + 112 * math.cos(a), cy + 112 * math.sin(a), 2.5)
    bx, by = cx + 48, cy - 34
    pts += fill(lambda x, y: math.hypot(x - bx, y - by) < 8, 2.2) + ring(bx, by, 14, 3.5)
    return pts


def bug_dots():
    """Beetle: dithered head and body, split wing line, six legs, two antennae."""
    cx, cy = BOX_W / 2, BOX_H / 2 + 14
    body = lambda x, y: ((x - cx) / 52) ** 2 + ((y - cy) / 70) ** 2 <= 1
    head = lambda x, y: math.hypot(x - cx, y - (cy - 88)) <= 24
    pts = fill(lambda x, y: (body(x, y) and abs(x - cx) > 2.5) or head(x, y),
               density=lambda x, y: 0.55 + 0.4 * (x < cx))
    for side in (1, -1):
        for k, (y0, dy) in enumerate(((cy - 38, -30), (cy, 0), (cy + 38, 30))):
            x0 = cx + side * 48
            kx, ky = x0 + side * 34, y0 + dy * 0.4 - 6
            pts += line(x0, y0, kx, ky) + line(kx, ky, kx + side * 22, ky + dy * 0.9 + 18)
        hx, hy = cx + side * 10, cy - 108
        pts += line(hx, hy, hx + side * 22, hy - 26) + line(hx + side * 22, hy - 26, hx + side * 40, hy - 30)
    return pts


def bars_dots():
    """Severity chart: Critical / High / Medium / Low bars, falling height and density, on an axis."""
    base, w, gap = BOX_H - 26, 40, 16
    x0 = (BOX_W - (4 * w + 3 * gap)) / 2
    heights, dens = (196, 146, 98, 56), (1.0, 0.78, 0.58, 0.42)
    bars = [(x0 + k * (w + gap), base - h, d) for k, (h, d) in enumerate(zip(heights, dens))]
    def which(x, y):
        for bx, top, d in bars:
            if bx <= x <= bx + w and top <= y <= base - 6:
                return d
        return 0
    pts = fill(lambda x, y: which(x, y) > 0, 3.0, which)
    pts += line(x0 - 14, base, x0 + 4 * w + 3 * gap + 14, base, 2.8)
    return pts


def noise_dots(n, seed=7):
    rnd = random.Random(seed)
    return [(rnd.uniform(0, BOX_W), rnd.uniform(0, BOX_H)) for _ in range(n)]


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def shield_dots(w, h, step=3.4, cut="keyhole"):
    """Dithered shield with a keyhole or checkmark cut-out. Returns [(x, y)] in 0..w, 0..h."""
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
            if cut == "keyhole":
                if math.hypot(u, (v - 0.40) * 1.15) < 0.17:
                    continue
                if abs(u) < 0.07 + (v - 0.45) * 0.12 and 0.45 <= v < 0.68:
                    continue
            else:                                  # checkmark, in shield units (v scaled to match u)
                p = (u, v * 2.2)
                if min(seg_dist(*p, -0.45, 0.95, -0.12, 1.32), seg_dist(*p, -0.12, 1.32, 0.48, 0.55)) < 0.11:
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
    centre = lambda pts: [(x + (BOX_W - sw) / 2, y + (BOX_H - sh) / 2) for x, y in pts]
    shapes = {"crosshair": crosshair_dots(), "bug": bug_dots(), "bars": bars_dots(),
              "shield": centre(shield_dots(sw, sh)), "check": centre(shield_dots(sw, sh, cut="check"))}
    noise = resample(noise_dots(n), n)
    stages = [resample(shapes[k], n) for k, _, _ in TIMELINE if k != "portrait"]
    a(f'<g fill="{t["dots"]}" fill-opacity="{t["dot_op"]}">')
    for i, (px, py) in enumerate(portrait):
        d = lambda q: f"{q[0]-px:.0f} {q[1]-py:.0f}"
        hold = [d(st[i]) for st in stages for _ in (0, 1)]
        vals = ";".join([d(noise[i])] + hold + ["0 0", "0 0", d(noise[i])])
        a(f'<circle cx="{ox+px:.1f}" cy="{oy+py:.1f}" r="1.05"><animateTransform attributeName="transform" '
          f'type="translate" dur="{LOOP}s" repeatCount="indefinite" keyTimes="{KEYTIMES}" values="{vals}"/></circle>')
    a('</g>')
    # scan line sweeping the drawing area
    sweep = f'dur="{LOOP / 8:g}s" repeatCount="indefinite"'
    a(f'<defs><linearGradient id="scan" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["accent"]}" '
      f'stop-opacity="0"/><stop offset="1" stop-color="{t["accent"]}" stop-opacity=".22"/></linearGradient></defs>')
    a(f'<g><animateTransform attributeName="transform" type="translate" values="0 {-24};0 {BOX_H}" {sweep}/>'
      f'<rect x="{ox-8}" y="{oy}" width="{BOX_W+16}" height="22" fill="url(#scan)"/>'
      f'<rect x="{ox-8}" y="{oy+22}" width="{BOX_W+16}" height="1.2" fill="{t["accent"]}" fill-opacity=".55"/></g>')
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
        y += 16.5
    # footer
    a(f'<line x1="{right_x+4}" y1="368" x2="{right_x+right_w-4}" y2="368" stroke="{t["stroke"]}"/>')
    a(f'<circle cx="{right_x+8}" cy="383" r="2.5" fill="{t["ok"]}"/>')
    a(f'<text x="{right_x+16}" y="386" font-size="9" font-weight="700" fill="{t["ok"]}">EVERY EXPERT WAS ONCE A BEGINNER</text>')
    a(f'<text x="{right_x+right_w-6}" y="386" text-anchor="end" font-size="9" fill="{t["dim"]}">UTC+5:30 · IST</text>')
    a('</svg>')
    open(f"assets/banner-{name}.svg", "w").write("".join(o))


for n, t in THEMES.items():
    build(n, t)
