"""
EVA Demo Video Generator
Creates a ~70s explainer video showing EVA's planning-before-perception advantage.

Requirements:
  pip install moviepy==1.0.3 Pillow requests numpy

Usage:
  cd ~/EVA && python scripts/make_demo_video.py
"""

import os
import sys
import textwrap
import tempfile
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import urllib.request

OUTPUT = "static/media/demo.mp4"
W, H = 1280, 720
FPS = 24

BG        = (13, 17, 23)
ACCENT    = (0, 180, 216)
GOOD      = (6, 214, 160)
BAD       = (239, 71, 111)
MID       = (255, 209, 102)
WHITE     = (230, 237, 243)
MUTED     = (139, 148, 158)
PANEL_BG  = (22, 27, 34)
BORDER    = (48, 54, 61)


# ─── Font helpers ────────────────────────────────────────────────────────────

def get_font(size, bold=False):
    """Try system fonts; fall back to PIL default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/nfs/stak/users/zhanyaol/.local/share/fonts/Inter-Bold.ttf" if bold else
        "/nfs/stak/users/zhanyaol/.local/share/fonts/Inter-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_text_centered(draw, y, text, font, color=WHITE, wrap_width=None):
    if wrap_width:
        lines = textwrap.wrap(text, wrap_width)
    else:
        lines = [text]
    for line in lines:
        tw, th = text_size(draw, line, font)
        draw.text(((W - tw) // 2, y), line, font=font, fill=color)
        y += th + 6
    return y


def draw_rounded_rect(draw, x0, y0, x1, y1, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=outline, width=width)


# ─── Frame factories ──────────────────────────────────────────────────────────

def blank():
    img = Image.new("RGB", (W, H), BG)
    return img


def make_gradient_bg(color1=BG, color2=(0, 20, 40)):
    img = blank()
    arr = np.array(img, dtype=float)
    for y in range(H):
        t = y / H
        for c in range(3):
            arr[y, :, c] = color1[c] * (1 - t) + color2[c] * t
    return Image.fromarray(arr.astype(np.uint8))


def draw_frame_grid(img, n_frames=32, highlight_idx=None, alpha=200):
    """Draw a horizontal strip of mini 'frames' (colored rectangles)."""
    draw = ImageDraw.Draw(img)
    cols = min(n_frames, 32)
    rows = max(1, n_frames // cols)
    cell_w = min(70, (W - 80) // cols)
    cell_h = int(cell_w * 0.56)
    total_w = cols * cell_w + (cols - 1) * 4
    total_h = rows * cell_h + (rows - 1) * 4
    x0 = (W - total_w) // 2
    y0 = (H - total_h) // 2

    rng = np.random.default_rng(42)
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            x = x0 + c * (cell_w + 4)
            y = y0 + r * (cell_h + 4)
            # Random grey scene color
            grey = int(rng.integers(40, 90))
            fill = (grey, grey + 5, grey + 10)
            if highlight_idx is not None and idx == highlight_idx:
                fill = (80, 20, 30)   # reddish highlight
                draw.rectangle([x, y, x + cell_w, y + cell_h], fill=fill, outline=BAD, width=2)
            else:
                draw.rectangle([x, y, x + cell_w, y + cell_h], fill=fill, outline=BORDER, width=1)
    return img


def title_card(title, subtitle="", duration_s=4, fade_in=0.5, fade_out=0.5):
    """Yield PIL frames for a simple title card."""
    n = int(duration_s * FPS)
    fi = int(fade_in * FPS)
    fo = int(fade_out * FPS)

    font_t = get_font(56, bold=True)
    font_s = get_font(26)

    for i in range(n):
        alpha = 1.0
        if i < fi:
            alpha = i / fi
        elif i > n - fo:
            alpha = (n - i) / fo

        img = make_gradient_bg()
        # Dim overlay
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, int((1 - alpha) * 220)))
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay).convert("RGB")

        draw = ImageDraw.Draw(img)
        # Accent line
        draw.rectangle([(W // 2 - 60, H // 2 - 70), (W // 2 + 60, H // 2 - 66)], fill=ACCENT)
        draw_text_centered(draw, H // 2 - 50, title, font_t, color=WHITE, wrap_width=40)
        if subtitle:
            draw_text_centered(draw, H // 2 + 30, subtitle, font_s, color=tuple(MUTED), wrap_width=60)
        yield img


def section_frames(scene_fn, duration_s, fade_in=0.3, fade_out=0.3):
    """Yield frames from a scene function with fade."""
    n = int(duration_s * FPS)
    fi = int(fade_in * FPS)
    fo = int(fade_out * FPS)
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


# ─── Individual scenes ────────────────────────────────────────────────────────

def scene_challenge(i, n):
    """Scene 1: The problem — too many frames."""
    img = make_gradient_bg()
    draw = ImageDraw.Draw(img)

    font_h = get_font(30, bold=True)
    font_b = get_font(19)
    font_m = get_font(15)

    # Question box (top)
    draw_rounded_rect(draw, 60, 40, W - 60, 130, 10, fill=PANEL_BG, outline=BORDER, width=1)
    draw.text((80, 58), "Q: What sequence of actions did the camera wearer perform", font=font_b, fill=WHITE)
    draw.text((80, 84), "   while adjusting and using a microscope for sample analysis?", font=font_b, fill=WHITE)

    progress = min(1.0, i / (n * 0.6))

    # Frame grid — show frames flooding in
    n_shown = max(8, int(256 * progress))
    cell_w, cell_h = 34, 20
    cols = 32
    rows = 8
    x0 = 60
    y0 = 155
    rng = np.random.default_rng(42)
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            if idx >= n_shown:
                break
            x = x0 + c * (cell_w + 2)
            y = y0 + r * (cell_h + 2)
            grey = int(rng.integers(35, 80))
            fill = (grey, grey + 4, grey + 8)
            # One "relevant" frame
            if idx == 110:
                fill = (60, 15, 20)
                draw.rectangle([x, y, x + cell_w, y + cell_h], fill=fill, outline=BAD, width=2)
            else:
                draw.rectangle([x, y, x + cell_w, y + cell_h], fill=fill, outline=BORDER, width=1)

    # Token count annotation
    tokens = int(10000 + 489000 * progress)
    draw_text_centered(draw, 345, f"≈ {tokens:,} visual tokens", font_b, color=BAD)
    draw_text_centered(draw, 375, f"Only 1 of 256 frames is actually relevant", font_m, color=tuple(MUTED))

    # Title overlay
    draw.text((60, H - 80), "The Challenge: Long Video Understanding", font=font_h, fill=ACCENT)
    return img


def scene_passive(i, n):
    """Scene 2: Passive MLLM."""
    img = make_gradient_bg((13, 17, 23), (25, 10, 15))
    draw = ImageDraw.Draw(img)
    font_h = get_font(32, bold=True)
    font_b = get_font(19)
    font_m = get_font(15)

    # Title
    draw.text((60, 40), "Approach 1: Passive MLLM", font=font_h, fill=BAD)

    # Frame strip
    cell_w, cell_h = 50, 30
    cols = 16
    rng = np.random.default_rng(7)
    x0 = 60
    y0 = 110
    for c in range(cols):
        x = x0 + c * (cell_w + 3)
        grey = int(rng.integers(40, 85))
        fill = (grey, grey + 4, grey + 8)
        if c == 9:
            fill = (70, 18, 25)
            draw.rectangle([x, y0, x + cell_w, y0 + cell_h], fill=fill, outline=BAD, width=2)
        else:
            draw.rectangle([x, y0, x + cell_w, y0 + cell_h], fill=fill, outline=BORDER, width=1)
    draw.text((x0, y0 + cell_h + 8), "Uniform Sampled Frames Input                           ↑ Only 1 relevant frame", font=font_m, fill=tuple(MUTED))

    # Arrow to MLLM
    t = min(1.0, i / (n * 0.4))
    arrow_x = int(60 + t * 450)
    draw.line([(60 + cols * (cell_w + 3), y0 + 15), (arrow_x, y0 + 15)], fill=MUTED, width=2)

    # MLLM box
    if t > 0.5:
        draw_rounded_rect(draw, 700, 90, 920, 160, 10, fill=PANEL_BG, outline=BORDER)
        draw_text_centered(draw, 112, "MLLM", get_font(22, bold=True), color=WHITE)
        draw_text_centered(draw, 138, "🤖", get_font(16), color=WHITE)

    # Wrong answer
    if t > 0.8:
        draw_rounded_rect(draw, 940, 90, 1200, 160, 10, fill=(50, 10, 15), outline=BAD)
        draw_text_centered(draw, 108, "Wrong Answer", font_b, color=BAD)
        draw_text_centered(draw, 135, "✗", get_font(22, bold=True), color=BAD)

    # Explanation
    draw.text((60, 300), "❌  Visual misguidance from irrelevant frames", font=font_b, fill=WHITE)
    draw.text((60, 335), "❌  All 499K tokens consumed regardless of relevance", font=font_b, fill=WHITE)
    draw.text((60, 370), "❌  No selective attention or adaptive reasoning", font=font_b, fill=WHITE)

    return img


def scene_trad_agent(i, n):
    """Scene 3: Traditional Agent."""
    img = make_gradient_bg((13, 17, 23), (20, 18, 5))
    draw = ImageDraw.Draw(img)
    font_h = get_font(32, bold=True)
    font_b = get_font(19)
    font_m = get_font(15)
    font_code = get_font(14)

    draw.text((60, 40), "Approach 2: Traditional Agentic Method", font=font_h, fill=MID)

    # Uniform frames
    cell_w, cell_h = 50, 30
    cols = 16
    rng = np.random.default_rng(13)
    x0 = 60
    y0 = 110
    for c in range(cols):
        x = x0 + c * (cell_w + 3)
        grey = int(rng.integers(40, 85))
        fill = (grey, grey + 4, grey + 8)
        draw.rectangle([x, y0, x + cell_w, y0 + cell_h], fill=fill, outline=BORDER, width=1)
    draw.text((x0, y0 + cell_h + 8), "Uniform frames → MLLM → tool call", font=font_m, fill=tuple(MUTED))

    t = min(1.0, i / (n * 0.5))

    # Tool call box
    if t > 0.2:
        draw_rounded_rect(draw, 60, 200, 480, 290, 10, fill=PANEL_BG, outline=BORDER)
        draw.text((80, 215), "Tool Call:", font=font_b, fill=ACCENT)
        draw.text((80, 240), '{ start_time: 3500, end_time: 4000,', font=font_code, fill=WHITE)
        draw.text((80, 262), '  nframes: 50, resize: 1.0 }', font=font_code, fill=WHITE)

    # Problem annotation
    if t > 0.5:
        draw_rounded_rect(draw, 510, 200, 900, 290, 10, fill=(50, 40, 5), outline=MID)
        draw.text((530, 215), "⚠  Fixed FPS & resolution", font=font_b, fill=MID)
        draw.text((530, 245), "⚠  Perception-first: already committed", font=font_b, fill=MID)
        draw.text((530, 270), "   to wrong time range", font=font_b, fill=MID)

    # Wrong answer still
    if t > 0.75:
        draw_rounded_rect(draw, 60, 330, 360, 400, 10, fill=(50, 10, 15), outline=BAD)
        draw_text_centered(draw, 348, "Still Wrong  ✗", font_b, color=BAD)

    draw.text((60, H - 140), "❌  Rigid tool interface (fixed nframes, no resize control)", font=font_b, fill=WHITE)
    draw.text((60, H - 108), "❌  Perception-first: uniform frames prejudice the plan", font=font_b, fill=WHITE)
    draw.text((60, H - 76),  "❌  Manual, hard-coded workflow — no end-to-end learning", font=font_b, fill=WHITE)
    return img


def scene_eva(i, n):
    """Scene 4: EVA in action."""
    img = make_gradient_bg((13, 17, 23), (5, 20, 18))
    draw = ImageDraw.Draw(img)
    font_h = get_font(32, bold=True)
    font_b = get_font(18)
    font_m = get_font(14)
    font_code = get_font(13)

    draw.text((60, 30), "EVA: Planning Before Perception", font=font_h, fill=GOOD)

    # Timeline (5 steps)
    steps = [
        ("📋 Question Only", "Agent reads the question\nNo frames yet.", 0.0),
        ("🗺️ Plan", '"Let me survey the full video\nat low resolution first..."', 0.18),
        ("🔧 Tool Call 1", "{start:0, end:6630,\nnframes:256, resize:0.1}", 0.36),
        ("🔍 Identify Window", "Relevant segment found:\n~3500s → ~4000s", 0.58),
        ("🔧 Tool Call 2 + Answer", "{start:3500, end:4000,\nnframes:50, resize:1.0}\n→ Correct Answer ✓", 0.76),
    ]

    progress = min(1.0, i / n)

    box_w = (W - 120 - 4 * 20) // 5
    box_h = 190

    for idx, (title, desc, threshold) in enumerate(steps):
        x = 60 + idx * (box_w + 20)
        y = 100

        visible = progress >= threshold
        alpha_fill = PANEL_BG if not visible else (15, 35, 30)
        outline_col = BORDER if not visible else GOOD
        title_col = tuple(MUTED) if not visible else GOOD

        draw_rounded_rect(draw, x, y, x + box_w, y + box_h, 8, fill=alpha_fill, outline=outline_col)
        # Step number
        draw.text((x + 10, y + 8), f"{'0' if idx < 9 else ''}{idx + 1}", font=get_font(11), fill=tuple(MUTED))

        tw, _ = text_size(draw, title, font_m)
        draw.text((x + (box_w - tw) // 2, y + 26), title, font=font_m, fill=title_col)

        # Description (wrapped)
        lines = desc.split('\n')
        ty = y + 62
        for line in lines:
            tw2, th = text_size(draw, line, font_code)
            draw.text((x + (box_w - tw2) // 2, ty), line, font=font_code, fill=WHITE if visible else tuple(BORDER))
            ty += th + 5

        # Arrow between steps
        if idx < len(steps) - 1:
            ax = x + box_w + 8
            ay = y + box_h // 2
            draw.text((ax, ay - 8), "→", font=get_font(16, bold=True), fill=ACCENT if visible else tuple(BORDER))

    # Efficiency bar at bottom
    if progress > 0.8:
        eff_t = (progress - 0.8) / 0.2
        draw.text((60, 330), "Token Efficiency:", font=font_b, fill=WHITE)
        # Qwen bar
        draw_rounded_rect(draw, 60, 360, 60 + int(600 * 1.0), 385, 4, fill=(50, 20, 20), outline=BAD)
        draw.text((680, 363), "Qwen2.5-VL: 499K tokens", font=font_m, fill=tuple(MUTED))
        # EVA bar
        eva_w = int(600 * 0.02 * eff_t)
        draw_rounded_rect(draw, 60, 396, 60 + eva_w, 421, 4, fill=(10, 60, 45), outline=GOOD)
        if eff_t > 0.5:
            draw.text((80 + eva_w, 399), f"EVA: ~10K tokens ({int(2 * eff_t)}%)", font=font_m, fill=GOOD)

    # Final result
    if progress > 0.9:
        draw_rounded_rect(draw, W - 280, H - 100, W - 40, H - 40, 10, fill=(10, 50, 35), outline=GOOD, width=2)
        draw_text_centered(draw, H - 88, "Correct Answer  ✓", font_b, color=GOOD)

    return img


def scene_results(i, n):
    """Scene 5: Results summary."""
    img = make_gradient_bg()
    draw = ImageDraw.Draw(img)
    font_h = get_font(36, bold=True)
    font_b = get_font(20)
    font_m = get_font(16)

    draw_text_centered(draw, 50, "EVA Results", font_h, color=ACCENT)

    progress = min(1.0, i / (n * 0.7))

    # Bars
    bars = [
        ("EVA-GRPO", 37.2, GOOD),
        ("Video-R1", 36.5, (100, 150, 200)),
        ("VideoChat-R1", 33.0, (80, 100, 130)),
        ("InternVL3-8B", 32.3, (60, 80, 110)),
    ]

    max_val = 40
    bar_h = 44
    y0 = 140
    bar_max_w = W - 320

    for bi, (name, val, color) in enumerate(bars):
        y = y0 + bi * (bar_h + 12)
        bw = int(bar_max_w * (val / max_val) * min(1.0, progress * 2))
        draw_rounded_rect(draw, 240, y, 240 + bw, y + bar_h, 6, fill=color)
        draw.text((60, y + 10), name, font=font_m, fill=WHITE)
        if bw > 60:
            draw.text((240 + bw + 10, y + 12), f"{val}%", font=font_b, fill=WHITE)

    draw.text((240, y0 + len(bars) * (bar_h + 12) + 10), "← Video-Holmes Overall Accuracy", font=font_m, fill=tuple(MUTED))

    # Extra stats
    if progress > 0.7:
        stats = [
            ("6–12%", "improvement over\nMLLM baselines"),
            ("1–3%", "gains over\nprior agents"),
            ("98%", "fewer visual\ntokens vs Qwen"),
        ]
        sx0 = 60
        sw = (W - 120) // 3
        sy = H - 160
        for si, (num, lab) in enumerate(stats):
            sx = sx0 + si * (sw + 10)
            draw_rounded_rect(draw, sx, sy, sx + sw - 10, sy + 120, 10, fill=PANEL_BG, outline=BORDER)
            draw_text_centered(draw, sy + 14, num, get_font(32, bold=True), color=ACCENT)
            for line in lab.split('\n'):
                draw_text_centered(draw, sy + 62 + lab.split('\n').index(line) * 22, line, font_m, color=tuple(MUTED))

    return img


# ─── Assembly ─────────────────────────────────────────────────────────────────

def make_video():
    try:
        from moviepy.editor import ImageSequenceClip
    except ImportError:
        print("Installing moviepy...")
        os.system(f"{sys.executable} -m pip install moviepy==1.0.3 --quiet")
        from moviepy.editor import ImageSequenceClip

    print("Generating demo video frames...")
    all_frames = []

    def collect(gen):
        for frame in gen:
            all_frames.append(np.array(frame))

    # Scene sequence
    collect(title_card("Long Video Understanding", "A Hard Problem — and EVA's Solution", 3.5))
    collect(section_frames(scene_challenge,   duration_s=9))
    collect(title_card("Approach 1: Passive MLLM", "", 2.0))
    collect(section_frames(scene_passive,     duration_s=9))
    collect(title_card("Approach 2: Traditional Agent", "", 2.0))
    collect(section_frames(scene_trad_agent,  duration_s=9))
    collect(title_card("EVA: Planning Before Perception", "Watch the agent decide what, when, and how to watch", 2.5))
    collect(section_frames(scene_eva,         duration_s=16))
    collect(title_card("Results", "State-of-the-art across 6 benchmarks", 2.0))
    collect(section_frames(scene_results,     duration_s=10))
    collect(title_card("EVA", "arXiv 2603.22918  ·  CVPR 2026  ·  SenseTime Research", 3.5))

    print(f"Total frames: {len(all_frames)} ({len(all_frames)/FPS:.1f}s)")

    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    clip = ImageSequenceClip(all_frames, fps=FPS)
    clip.write_videofile(OUTPUT, codec="libx264", audio=False, logger=None,
                         ffmpeg_params=["-crf", "23", "-preset", "fast"])
    clip.close()
    print(f"Video saved to: {OUTPUT}")


if __name__ == "__main__":
    make_video()
