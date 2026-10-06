#!/usr/bin/env python3
"""Turn a photo into 1-bit dither points for the banner's VISUAL.MAP panel.

    pip install opencv-python-headless numpy
    python3 scripts/portrait.py path/to/photo.jpg

Writes assets/portrait-points.json ({"dark": [[x, y], ...], "light": [...]}).
The crop box and segmentation hints below are tuned for the current photo
(1086x1448); adjust them for a different picture.
"""
import json
import sys

import cv2
import numpy as np

CROP = (290, 200, 1086, 1010)      # x0, y0, x1, y1 in the source photo: face + upper chest
BOX_W, BOX_H = 250, 254            # output size in banner pixels
STEP = 1.9                         # dot grid pitch


def segment(c, x0, y0):
    """GrabCut seeded with rough head/torso shapes; returns a 0/255 mask."""
    h, w = c.shape[:2]
    m = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    cv2.ellipse(m, (640 - x0, 450 - y0), (150, 210), 0, 0, 360, cv2.GC_PR_FGD, -1)
    torso = np.array([[560 - x0, 600 - y0], [800 - x0, 600 - y0], [w - 1, 700 - y0],
                      [w - 1, h - 1], [340 - x0, h - 1], [330 - x0, 780 - y0]])
    cv2.fillPoly(m, [torso], cv2.GC_PR_FGD)
    cv2.ellipse(m, (635 - x0, 470 - y0), (90, 130), 0, 0, 360, cv2.GC_FGD, -1)
    cv2.rectangle(m, (450 - x0, 760 - y0), (950 - x0, h - 1), cv2.GC_FGD, -1)
    cv2.rectangle(m, (0, 0), (w - 1, 30), cv2.GC_BGD, -1)
    cv2.rectangle(m, (0, 0), (150, 560 - y0), cv2.GC_BGD, -1)
    cv2.rectangle(m, (0, 0), (40, h - 1), cv2.GC_BGD, -1)
    cv2.rectangle(m, (870 - x0, 0), (w - 1, 560 - y0), cv2.GC_BGD, -1)
    bgm, fgm = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(c, m, None, bgm, fgm, 8, cv2.GC_INIT_WITH_MASK)
    mask = np.where((m == 1) | (m == 3), 255, 0).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask)
    mask = np.where(lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]), 255, 0).astype(np.uint8)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))


def dither(lum, mask):
    """Floyd-Steinberg over the masked region; returns [(x, y)] for 'on' cells."""
    a = lum.astype(np.float32).copy()
    h, w = a.shape
    on = []
    for y in range(h):
        for x in range(w):
            if not mask[y, x]:
                continue
            old = a[y, x]
            new = 1.0 if old > 0.5 else 0.0
            err = old - new
            if new:
                on.append((x, y))
            if x + 1 < w: a[y, x + 1] += err * 7 / 16
            if y + 1 < h:
                if x > 0: a[y + 1, x - 1] += err * 3 / 16
                a[y + 1, x] += err * 5 / 16
                if x + 1 < w: a[y + 1, x + 1] += err * 1 / 16
    return on


def main(path):
    img = cv2.imread(path)
    x0, y0, x1, y1 = CROP
    c = img[y0:y1, x0:x1].copy()
    mask = segment(c, x0, y0)
    gw, gh = int(BOX_W / STEP), int(BOX_H / STEP)
    gray = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)
    gray = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(6, 6)).apply(gray)
    blur = cv2.GaussianBlur(gray, (0, 0), 6)
    gray = cv2.addWeighted(gray, 1.6, blur, -0.6, 0)        # unsharp: crisper eyes/glasses/beard
    small = cv2.resize(gray, (gw, gh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    msk = cv2.resize(mask, (gw, gh), interpolation=cv2.INTER_AREA) > 127
    edge = cv2.morphologyEx(msk.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((2, 2), np.uint8)) > 0
    out = {}
    # dark theme: dots = light areas; light theme: dots = dark areas, capped so the sweater isn't solid
    for theme, lum in (("dark", np.clip(small, 0, 1) ** 1.25 * 0.95),
                       ("light", np.clip(1 - small, 0, 1) ** 1.6 * 0.4)):
        lum[edge] = np.maximum(lum[edge], 0.75)          # keep the silhouette readable
        pts = dither(lum, msk)
        out[theme] = [[round(x * STEP, 1), round(y * STEP, 1)] for x, y in pts]
    json.dump(out, open("assets/portrait-points.json", "w"), separators=(",", ":"))
    print({k: len(v) for k, v in out.items()})


if __name__ == "__main__":
    main(sys.argv[1])
