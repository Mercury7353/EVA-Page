"""
EVA Demo Video Generator v2
Creates a ~70s explainer video showing EVA's planning-before-perception advantage.

Requirements:
  pip install moviepy==1.0.3 Pillow numpy

Usage:
  cd <project_dir> && python scripts/make_demo_video.py
"""

import os
import sys
import textwrap
import tempfile
import glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUTPUT = "static/media/demo.mp4"
W, H = 1920, 1080
FPS = 24
FRAME_DIR = None  # set at runtime

# ─── Color palette ────────────────────────────────────────────────────────────
BG        = (10, 12, 18)
BG2       = (16, 20, 28)
ACCENT    = (0, 180, 216)
ACCENT2   = (0, 119, 182)
GOOD      = (6, 214, 160)
BAD       = (239, 71, 111)
MID       = (255, 209, 102)
WHITE     = (235, 240, 248)
MUTED     = (120, 130, 145)
PANEL_BG  = (20, 25, 35)
BORDER    = (45, 52, 65)
DARK_RED  = (40, 8, 12)
DARK_GREEN = (8, 35, 25)
DARK_AMBER = (35, 30, 8)

# ─── Font helpers ────────────────────────────────────────────────────────────

_font_cache = {}

def get_font(size, bold=False):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    candidates = [
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                f = ImageFont.truetype(path, size)
                _font_cache[key] = f
                return f
            except Exception:
                pass
    f = ImageFont.load_default()
    _font_cache[key] = f
    return f


def tsize(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_text_c(draw, y, text, font, color=WHITE):
    """Draw text horizontally centered on the canvas."""
    tw, th = tsize(draw, text, font)
    draw.text(((W - tw) // 2, y), text, font=font, fill=color)
    return y + th + 8


def draw_text_in_box(draw, cx, y, text, font, color=WHITE):
    """Draw text centered at horizontal coordinate cx."""
    tw, th = tsize(draw, text, font)
    draw.text((cx - tw // 2, y), text, font=font, fill=color)
    return y + th + 4


def rrect(draw, x0, y0, x1, y1, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill, outline=outline, width=width)


def lerp(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))


# ─── Simulated "video frames" with varied colors ─────────────────────────────

def make_scene_color(rng, warm=False):
    """Generate a plausible video-frame color (not just grey)."""
    if warm:
        r = int(rng.integers(60, 140))
        g = int(rng.integers(40, 100))
        b = int(rng.integers(30, 70))
    else:
        base = int(rng.integers(30, 90))
        r = base + int(rng.integers(-10, 20))
        g = base + int(rng.integers(-5, 25))
        b = base + int(rng.integers(0, 35))
    return (min(255, r), min(255, g), min(255, b))


def draw_video_frames(draw, x0, y0, cols, rows, cell_w, cell_h, gap,
                      rng, highlight_idx=None, highlight_color=BAD,
                      n_shown=None, low_res=False):
    """Draw a grid of colored rectangles simulating video frames."""
    total = cols * rows
    if n_shown is None:
        n_shown = total
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            if idx >= n_shown:
                return
            x = x0 + c * (cell_w + gap)
            y = y0 + r * (cell_h + gap)
            fill = make_scene_color(rng, warm=(idx % 7 < 3))
            if low_res:
                # Wash out to simulate low resolution
                fill = (fill[0] // 2 + 20, fill[1] // 2 + 20, fill[2] // 2 + 25)
            if highlight_idx is not None and idx == highlight_idx:
                draw.rectangle([x - 2, y - 2, x + cell_w + 2, y + cell_h + 2],
                               outline=highlight_color, width=3)
            draw.rectangle([x, y, x + cell_w, y + cell_h], fill=fill)
            # Add a subtle "content" stripe inside each frame
            sy = y + cell_h // 3
            stripe_c = tuple(min(255, v + 15) for v in fill)
            draw.rectangle([x + 2, sy, x + cell_w - 2, sy + max(2, cell_h // 6)], fill=stripe_c)


# ─── Gradient background ─────────────────────────────────────────────────────

def make_gradient_bg(c1=BG, c2=BG2):
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        t = y / H
        for ch in range(3):
            arr[y, :, ch] = int(c1[ch] * (1 - t) + c2[ch] * t)
    return Image.fromarray(arr)


# ─── Title card ───────────────────────────────────────────────────────────────

def title_card(title, subtitle="", duration_s=3.5, fade_in=0.5, fade_out=0.5):
    n = int(duration_s * FPS)
    fi, fo = int(fade_in * FPS), int(fade_out * FPS)
    font_t = get_font(72, bold=True)
    font_s = get_font(34)

    for i in range(n):
        alpha = 1.0
        if i < fi:
            alpha = i / fi
        elif i > n - fo:
            alpha = (n - i) / fo

        img = make_gradient_bg()
        if alpha < 1.0:
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, int((1 - alpha) * 230)))
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay).convert("RGB")

        draw = ImageDraw.Draw(img)
        # Accent bar
        bar_w = 120
        rrect(draw, (W - bar_w) // 2, H // 2 - 80, (W + bar_w) // 2, H // 2 - 74, 3, fill=ACCENT)
        draw_text_c(draw, H // 2 - 55, title, font_t, WHITE)
        if subtitle:
            draw_text_c(draw, H // 2 + 35, subtitle, font_s, MUTED)
        yield img


def section_frames(scene_fn, duration_s, fade_in=0.3, fade_out=0.3):
    n = int(duration_s * FPS)
    fi, fo = int(fade_in * FPS), int(fade_out * FPS)
    for i in range(n):
        alpha = 1.0
        if i < fi:
            alpha = i / fi
        elif i > n - fo:
            alpha = (n - i) / fo
        base = scene_fn(i, n)
        if alpha < 1.0:
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, int((1 - alpha) * 200)))
            base = base.convert("RGBA")
            base = Image.alpha_composite(base, overlay).convert("RGB")
        yield base


# ═══════════════════════════════════════════════════════════════════════════════
#   SCENE 1: The challenge
# ═══════════════════════════════════════════════════════════════════════════════

def scene_challenge(i, n):
    img = make_gradient_bg()
    draw = ImageDraw.Draw(img)
    progress = min(1.0, i / (n * 0.6))

    # Title at top
    draw_text_c(draw, 40, "The Challenge: Long Video Understanding", get_font(42, True), ACCENT)

    # Question box
    qx, qy = 100, 110
    rrect(draw, qx, qy, W - qx, qy + 80, 12, fill=PANEL_BG, outline=BORDER)
    draw.text((qx + 24, qy + 12),
              'Q: "What sequence of actions did the camera wearer perform',
              font=get_font(22), fill=WHITE)
    draw.text((qx + 44, qy + 42),
              'while adjusting and using a microscope for sample analysis?"',
              font=get_font(22), fill=WHITE)

    # Frame grid — 32 x 6 frames flooding in
    cols, rows = 32, 6
    cell_w, cell_h = 48, 30
    gap = 3
    gx = (W - cols * (cell_w + gap)) // 2
    gy = 220
    n_shown = max(4, int(cols * rows * progress))
    rng = np.random.default_rng(42)
    draw_video_frames(draw, gx, gy, cols, rows, cell_w, cell_h, gap, rng,
                      highlight_idx=87, highlight_color=BAD, n_shown=n_shown)

    # Annotations below grid
    grid_bottom = gy + rows * (cell_h + gap) + 20
    tokens = int(10000 + 489000 * progress)
    draw_text_c(draw, grid_bottom, f"~{tokens:,} visual tokens consumed", get_font(28, True), BAD)
    draw_text_c(draw, grid_bottom + 42,
                "Only 1 of 192 frames is actually relevant to the question",
                get_font(22), MUTED)

    # Bottom label
    draw.text((100, H - 70), "256 uniformly sampled frames -- most are irrelevant noise",
              font=get_font(24), fill=MUTED)
    return img


# ═══════════════════════════════════════════════════════════════════════════════
#   SCENE 2: Passive MLLM
# ═══════════════════════════════════════════════════════════════════════════════

def scene_passive(i, n):
    img = make_gradient_bg(BG, (25, 10, 15))
    draw = ImageDraw.Draw(img)
    t = min(1.0, i / (n * 0.5))

    draw_text_c(draw, 40, "Approach 1:  Passive MLLM", get_font(44, True), BAD)

    # Frame strip
    cols = 16
    cell_w, cell_h = 80, 50
    gap = 6
    strip_w = cols * (cell_w + gap)
    gx = (W - strip_w) // 2
    gy = 140
    rng = np.random.default_rng(7)
    draw_video_frames(draw, gx, gy, cols, 1, cell_w, cell_h, gap, rng,
                      highlight_idx=11, highlight_color=BAD)

    draw.text((gx, gy + cell_h + 12), "Uniform Sampled Frames",
              font=get_font(20), fill=MUTED)
    # Arrow pointing to highlighted frame
    hx = gx + 11 * (cell_w + gap) + cell_w // 2
    draw.text((hx - 60, gy + cell_h + 12), "^ relevant", font=get_font(18, True), fill=BAD)

    # Flow: Frames --> MLLM --> Wrong Answer
    cy = 310
    # MLLM box
    rrect(draw, W // 2 - 120, cy, W // 2 + 120, cy + 80, 12, fill=PANEL_BG, outline=BORDER, width=2)
    draw_text_in_box(draw, W // 2, cy + 10, "MLLM", get_font(30, True), WHITE)
    draw_text_in_box(draw, W // 2, cy + 48, "(processes all frames)", get_font(16), MUTED)

    # Arrow from strip to MLLM
    draw.line([(W // 2, gy + cell_h + 4), (W // 2, cy)], fill=MUTED, width=2)

    # Wrong answer
    if t > 0.6:
        ry = cy + 100
        rrect(draw, W // 2 - 160, ry, W // 2 + 160, ry + 70, 12, fill=DARK_RED, outline=BAD, width=2)
        draw_text_in_box(draw, W // 2, ry + 8, "WRONG ANSWER  X", get_font(28, True), BAD)
        draw_text_in_box(draw, W // 2, ry + 42, "Misled by irrelevant frames", get_font(18), MUTED)
        draw.line([(W // 2, cy + 80), (W // 2, ry)], fill=BAD, width=2)

    # Bullet points at bottom
    by = 570
    font_bp = get_font(26)
    draw.text((140, by),      "[X]  Visual misguidance from irrelevant frames", font=font_bp, fill=WHITE)
    draw.text((140, by + 48), "[X]  All 499K tokens consumed regardless of relevance", font=font_bp, fill=WHITE)
    draw.text((140, by + 96), "[X]  No selective attention or adaptive reasoning", font=font_bp, fill=WHITE)

    return img


# ═══════════════════════════════════════════════════════════════════════════════
#   SCENE 3: Traditional Agent
# ═══════════════════════════════════════════════════════════════════════════════

def scene_trad_agent(i, n):
    img = make_gradient_bg(BG, (22, 18, 5))
    draw = ImageDraw.Draw(img)
    t = min(1.0, i / (n * 0.5))

    draw_text_c(draw, 40, "Approach 2:  Traditional Agentic Method", get_font(44, True), MID)

    # Frame strip
    cols = 14
    cell_w, cell_h = 80, 50
    gap = 6
    gx = (W - cols * (cell_w + gap)) // 2
    gy = 135
    rng = np.random.default_rng(13)
    draw_video_frames(draw, gx, gy, cols, 1, cell_w, cell_h, gap, rng)
    draw.text((gx, gy + cell_h + 10), "Uniform frames --> MLLM --> Tool call",
              font=get_font(20), fill=MUTED)

    # Tool call box (left side)
    if t > 0.25:
        bx, by = 120, 280
        bw, bh = 520, 140
        rrect(draw, bx, by, bx + bw, by + bh, 12, fill=PANEL_BG, outline=ACCENT, width=2)
        draw.text((bx + 24, by + 16), "Tool Call:", font=get_font(24, True), fill=ACCENT)
        draw.text((bx + 24, by + 54), "start_time: 3500,  end_time: 4000",
                  font=get_font(22), fill=WHITE)
        draw.text((bx + 24, by + 86), "nframes: 50,  resize: 1.0",
                  font=get_font(22), fill=WHITE)

    # Problem box (right side)
    if t > 0.5:
        px, py = 720, 280
        pw, ph = 560, 140
        rrect(draw, px, py, px + pw, py + ph, 12, fill=DARK_AMBER, outline=MID, width=2)
        draw.text((px + 24, py + 16), "[!]  Fixed FPS & resolution", font=get_font(24, True), fill=MID)
        draw.text((px + 24, py + 54), "[!]  Perception-first strategy:", font=get_font(22), fill=WHITE)
        draw.text((px + 24, py + 86), "     already committed to wrong time range",
                  font=get_font(22), fill=WHITE)

    # Wrong answer
    if t > 0.7:
        rrect(draw, W // 2 - 180, 460, W // 2 + 180, 530, 12, fill=DARK_RED, outline=BAD, width=2)
        draw_text_in_box(draw, W // 2, 470, "Still Wrong  X", get_font(28, True), BAD)
        draw_text_in_box(draw, W // 2, 502, "Fixed nframes misses action sequence",
                         get_font(18), MUTED)

    # Bullet points
    by2 = 580
    font_bp = get_font(26)
    draw.text((140, by2),       "[X]  Rigid tool interface -- fixed nframes, no resize control",
              font=font_bp, fill=WHITE)
    draw.text((140, by2 + 48),  "[X]  Perception-first: uniform frames prejudice the plan",
              font=font_bp, fill=WHITE)
    draw.text((140, by2 + 96),  "[X]  Manual, hard-coded workflow -- no end-to-end learning",
              font=font_bp, fill=WHITE)

    return img


# ═══════════════════════════════════════════════════════════════════════════════
#   SCENE 4: EVA — vertical flow, large text, visual content
# ═══════════════════════════════════════════════════════════════════════════════

def scene_eva(i, n):
    img = make_gradient_bg(BG, (5, 18, 22))
    draw = ImageDraw.Draw(img)
    progress = min(1.0, i / n)

    draw_text_c(draw, 30, "EVA:  Planning Before Perception", get_font(48, True), GOOD)

    # Layout: 3 rows showing the iterative loop
    # Row 1: Question only → Plan (text reasoning)
    # Row 2: Tool Call 1 (low-res scan) → See overview frames
    # Row 3: Tool Call 2 (zoom in) → Correct Answer

    left_x = 80
    right_x = W // 2 + 40
    col_w = W // 2 - 120
    font_step = get_font(26, True)
    font_body = get_font(22)
    font_code = get_font(20)
    font_label = get_font(18)

    # === ROW 1: Question + Plan (always visible) ===
    r1y = 110
    # Step 1: question box
    rrect(draw, left_x, r1y, left_x + col_w, r1y + 130, 12,
          fill=PANEL_BG, outline=GOOD if progress > 0 else BORDER, width=2)
    draw.text((left_x + 20, r1y + 10), "Step 1: Read Question Only",
              font=font_step, fill=GOOD)
    draw.text((left_x + 20, r1y + 48),
              '"What actions did the camera wearer',
              font=font_body, fill=WHITE)
    draw.text((left_x + 20, r1y + 78),
              ' perform while using a microscope?"',
              font=font_body, fill=WHITE)
    draw.text((left_x + 20, r1y + 108), "No frames loaded yet -- zero visual tokens",
              font=font_label, fill=MUTED)

    # Arrow
    if progress > 0.15:
        draw.text((left_x + col_w + 10, r1y + 50), "-->", font=get_font(28, True), fill=ACCENT)

    # Step 2: Plan
    if progress > 0.15:
        c = GOOD if progress > 0.15 else BORDER
        rrect(draw, right_x, r1y, right_x + col_w, r1y + 130, 12,
              fill=(12, 30, 25), outline=c, width=2)
        draw.text((right_x + 20, r1y + 10), "Step 2: Plan Strategy",
                  font=font_step, fill=GOOD)
        draw.text((right_x + 20, r1y + 48),
                  '"Let me first survey the whole video',
                  font=font_body, fill=WHITE)
        draw.text((right_x + 20, r1y + 78),
                  ' at low resolution to find relevant parts..."',
                  font=font_body, fill=WHITE)
        draw.text((right_x + 20, r1y + 108), "Reasoning before perception",
                  font=font_label, fill=MUTED)

    # === ROW 2: Tool Call 1 + Low-res overview ===
    r2y = 280
    if progress > 0.33:
        # Down arrow
        draw.text((W // 2 - 10, r2y - 28), "v", font=get_font(28, True), fill=ACCENT)

        # Tool Call 1
        rrect(draw, left_x, r2y, left_x + col_w, r2y + 130, 12,
              fill=PANEL_BG, outline=ACCENT, width=2)
        draw.text((left_x + 20, r2y + 10), "Step 3: Tool Call (Low-Res Scan)",
                  font=font_step, fill=ACCENT)
        draw.text((left_x + 20, r2y + 50),
                  "start: 0,  end: 6630", font=font_code, fill=WHITE)
        draw.text((left_x + 20, r2y + 80),
                  "nframes: 256,  resize: 0.1", font=font_code, fill=WHITE)
        draw.text((left_x + 20, r2y + 108), "Quick overview -- minimal token cost",
                  font=font_label, fill=MUTED)

    if progress > 0.33:
        draw.text((left_x + col_w + 10, r2y + 50), "-->", font=get_font(28, True), fill=ACCENT)

    # Low-res frames preview
    if progress > 0.45:
        rrect(draw, right_x, r2y, right_x + col_w, r2y + 130, 12,
              fill=(15, 20, 30), outline=BORDER, width=1)
        draw.text((right_x + 20, r2y + 8), "Low-Resolution Overview",
                  font=font_label, fill=MUTED)
        rng2 = np.random.default_rng(99)
        # Show small low-res frames
        fr_cols, fr_rows = 16, 3
        fw, fh = 40, 24
        fg = 3
        fx0 = right_x + (col_w - fr_cols * (fw + fg)) // 2
        fy0 = r2y + 32
        draw_video_frames(draw, fx0, fy0, fr_cols, fr_rows, fw, fh, fg, rng2,
                          highlight_idx=38, highlight_color=MID, low_res=True)
        # Annotation on highlighted
        draw.text((right_x + 20, r2y + 108), "^ Relevant segment identified around ~3500s",
                  font=font_label, fill=MID)

    # === ROW 3: Tool Call 2 + Correct Answer ===
    r3y = 450
    if progress > 0.6:
        draw.text((W // 2 - 10, r3y - 28), "v", font=get_font(28, True), fill=ACCENT)

        # Tool Call 2
        rrect(draw, left_x, r3y, left_x + col_w, r3y + 130, 12,
              fill=PANEL_BG, outline=ACCENT, width=2)
        draw.text((left_x + 20, r3y + 10), "Step 4: Tool Call (Zoom In, High-Res)",
                  font=font_step, fill=ACCENT)
        draw.text((left_x + 20, r3y + 50),
                  "start: 3500,  end: 4000", font=font_code, fill=WHITE)
        draw.text((left_x + 20, r3y + 80),
                  "nframes: 50,  resize: 1.0", font=font_code, fill=WHITE)
        draw.text((left_x + 20, r3y + 108), "Full resolution on the relevant segment",
                  font=font_label, fill=MUTED)

    if progress > 0.6:
        draw.text((left_x + col_w + 10, r3y + 50), "-->", font=get_font(28, True), fill=ACCENT)

    # High-res frames + correct answer
    if progress > 0.72:
        rrect(draw, right_x, r3y, right_x + col_w, r3y + 130, 12,
              fill=(10, 20, 18), outline=GOOD, width=2)
        draw.text((right_x + 20, r3y + 8), "High-Resolution Frames",
                  font=font_label, fill=MUTED)
        rng3 = np.random.default_rng(200)
        fr_cols2 = 12
        fw2, fh2 = 52, 34
        fx2 = right_x + (col_w - fr_cols2 * (fw2 + 4)) // 2
        fy2 = r3y + 32
        draw_video_frames(draw, fx2, fy2, fr_cols2, 2, fw2, fh2, 4, rng3)
        draw.text((right_x + 20, r3y + 108), "Sufficient detail to identify action sequence",
                  font=font_label, fill=GOOD)

    # === BOTTOM: Correct answer + efficiency stats ===
    if progress > 0.85:
        by = 620
        # Correct answer banner
        rrect(draw, left_x, by, left_x + col_w, by + 80, 12,
              fill=DARK_GREEN, outline=GOOD, width=3)
        draw.text((left_x + 30, by + 10), "CORRECT ANSWER", font=get_font(32, True), fill=GOOD)
        draw.text((left_x + 30, by + 48),
                  "Option B: Place petri dish -> adjust eyepieces -> ...",
                  font=font_label, fill=WHITE)

        # Efficiency stat
        rrect(draw, right_x, by, right_x + col_w, by + 80, 12,
              fill=PANEL_BG, outline=ACCENT, width=2)
        draw.text((right_x + 30, by + 10), "TOKEN EFFICIENCY",
                  font=get_font(26, True), fill=ACCENT)
        draw.text((right_x + 30, by + 46),
                  "Only ~10K tokens  (vs 499K for Qwen2.5-VL = 98% fewer)",
                  font=font_label, fill=WHITE)

    return img


# ═══════════════════════════════════════════════════════════════════════════════
#   SCENE 5: Results
# ═══════════════════════════════════════════════════════════════════════════════

def scene_results(i, n):
    img = make_gradient_bg()
    draw = ImageDraw.Draw(img)
    progress = min(1.0, i / (n * 0.65))

    draw_text_c(draw, 40, "EVA: State-of-the-Art Results", get_font(48, True), ACCENT)

    # Horizontal bar chart
    bars = [
        ("EVA-GRPO (Ours)", 37.2, GOOD),
        ("Video-R1",         36.5, (80, 130, 180)),
        ("VideoChat-R1",     33.0, (65, 100, 140)),
        ("InternVL3-8B",     32.3, (55, 80, 115)),
        ("Qwen2.5-VL-7B",   27.8, (45, 65, 90)),
    ]

    max_val = 42
    bar_h = 52
    bar_gap = 16
    name_w = 320
    bar_max_w = W - name_w - 260
    y0 = 150

    for bi, (name, val, color) in enumerate(bars):
        y = y0 + bi * (bar_h + bar_gap)
        bw = int(bar_max_w * (val / max_val) * min(1.0, progress * 1.8))

        # Name label
        draw.text((100, y + 10), name, font=get_font(24, bi == 0), fill=WHITE)

        # Bar
        rrect(draw, name_w, y, name_w + max(bw, 4), y + bar_h, 8, fill=color)

        # Value label
        if bw > 50:
            draw.text((name_w + bw + 16, y + 10), f"{val}%",
                      font=get_font(26, True), fill=WHITE)

    chart_bottom = y0 + len(bars) * (bar_h + bar_gap) + 10
    draw.text((name_w, chart_bottom),
              "Video-Holmes Benchmark -- Overall Accuracy",
              font=get_font(22), fill=MUTED)

    # Stat cards at bottom
    if progress > 0.65:
        stats = [
            ("6-12%", "accuracy gain over", "MLLM baselines"),
            ("1-3%", "gain over prior", "agent methods"),
            ("98%", "fewer visual tokens", "vs Qwen2.5-VL"),
            ("68.3%", "MLVU score", "(vs 59.1% FrameThinker)"),
        ]
        n_stats = len(stats)
        card_w = (W - 200 - (n_stats - 1) * 24) // n_stats
        card_h = 160
        card_y = H - card_h - 50

        for si, (num, line1, line2) in enumerate(stats):
            cx = 100 + si * (card_w + 24)
            rrect(draw, cx, card_y, cx + card_w, card_y + card_h, 14,
                  fill=PANEL_BG, outline=BORDER, width=1)
            # Number centered in card
            card_cx = cx + card_w // 2
            draw_text_in_box(draw, card_cx, card_y + 20, num, get_font(40, True), ACCENT)
            draw_text_in_box(draw, card_cx, card_y + 80, line1, get_font(20), MUTED)
            draw_text_in_box(draw, card_cx, card_y + 108, line2, get_font(20), MUTED)

    return img


# ═══════════════════════════════════════════════════════════════════════════════
#   Assembly
# ═══════════════════════════════════════════════════════════════════════════════

def make_video():
    global FRAME_DIR
    import shutil

    FRAME_DIR = tempfile.mkdtemp(prefix="eva_frames_")
    print(f"Generating EVA demo video frames (1920x1080) -> {FRAME_DIR}")

    frame_idx = [0]

    def collect(gen):
        for frame in gen:
            path = os.path.join(FRAME_DIR, f"frame_{frame_idx[0]:06d}.png")
            frame.save(path)
            frame_idx[0] += 1
            if frame_idx[0] % 100 == 0:
                print(f"  ... {frame_idx[0]} frames rendered")

    # Scene sequence
    collect(title_card("Long Video Understanding",
                       "A Hard Problem", 3.0))
    collect(section_frames(scene_challenge, duration_s=9))

    collect(title_card("Approach 1:  Passive MLLM", "", 2.0))
    collect(section_frames(scene_passive, duration_s=9))

    collect(title_card("Approach 2:  Traditional Agent", "", 2.0))
    collect(section_frames(scene_trad_agent, duration_s=9))

    collect(title_card("EVA:  Planning Before Perception",
                       "The agent decides what, when, and how to watch", 2.5))
    collect(section_frames(scene_eva, duration_s=18))

    collect(title_card("Results", "", 1.5))
    collect(section_frames(scene_results, duration_s=11))

    # Final card: just EVA + CVPR 2026
    collect(title_card("EVA", "CVPR 2026", 3.5))

    total = frame_idx[0]
    total_s = total / FPS
    print(f"Total frames: {total}  ({total_s:.1f}s)")

    # Use ffmpeg directly for memory efficiency
    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    pattern = os.path.join(FRAME_DIR, "frame_%06d.png")
    cmd = (f"ffmpeg -y -framerate {FPS} -i {pattern} "
           f"-c:v libx264 -crf 22 -preset fast -pix_fmt yuv420p "
           f"-an {OUTPUT}")
    print(f"Encoding: {cmd}")
    ret = os.system(cmd)
    if ret != 0:
        print("ffmpeg failed, trying moviepy fallback...")
        from moviepy.editor import ImageSequenceClip
        frames = sorted(glob.glob(os.path.join(FRAME_DIR, "*.png")))
        clip = ImageSequenceClip(frames, fps=FPS)
        clip.write_videofile(OUTPUT, codec="libx264", audio=False, logger=None)
        clip.close()

    shutil.rmtree(FRAME_DIR, ignore_errors=True)
    print(f"Video saved to: {OUTPUT}")


if __name__ == "__main__":
    make_video()
