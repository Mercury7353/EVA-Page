"""
EVA Demo Video Generator v3
1920x1080, real video frames, black background, tech aesthetic.
"""

import os, sys, glob, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUTPUT = "static/media/demo.mp4"
W, H = 1920, 1080
FPS = 24

# Paths to real video frames (extracted from source_video.mp4)
FRAME_DIR_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")

# ─── Colors ───────────────────────────────────────────────────────────────────
BG        = (6, 6, 10)
ACCENT    = (0, 200, 255)
ACCENT2   = (0, 140, 220)
GOOD      = (0, 230, 170)
BAD       = (255, 60, 80)
MID       = (255, 200, 60)
WHITE     = (240, 242, 248)
MUTED     = (100, 110, 128)
DIM       = (50, 55, 68)
PANEL     = (14, 16, 22)
BORDER    = (40, 46, 58)

# ─── Font cache ───────────────────────────────────────────────────────────────
_fc = {}
def F(size, bold=False):
    k = (size, bold)
    if k in _fc: return _fc[k]
    paths = [
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size); _fc[k] = f; return f
            except: pass
    f = ImageFont.load_default(); _fc[k] = f; return f

def ts(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]

def tc(draw, y, text, font, color=WHITE):
    tw, th = ts(draw, text, font)
    draw.text(((W - tw) // 2, y), text, font=font, fill=color)
    return y + th + 4

def tb(draw, cx, y, text, font, color=WHITE):
    tw, _ = ts(draw, text, font)
    draw.text((cx - tw // 2, y), text, font=font, fill=color)

def rrect(d, x0, y0, x1, y1, r, fill=None, outline=None, w=1):
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill, outline=outline, width=w)

# ─── Real video frames ────────────────────────────────────────────────────────
_real_frames = None
def load_real_frames():
    global _real_frames
    if _real_frames is not None: return _real_frames
    files = sorted(glob.glob(os.path.join(FRAME_DIR_SRC, "f_*.jpg")))
    _real_frames = []
    for f in files:
        img = Image.open(f).convert("RGB")
        _real_frames.append(img)
    print(f"  Loaded {len(_real_frames)} real video frames")
    return _real_frames

def get_frame_thumb(idx, w, h, low_res=False, darken=0):
    frames = load_real_frames()
    if not frames:
        return Image.new("RGB", (w, h), (40, 60, 80))
    img = frames[idx % len(frames)].copy()
    if low_res:
        img = img.resize((img.width // 8, img.height // 8), Image.BILINEAR)
        img = img.resize((w, h), Image.NEAREST)
    else:
        img = img.resize((w, h), Image.LANCZOS)
    if darken > 0:
        arr = np.array(img, dtype=np.float32)
        arr = arr * (1.0 - darken / 255.0)
        img = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    return img

def paste_frame_grid(canvas, x0, y0, cols, rows, fw, fh, gap,
                     start_idx=0, n_show=None, low_res=False,
                     highlight=None, hl_color=BAD, darken=0, border_col=None):
    if n_show is None: n_show = cols * rows
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            if idx >= n_show: return
            x = x0 + c * (fw + gap)
            y = y0 + r * (fh + gap)
            thumb = get_frame_thumb(start_idx + idx, fw, fh, low_res=low_res, darken=darken)
            canvas.paste(thumb, (x, y))
            if border_col:
                d = ImageDraw.Draw(canvas)
                d.rectangle([x, y, x + fw - 1, y + fh - 1], outline=border_col, width=1)
            if highlight is not None and idx == highlight:
                d = ImageDraw.Draw(canvas)
                d.rectangle([x - 3, y - 3, x + fw + 2, y + fh + 2], outline=hl_color, width=3)

# ─── Background ───────────────────────────────────────────────────────────────
def tech_bg():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    c = (12, 12, 16)
    for x in range(0, W, 120):
        draw.line([(x, 0), (x, H)], fill=c, width=1)
    for y in range(0, H, 120):
        draw.line([(0, y), (W, y)], fill=c, width=1)
    return img

# ─── Title card ───────────────────────────────────────────────────────────────
def title_card(title, subtitle="", dur=3.5, fi=0.5, fo=0.5):
    n = int(dur * FPS)
    nfi, nfo = int(fi * FPS), int(fo * FPS)
    ft = F(78, True); fs = F(32)
    for i in range(n):
        a = 1.0
        if i < nfi: a = i / nfi
        elif i > n - nfo: a = (n - i) / nfo
        img = tech_bg()
        if a < 1.0:
            ov = Image.new("RGBA", (W, H), (0, 0, 0, int((1 - a) * 240)))
            img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        draw = ImageDraw.Draw(img)
        rrect(draw, W // 2 - 80, H // 2 - 85, W // 2 + 80, H // 2 - 79, 2, fill=ACCENT)
        tc(draw, H // 2 - 60, title, ft, WHITE)
        if subtitle:
            tc(draw, H // 2 + 38, subtitle, fs, MUTED)
        yield img

def fade_wrap(scene_fn, dur, fi=0.3, fo=0.3):
    n = int(dur * FPS)
    nfi, nfo = int(fi * FPS), int(fo * FPS)
    for i in range(n):
        a = 1.0
        if i < nfi: a = i / nfi
        elif i > n - nfo: a = (n - i) / nfo
        base = scene_fn(i, n)
        if a < 1.0:
            ov = Image.new("RGBA", (W, H), (0, 0, 0, int((1 - a) * 220)))
            base = Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")
        yield base

# ═══════════════════════════════════════════════════════════════════════════════
#   SCENE 1: The Challenge
# ═══════════════════════════════════════════════════════════════════════════════

def scene_challenge(i, n):
    img = tech_bg()
    draw = ImageDraw.Draw(img)
    t = min(1.0, i / (n * 0.6))

    tc(draw, 30, "The Challenge: Long Video Understanding", F(46, True), ACCENT)

    # Question bar
    rrect(draw, 80, 95, W - 80, 160, 10, fill=PANEL, outline=BORDER)
    draw.text((100, 105), 'Q: "What sequence of actions did the camera wearer perform',
              font=F(22), fill=WHITE)
    draw.text((120, 133), 'while adjusting and using a microscope for sample analysis?"',
              font=F(22), fill=WHITE)

    # Real video frame grid
    cols, rows = 24, 5
    fw, fh = 64, 40
    gap = 4
    gw = cols * (fw + gap) - gap
    gx = (W - gw) // 2
    gy = 185
    n_show = max(4, int(cols * rows * t))
    paste_frame_grid(img, gx, gy, cols, rows, fw, fh, gap,
                     start_idx=0, n_show=n_show,
                     highlight=47, hl_color=BAD, border_col=(25, 28, 35))

    draw = ImageDraw.Draw(img)
    grid_b = gy + rows * (fh + gap) + 15
    tokens = int(10000 + 489000 * t)
    tc(draw, grid_b, f"~{tokens:,} visual tokens", F(30, True), BAD)

    # Footnote
    draw.text((80, H - 45), "256 uniformly sampled frames -- only 1 relevant to the question (highlighted in red)",
              font=F(17), fill=DIM)
    return img

# ═══════════════════════════════════════════════════════════════════════════════
#   SCENE 2: Passive MLLM
# ═══════════════════════════════════════════════════════════════════════════════

def scene_passive(i, n):
    img = tech_bg()
    draw = ImageDraw.Draw(img)
    t = min(1.0, i / (n * 0.5))

    tc(draw, 25, "Passive Recognition Method", F(46, True), BAD)

    # Frame strip
    cols = 16
    fw, fh = 90, 56
    gap = 5
    gw = cols * (fw + gap) - gap
    gx = (W - gw) // 2
    gy = 110
    paste_frame_grid(img, gx, gy, cols, 1, fw, fh, gap,
                     start_idx=0, highlight=11, hl_color=BAD, border_col=(25, 28, 35))

    draw = ImageDraw.Draw(img)
    cx = W // 2

    # Arrow down
    draw.line([(cx, gy + fh + 8), (cx, gy + fh + 50)], fill=MUTED, width=2)
    draw.text((cx + 10, gy + fh + 18), "all frames fed in", font=F(16), fill=DIM)

    # MLLM box
    my = gy + fh + 55
    rrect(draw, cx - 100, my, cx + 100, my + 60, 10, fill=PANEL, outline=BORDER, w=2)
    tb(draw, cx, my + 14, "MLLM", F(28, True), WHITE)

    # Arrow down + Wrong answer
    if t > 0.5:
        draw.line([(cx, my + 62), (cx, my + 100)], fill=BAD, width=2)
        wy = my + 105
        rrect(draw, cx - 160, wy, cx + 160, wy + 60, 10, fill=(30, 6, 10), outline=BAD, w=2)
        tb(draw, cx, wy + 12, "WRONG ANSWER", F(28, True), BAD)

    # Problems (right)
    if t > 0.7:
        px = W // 2 + 300
        py = 300
        draw.text((px, py), "Problems:", font=F(22, True), fill=BAD)
        draw.text((px, py + 36), "- Only 1 relevant frame among 256", font=F(20), fill=MUTED)
        draw.text((px, py + 68), "- No way to select or zoom in", font=F(20), fill=MUTED)
        draw.text((px, py + 100), "- 499K tokens wasted on noise", font=F(20), fill=MUTED)

    draw.text((80, H - 45),
              "Passive approach processes all uniformly sampled frames at once -- misled by irrelevant content",
              font=F(17), fill=DIM)
    return img

# ═══════════════════════════════════════════════════════════════════════════════
#   SCENE 3: Traditional Agent — uniform sample + zoom in emphasized
# ═══════════════════════════════════════════════════════════════════════════════

def scene_trad_agent(i, n):
    img = tech_bg()
    draw = ImageDraw.Draw(img)
    t = min(1.0, i / (n * 0.5))

    tc(draw, 20, "Traditional Agentic Method", F(46, True), MID)

    lx = 80

    # ── Phase 1: Uniform Sample ──
    p1y = 100
    draw.text((lx, p1y), "Phase 1: Uniform Sample", font=F(24, True), fill=MID)
    fr_y = p1y + 38
    cols1 = 8
    fw1, fh1 = 90, 56
    gap1 = 5
    paste_frame_grid(img, lx, fr_y, cols1, 1, fw1, fh1, gap1,
                     start_idx=0, border_col=(30, 33, 40))
    draw = ImageDraw.Draw(img)

    # Arrow + MLLM
    ax = lx + cols1 * (fw1 + gap1) + 15
    draw.text((ax, fr_y + 14), "-->", font=F(24, True), fill=MUTED)
    mx = ax + 65
    rrect(draw, mx, fr_y - 2, mx + 130, fr_y + fh1 + 2, 8, fill=PANEL, outline=BORDER)
    tb(draw, mx + 65, fr_y + 14, "MLLM", F(24, True), WHITE)

    # ── Phase 2: Zoom In ──
    if t > 0.25:
        p2y = fr_y + fh1 + 35
        draw.text((lx, p2y), "Phase 2: Zoom In (Tool Call)", font=F(24, True), fill=MID)

        tc_y = p2y + 38
        rrect(draw, lx, tc_y, lx + 400, tc_y + 80, 10, fill=PANEL, outline=ACCENT2)
        draw.text((lx + 16, tc_y + 8), "Tool Call:", font=F(20, True), fill=ACCENT)
        draw.text((lx + 16, tc_y + 36), "start: 3500  end: 4000  nframes: 50", font=F(18), fill=WHITE)
        draw.text((lx + 16, tc_y + 58), "resize: 1.0", font=F(18), fill=WHITE)

        draw.text((lx + 420, tc_y + 24), "-->", font=F(24, True), fill=MUTED)

        # Zoomed frames
        zx = lx + 490
        paste_frame_grid(img, zx, tc_y + 8, 8, 1, 90, 56, 5,
                         start_idx=30, border_col=(30, 33, 40))

    # Wrong Answer
    if t > 0.6:
        draw = ImageDraw.Draw(img)
        wy = tc_y + 110
        cx = W // 2 - 100
        rrect(draw, cx - 180, wy, cx + 180, wy + 60, 10, fill=(30, 20, 5), outline=MID, w=2)
        tb(draw, cx, wy + 10, "STILL WRONG", F(28, True), MID)

    # Problems (right side)
    if t > 0.65:
        draw = ImageDraw.Draw(img)
        px = W - 500
        py = 140
        draw.text((px, py), "Why it fails:", font=F(22, True), fill=MID)
        draw.text((px, py + 40), "- Perception-first: sees frames", font=F(20), fill=MUTED)
        draw.text((px, py + 68), "  BEFORE forming a strategy", font=F(20), fill=MUTED)
        draw.text((px, py + 108), "- Fixed nframes & resolution", font=F(20), fill=MUTED)
        draw.text((px, py + 148), "- Zoom in on wrong segment:", font=F(20), fill=MUTED)
        draw.text((px, py + 176), "  misses the action sequence", font=F(20), fill=MUTED)

    draw = ImageDraw.Draw(img)
    draw.text((80, H - 45),
              "Traditional agent: uniform sample then zoom in -- perception-first leads to wrong time range",
              font=F(17), fill=DIM)
    return img

# ═══════════════════════════════════════════════════════════════════════════════
#   SCENE 4: EVA — clean vertical flow, shows subsumption
# ═══════════════════════════════════════════════════════════════════════════════

def scene_eva(i, n):
    img = tech_bg()
    draw = ImageDraw.Draw(img)
    t = min(1.0, i / n)

    tc(draw, 15, "EVA: Planning Before Perception", F(48, True), GOOD)

    lx = 80
    rx = W - 80
    mid = W // 2

    # ── Row 1: Question + Plan ──
    r1y = 85
    if t >= 0.0:
        rrect(draw, lx, r1y, lx + 440, r1y + 80, 10, fill=PANEL, outline=GOOD, w=2)
        draw.text((lx + 16, r1y + 6), "Step 1: Read Question", font=F(22, True), fill=GOOD)
        draw.text((lx + 16, r1y + 36), "No frames loaded -- 0 visual tokens", font=F(17), fill=MUTED)
        draw.text((lx + 16, r1y + 58), "Agent reasons from text alone", font=F(17), fill=MUTED)

    if t >= 0.1:
        draw.text((lx + 460, r1y + 24), "-->", font=F(26, True), fill=ACCENT)
        sx = lx + 540
        rrect(draw, sx, r1y, sx + 520, r1y + 80, 10, fill=PANEL, outline=GOOD, w=2)
        draw.text((sx + 16, r1y + 6), "Step 2: Plan Strategy", font=F(22, True), fill=GOOD)
        draw.text((sx + 16, r1y + 36), '"Survey the video at low-res first..."', font=F(17), fill=WHITE)
        draw.text((sx + 16, r1y + 58), "Reasoning BEFORE any perception", font=F(17), fill=MUTED)

    if t >= 0.1:
        tag_x = rx - 330
        rrect(draw, tag_x, r1y + 15, rx, r1y + 55, 8, fill=(8, 30, 22), outline=GOOD)
        tb(draw, (tag_x + rx) // 2, r1y + 21, "Plans without seeing frames", F(18, True), GOOD)

    # ── Row 2: Low-res scan ──
    r2y = 200
    if t >= 0.25:
        draw.line([(mid, r1y + 84), (mid, r2y - 4)], fill=ACCENT, width=2)

        rrect(draw, lx, r2y, lx + 440, r2y + 90, 10, fill=PANEL, outline=ACCENT, w=2)
        draw.text((lx + 16, r2y + 4), "Step 3: Low-Res Scan", font=F(22, True), fill=ACCENT)
        draw.text((lx + 16, r2y + 32), "start: 0  end: 6630", font=F(18), fill=WHITE)
        draw.text((lx + 16, r2y + 56), "nframes: 256  resize: 0.1", font=F(18), fill=WHITE)

        draw.text((lx + 460, r2y + 30), "-->", font=F(26, True), fill=ACCENT)

    if t >= 0.35:
        fx = lx + 540
        paste_frame_grid(img, fx, r2y + 5, 10, 2, 68, 38, 4,
                         start_idx=0, low_res=True,
                         highlight=13, hl_color=MID, border_col=(20, 25, 35))
        draw = ImageDraw.Draw(img)

    if t >= 0.35:
        tag_x = rx - 330
        rrect(draw, tag_x, r2y + 20, rx, r2y + 60, 8, fill=(12, 12, 28), outline=ACCENT2)
        tb(draw, (tag_x + rx) // 2, r2y + 27, "Subsumes passive approach", F(17, True), ACCENT)

    # ── Row 3: High-res zoom ──
    r3y = 330
    if t >= 0.5:
        draw.line([(mid, r2y + 94), (mid, r3y - 4)], fill=ACCENT, width=2)

        rrect(draw, lx, r3y, lx + 440, r3y + 90, 10, fill=PANEL, outline=ACCENT, w=2)
        draw.text((lx + 16, r3y + 4), "Step 4: High-Res Zoom", font=F(22, True), fill=ACCENT)
        draw.text((lx + 16, r3y + 32), "start: 3500  end: 4000", font=F(18), fill=WHITE)
        draw.text((lx + 16, r3y + 56), "nframes: 50  resize: 1.0", font=F(18), fill=WHITE)

        draw.text((lx + 460, r3y + 30), "-->", font=F(26, True), fill=ACCENT)

    if t >= 0.6:
        fx2 = lx + 540
        paste_frame_grid(img, fx2, r3y + 5, 10, 2, 68, 38, 4,
                         start_idx=30, border_col=(20, 25, 35))
        draw = ImageDraw.Draw(img)

    if t >= 0.6:
        tag_x = rx - 330
        rrect(draw, tag_x, r3y + 20, rx, r3y + 60, 8, fill=(12, 12, 28), outline=ACCENT2)
        tb(draw, (tag_x + rx) // 2, r3y + 27, "Subsumes agent zoom-in", F(17, True), ACCENT)

    # ── Result row ──
    if t >= 0.75:
        ry = 460
        draw.line([(mid, r3y + 94), (mid, ry - 4)], fill=GOOD, width=2)

        rrect(draw, lx, ry, mid - 30, ry + 70, 12, fill=(6, 28, 20), outline=GOOD, w=3)
        draw.text((lx + 20, ry + 8), "CORRECT ANSWER", font=F(28, True), fill=GOOD)
        draw.text((lx + 20, ry + 44), "Option B identified correctly", font=F(17), fill=MUTED)

        rrect(draw, mid + 30, ry, rx, ry + 70, 12, fill=PANEL, outline=ACCENT, w=2)
        draw.text((mid + 50, ry + 8), "~10K tokens", font=F(28, True), fill=ACCENT)
        draw.text((mid + 50, ry + 44), "vs 499K for Qwen2.5-VL  (98% fewer)", font=F(17), fill=MUTED)

    # ── Bottom comparison ──
    if t >= 0.85:
        sy = 575
        cw = (W - 240) // 3
        cg = 30

        cx0 = 100
        rrect(draw, cx0, sy, cx0 + cw, sy + 80, 10, fill=PANEL, outline=BAD)
        draw.text((cx0 + 14, sy + 8), "Passive MLLM", font=F(20, True), fill=BAD)
        draw.text((cx0 + 14, sy + 36), "All frames / 499K tokens / Wrong", font=F(16), fill=MUTED)

        cx1 = cx0 + cw + cg
        rrect(draw, cx1, sy, cx1 + cw, sy + 80, 10, fill=PANEL, outline=MID)
        draw.text((cx1 + 14, sy + 8), "Traditional Agent", font=F(20, True), fill=MID)
        draw.text((cx1 + 14, sy + 36), "Sample + Zoom (fixed) / Wrong", font=F(16), fill=MUTED)

        cx2 = cx1 + cw + cg
        rrect(draw, cx2, sy, cx2 + cw, sy + 80, 10, fill=(6, 28, 20), outline=GOOD, w=2)
        draw.text((cx2 + 14, sy + 8), "EVA (Ours)", font=F(20, True), fill=GOOD)
        draw.text((cx2 + 14, sy + 36), "Plan -> Scan -> Zoom / 10K tokens / Correct", font=F(16, True), fill=GOOD)

    draw = ImageDraw.Draw(img)
    draw.text((80, H - 42),
              "EVA plans from the question, then adaptively scans and zooms -- encompassing both passive and agent strategies",
              font=F(17), fill=DIM)
    return img

# ═══════════════════════════════════════════════════════════════════════════════
#   SCENE 5: Results — VideoMME
# ═══════════════════════════════════════════════════════════════════════════════

def scene_results(i, n):
    img = tech_bg()
    draw = ImageDraw.Draw(img)
    t = min(1.0, i / (n * 0.6))

    tc(draw, 30, "Benchmark: VideoMME", F(48, True), ACCENT)
    tc(draw, 90, "Video Understanding Performance", F(26), MUTED)

    bars = [
        ("EVA-GRPO (Ours)", 60.2, GOOD, "22.8 frames"),
        ("Qwen2.5-VL-7B",  63.3, (70, 100, 150), "768 frames"),
        ("VideoChat-R1",    56.5, (55, 80, 120), ""),
        ("Video-R1",        56.3, (50, 75, 110), ""),
        ("InternVL2.5-8B",  53.4, (45, 65, 95), ""),
    ]

    max_v = 70
    bar_h = 50
    bar_gap = 16
    name_w = 350
    bar_w = W - name_w - 350
    y0 = 160

    for bi, (name, val, color, note) in enumerate(bars):
        y = y0 + bi * (bar_h + bar_gap)
        bw = int(bar_w * (val / max_v) * min(1.0, t * 2.0))
        draw.text((80, y + 10), name, font=F(22, bi == 0), fill=WHITE if bi > 0 else GOOD)
        rrect(draw, name_w, y + 4, name_w + max(bw, 4), y + bar_h - 4, 6, fill=color)
        if bw > 40:
            draw.text((name_w + bw + 12, y + 10), f"{val}%", font=F(24, True), fill=WHITE)
        if note and bw > 40:
            draw.text((name_w + bw + 80, y + 14), note, font=F(18),
                      fill=GOOD if bi == 0 else MUTED)

    chart_b = y0 + len(bars) * (bar_h + bar_gap)
    draw.text((name_w, chart_b + 5), "VideoMME Overall Accuracy (%)", font=F(20), fill=DIM)

    # Stat cards
    if t > 0.6:
        stats = [
            ("6-12%", "accuracy gain", "over MLLM baselines"),
            ("98%", "fewer visual", "tokens vs Qwen"),
            ("68.3%", "MLVU score", "vs 59.1% FrameThinker"),
            ("43.3%", "LVBench score", "vs 36.6% FrameThinker"),
        ]
        n_s = len(stats)
        cw = (W - 200 - (n_s - 1) * 20) // n_s
        ch = 140
        cy = H - ch - 60

        for si, (num, l1, l2) in enumerate(stats):
            cx = 100 + si * (cw + 20)
            rrect(draw, cx, cy, cx + cw, cy + ch, 12, fill=PANEL, outline=BORDER)
            ccx = cx + cw // 2
            tb(draw, ccx, cy + 16, num, F(38, True), ACCENT)
            tb(draw, ccx, cy + 72, l1, F(18), MUTED)
            tb(draw, ccx, cy + 96, l2, F(18), MUTED)

    draw.text((80, H - 40),
              "EVA achieves competitive accuracy with 98% fewer visual tokens across 6 benchmarks",
              font=F(17), fill=DIM)
    return img

# ═══════════════════════════════════════════════════════════════════════════════
#   Assembly
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    tmpdir = tempfile.mkdtemp(prefix="eva_v3_")
    print(f"Rendering 1920x1080 frames to {tmpdir}")

    idx = [0]
    def collect(gen):
        for frame in gen:
            path = os.path.join(tmpdir, f"f_{idx[0]:06d}.png")
            frame.save(path, optimize=False)
            idx[0] += 1
            if idx[0] % 100 == 0:
                print(f"  {idx[0]} frames")

    load_real_frames()

    collect(title_card("Long Video Understanding", "A Hard Problem", 3.0))
    collect(fade_wrap(scene_challenge, 9))
    collect(title_card("Passive Recognition", "", 2.0))
    collect(fade_wrap(scene_passive, 9))
    collect(title_card("Traditional Agentic Method", "", 2.0))
    collect(fade_wrap(scene_trad_agent, 10))
    collect(title_card("EVA", "Planning Before Perception", 2.5))
    collect(fade_wrap(scene_eva, 20))
    collect(title_card("Results", "", 1.5))
    collect(fade_wrap(scene_results, 11))
    collect(title_card("EVA", "CVPR 2026", 3.5))

    total = idx[0]
    print(f"Total: {total} frames ({total / FPS:.1f}s)")

    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    pattern = os.path.join(tmpdir, "f_%06d.png")
    cmd = (f"ffmpeg -y -framerate {FPS} -i {pattern} "
           f"-c:v libx264 -crf 20 -preset medium -pix_fmt yuv420p "
           f"-an {OUTPUT}")
    print("Encoding...")
    ret = os.system(cmd)
    if ret != 0:
        print("ffmpeg failed!")
        sys.exit(1)

    shutil.rmtree(tmpdir, ignore_errors=True)
    sz = os.path.getsize(OUTPUT) / 1024
    print(f"Done: {OUTPUT} ({sz:.0f} KB)")

if __name__ == "__main__":
    main()
