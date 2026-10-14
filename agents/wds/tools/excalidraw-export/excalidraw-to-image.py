#!/usr/bin/env python3
"""
excalidraw-to-image.py — Render .excalidraw files to JPG/PNG images.

WDS tool excalidraw-export (agents/wds/tools/excalidraw-export.md).
Reads Excalidraw JSON and renders elements (rectangles, text, lines,
ellipses) using Pillow. Needs: python -m pip install pillow

Usage:
    python agents/wds/tools/excalidraw-export/excalidraw-to-image.py <input.excalidraw> [output.png]
    python agents/wds/tools/excalidraw-export/excalidraw-to-image.py <input.excalidraw> --update-spec <spec.md>
    python agents/wds/tools/excalidraw-export/excalidraw-to-image.py --batch <directory>

Options:
    --format jpg|png    Output format (default: png)
    --scale  N          Scale factor (default: 1.0)
    --update-spec FILE  After export, update image reference in spec markdown
    --batch DIR         Convert all .excalidraw files in directory (recursive)
    --padding N         Padding around content in pixels (default: 40)
"""

import json
import sys
import os
import re
import glob
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------------------
# Font mapping — Excalidraw fontFamily values
# ---------------------------------------------------------------------------
# 1 = Virgil (hand-drawn) → we use a clean sans-serif instead
# 2 = Helvetica / Arial
# 3 = Cascadia / monospace
# 4 = Comic Shanns (Excalidraw+ only)

# Each family lists candidates in order: Windows, macOS, Linux. The first
# one that loads is used; plain file names are looked up in the system font
# folders by Pillow.
SANS = ["C:/Windows/Fonts/segoeui.ttf", "/System/Library/Fonts/Helvetica.ttc",
        "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
ARIAL = ["C:/Windows/Fonts/arial.ttf", "/Library/Fonts/Arial.ttf",
         "/System/Library/Fonts/Supplemental/Arial.ttf"] + SANS
MONO = ["C:/Windows/Fonts/consola.ttf", "/System/Library/Fonts/Menlo.ttc",
        "DejaVuSansMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]

FONT_MAP = {
    1: SANS,    # hand-drawn → clean sans
    2: ARIAL,   # Helvetica → Arial
    3: MONO,    # monospace
    4: SANS,    # fallback
}


def hex_to_rgba(hex_color, opacity=100):
    """Convert hex color + opacity (0-100) to RGBA tuple. Returns None for transparent."""
    if not hex_color or hex_color == "transparent":
        return None
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    a = int(255 * opacity / 100)
    return (r, g, b, a)


def get_font(family, size):
    """Load a Pillow font for the given Excalidraw fontFamily and size."""
    for path in FONT_MAP.get(family, FONT_MAP[2]):
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def compute_bounds(elements):
    """Compute the bounding box of all visible elements."""
    min_x, min_y = float("inf"), float("inf")
    max_x, max_y = float("-inf"), float("-inf")

    for el in elements:
        x, y = el["x"], el["y"]
        w = el.get("width", 0)
        h = el.get("height", 0)

        if el["type"] == "line":
            points = el.get("points", [])
            for px, py in points:
                min_x = min(min_x, x + px)
                min_y = min(min_y, y + py)
                max_x = max(max_x, x + px)
                max_y = max(max_y, y + py)
        else:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)

    return min_x, min_y, max_x, max_y


def draw_rectangle(draw, el, offset_x, offset_y, scale):
    """Render a rectangle element."""
    x = (el["x"] - offset_x) * scale
    y = (el["y"] - offset_y) * scale
    w = el["width"] * scale
    h = el["height"] * scale
    opacity = el.get("opacity", 100)

    # Fill
    bg = el.get("backgroundColor", "transparent")
    fill = hex_to_rgba(bg, opacity)
    if fill:
        draw.rectangle([x, y, x + w, y + h], fill=fill)

    # Stroke
    stroke_color = el.get("strokeColor", "#1e1e1e")
    stroke_width = max(1, int(el.get("strokeWidth", 1) * scale))
    stroke = hex_to_rgba(stroke_color, opacity)
    if not stroke:
        return

    # Rounded corners
    roundness = el.get("roundness")
    if roundness:
        radius = min(w, h) * 0.1  # approximate
        draw.rounded_rectangle([x, y, x + w, y + h], radius=radius,
                               outline=stroke, width=stroke_width)
    else:
        draw.rectangle([x, y, x + w, y + h], outline=stroke, width=stroke_width)


def draw_ellipse(draw, el, offset_x, offset_y, scale):
    """Render an ellipse element."""
    x = (el["x"] - offset_x) * scale
    y = (el["y"] - offset_y) * scale
    w = el["width"] * scale
    h = el["height"] * scale
    opacity = el.get("opacity", 100)

    bg = el.get("backgroundColor", "transparent")
    fill = hex_to_rgba(bg, opacity)

    stroke_color = el.get("strokeColor", "#1e1e1e")
    stroke_width = max(1, int(el.get("strokeWidth", 1) * scale))
    stroke = hex_to_rgba(stroke_color, opacity)

    draw.ellipse([x, y, x + w, y + h], fill=fill, outline=stroke, width=stroke_width)


def draw_text(draw, el, offset_x, offset_y, scale):
    """Render a text element."""
    x = (el["x"] - offset_x) * scale
    y = (el["y"] - offset_y) * scale
    w = el.get("width", 0) * scale
    opacity = el.get("opacity", 100)
    text = el.get("text", "")
    if not text:
        return

    font_size = max(8, int(el.get("fontSize", 16) * scale))
    font_family = el.get("fontFamily", 2)
    font = get_font(font_family, font_size)

    color = hex_to_rgba(el.get("strokeColor", "#1e1e1e"), opacity)

    # Handle text alignment
    align = el.get("textAlign", "left")

    for i, line in enumerate(text.split("\n")):
        line_y = y + i * font_size * 1.2

        if align == "center" and w > 0:
            bbox = font.getbbox(line)
            line_w = bbox[2] - bbox[0]
            line_x = x + (w - line_w) / 2
        elif align == "right" and w > 0:
            bbox = font.getbbox(line)
            line_w = bbox[2] - bbox[0]
            line_x = x + w - line_w
        else:
            line_x = x

        draw.text((line_x, line_y), line, fill=color, font=font)


def draw_line(draw, el, offset_x, offset_y, scale):
    """Render a line element (may have multiple points)."""
    points = el.get("points", [])
    if len(points) < 2:
        return

    x, y = el["x"], el["y"]
    opacity = el.get("opacity", 100)
    stroke_color = el.get("strokeColor", "#1e1e1e")
    stroke_width = max(1, int(el.get("strokeWidth", 1) * scale))
    color = hex_to_rgba(stroke_color, opacity)

    scaled_points = [
        ((x + px - offset_x) * scale, (y + py - offset_y) * scale)
        for px, py in points
    ]

    for i in range(len(scaled_points) - 1):
        draw.line([scaled_points[i], scaled_points[i + 1]],
                  fill=color, width=stroke_width)


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

RENDERERS = {
    "rectangle": draw_rectangle,
    "ellipse": draw_ellipse,
    "text": draw_text,
    "line": draw_line,
}


def render_excalidraw(data, scale=1.0, padding=40, bg_color=None):
    """Render an Excalidraw document to a Pillow Image."""
    # Filter visible elements
    elements = [
        el for el in data.get("elements", [])
        if not el.get("isDeleted", False)
    ]

    if not elements:
        # Empty document — return small blank image
        img = Image.new("RGBA", (200, 200), (255, 255, 255, 255))
        return img

    # Compute bounds
    min_x, min_y, max_x, max_y = compute_bounds(elements)

    # Canvas size
    canvas_w = int((max_x - min_x) * scale + padding * 2)
    canvas_h = int((max_y - min_y) * scale + padding * 2)

    # Background color from appState or default
    if bg_color is None:
        bg_color = data.get("appState", {}).get("viewBackgroundColor", "#ffffff")
    bg_rgba = hex_to_rgba(bg_color, 100) or (255, 255, 255, 255)

    img = Image.new("RGBA", (canvas_w, canvas_h), bg_rgba)
    draw = ImageDraw.Draw(img)

    # Offset so content starts at (padding, padding)
    offset_x = min_x - padding / scale
    offset_y = min_y - padding / scale

    # Sort by element order (index field or array position)
    for el in elements:
        el_type = el.get("type")
        renderer = RENDERERS.get(el_type)
        if renderer:
            renderer(draw, el, offset_x, offset_y, scale)

    return img


def convert_file(input_path, output_path=None, fmt="png", scale=1.0, padding=40):
    """Convert a single .excalidraw file to an image."""
    input_path = Path(input_path)

    if output_path is None:
        output_path = input_path.with_suffix(f".{fmt}")
    else:
        output_path = Path(output_path)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    img = render_excalidraw(data, scale=scale, padding=padding)

    # Convert to RGB for JPG (no alpha)
    if fmt.lower() in ("jpg", "jpeg"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
        bg.save(output_path, "JPEG", quality=92)
    else:
        img.save(output_path, "PNG")

    return output_path


def update_spec_image(spec_path, image_path):
    """Update a markdown spec to reference the generated image.

    Looks for image references matching the base name pattern and
    ensures they point to the generated file.
    """
    spec_path = Path(spec_path)
    image_path = Path(image_path)

    # Make image path relative to spec location
    try:
        rel_path = image_path.relative_to(spec_path.parent)
    except ValueError:
        rel_path = image_path

    content = spec_path.read_text(encoding="utf-8")

    # Pattern: ![...](Sketches/something.ext)
    # Replace with actual generated file
    stem = image_path.stem.rsplit("-wireframe", 1)[0]  # e.g. "1.1-start"
    pattern = re.compile(
        r"(!\[[^\]]*\]\()([^)]*" + re.escape(stem) + r"[^)]*)(\.excalidraw)?(\.(png|jpg|jpeg))(\))",
        re.IGNORECASE,
    )

    def replacer(m):
        return f"{m.group(1)}{rel_path}{m.group(6)}"

    new_content = pattern.sub(replacer, content)

    if new_content != content:
        spec_path.write_text(new_content, encoding="utf-8")
        return True
    return False


def batch_convert(directory, fmt="png", scale=1.0, padding=40):
    """Convert all .excalidraw files in a directory tree."""
    directory = Path(directory)
    results = []

    for excal_file in directory.rglob("*.excalidraw"):
        output = excal_file.with_suffix(f".{fmt}")
        try:
            convert_file(excal_file, output, fmt=fmt, scale=scale, padding=padding)
            results.append((excal_file, output, None))
            print(f"  OK  {excal_file.name} -> {output.name}")
        except Exception as e:
            results.append((excal_file, None, str(e)))
            print(f"  ERR {excal_file.name}: {e}")

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Render Excalidraw files to JPG/PNG images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", nargs="?", help="Input .excalidraw file")
    parser.add_argument("output", nargs="?", help="Output image path (optional)")
    parser.add_argument("--format", choices=["png", "jpg"], default="png",
                        help="Output format (default: png, use jpg for colorful/photo-heavy designs)")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="Scale factor (default: 1.0)")
    parser.add_argument("--padding", type=int, default=40,
                        help="Padding in pixels (default: 40)")
    parser.add_argument("--update-spec", metavar="FILE",
                        help="Update image reference in spec markdown")
    parser.add_argument("--batch", metavar="DIR",
                        help="Batch convert all .excalidraw in directory")

    args = parser.parse_args()

    if args.batch:
        fmt = args.format
        results = batch_convert(args.batch, fmt=fmt, scale=args.scale, padding=args.padding)
        ok = sum(1 for _, _, err in results if err is None)
        fail = sum(1 for _, _, err in results if err is not None)
        print(f"\nDone: {ok} converted, {fail} errors")
        return

    if not args.input:
        parser.print_help()
        sys.exit(1)

    output_path = convert_file(
        args.input, args.output,
        fmt=args.format, scale=args.scale, padding=args.padding,
    )
    print(f"Saved: {output_path}")

    if args.update_spec:
        updated = update_spec_image(args.update_spec, output_path)
        if updated:
            print(f"Updated spec: {args.update_spec}")
        else:
            print(f"No matching image reference found in {args.update_spec}")


if __name__ == "__main__":
    main()
