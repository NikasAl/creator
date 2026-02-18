#!/usr/bin/env python3
import argparse
import os
import sys
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont


SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

STROKE_WIDTH = 3

COLOR_MAP = {
    "red": (255, 0, 0, 255),
    "green": (0, 255, 0, 255),
    "blue": (0, 0, 255, 255),
    "yellow": (255, 255, 0, 255),
    "white": (255, 255, 255, 255),
    "black": (0, 0, 0, 255),
    "cyan": (0, 255, 255, 255),
}


def parse_color_name(color_name: str) -> Tuple[int, int, int, int]:
    """Parse a color name string and return RGBA tuple."""
    color_name_lower = color_name.lower().strip()
    if color_name_lower not in COLOR_MAP:
        available = ", ".join(sorted(COLOR_MAP.keys()))
        raise ValueError(f"Unknown color '{color_name}'. Available colors: {available}")
    return COLOR_MAP[color_name_lower]


def list_images(images_dir: str) -> List[str]:
    if not os.path.isdir(images_dir):
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    files = [
        os.path.join(images_dir, f)
        for f in os.listdir(images_dir)
        if os.path.splitext(f.lower())[1] in SUPPORTED_EXTENSIONS
    ]
    files.sort()
    return files


def try_load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_path:
        try:
            return ImageFont.truetype(font_path, size=size)
        except Exception:
            pass
    # Try common system fonts
    for candidate in [
        "/usr/share/fonts/TTF/DejaVuSerif-BoldItalic.ttf",
    ]:
        if os.path.isfile(candidate):
            try:
                return ImageFont.truetype(candidate, size=size)
            except Exception:
                continue
    # Fallback to default PIL bitmap font (no sizing support)
    return ImageFont.load_default()


def process_text_escapes(text: str) -> str:
    """Process escape sequences in text (like \\n) to actual characters."""
    # Only process \n escape sequences, leave other characters intact
    return text.replace('\\n', '\n')


def wrap_text_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    if not text:
        return ""
    lines: List[str] = []
    # Process escape sequences first
    processed_text = process_text_escapes(text)
    # Respect explicit newlines by wrapping each paragraph separately
    paragraphs = processed_text.splitlines()
    for para in paragraphs:
        if para.strip() == "":
            # Preserve empty line
            lines.append("")
            continue
        words = para.split()
        line_words: List[str] = []
        for word in words:
            trial = (" ".join(line_words + [word])).strip()
            left, top, right, bottom = draw.textbbox((0, 0), trial, font=font)
            width = right - left
            if width <= max_width or not line_words:
                line_words.append(word)
            else:
                lines.append(" ".join(line_words))
                line_words = [word]
        if line_words:
            lines.append(" ".join(line_words))
    return "\n".join(lines)


def compute_font_for_text(
    draw: ImageDraw.ImageDraw,
    base_font_path: str,
    text: str,
    image_width: int,
    max_ratio: float = 0.85,
) -> Tuple[ImageFont.ImageFont, str]:
    target_width = int(image_width * max_ratio)
    # Start with a font size proportional to image width and then adjust downwards
    size = max(16, image_width // 18)
    while size >= 12:
        font = try_load_font(base_font_path, size)
        wrapped = wrap_text_to_width(draw, text, font, target_width)
        left, top, right, bottom = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=4)
        width = right - left
        if width <= target_width:
            return font, wrapped
        size -= 2
    # Fallback small font
    font = try_load_font(base_font_path, 12)
    wrapped = wrap_text_to_width(draw, text, font, target_width)
    return font, wrapped


def add_text_overlay(
    image: Image.Image,
    text: str,
    font_path: str | None = None,
    opacity: int = 140,
    padding_ratio: float = 0.03,
    edge_margin_ratio: float = 0.02,
    vertical_position: str = "bottom",
    radius: int | None = None,
    stroke_width: int = 0,
    stroke_color: Tuple[int, int, int, int] = (0, 0, 0, 255),
) -> Image.Image:
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    width, height = image.size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font, wrapped_text = compute_font_for_text(draw, font_path or "", text, width)

    # Compute text bounding box
    left, top, right, bottom = draw.multiline_textbbox((0, 0), wrapped_text, font=font, spacing=4)
    text_width = right - left
    text_height = bottom - top

    # Internal padding around text inside the rectangle
    padding = int(min(width, height) * padding_ratio)
    rect_width = text_width + padding * 2
    rect_height = text_height + padding * 2

    # Position rectangle
    x = (width - rect_width) // 2
    if vertical_position == "top":
        y = int(min(width, height) * edge_margin_ratio)
    elif vertical_position == "middle":
        y = (height - rect_height) // 2
    else:  # bottom
        y = height - rect_height - int(min(width, height) * edge_margin_ratio)

    # Draw semi-transparent rounded rectangle
    rect_color = (0, 0, 0, max(0, min(255, opacity)))
    if radius is None:
        radius = max(8, int(min(width, height) * 0.02))
    try:
        draw.rounded_rectangle([x, y, x + rect_width, y + rect_height], radius=radius, fill=rect_color)
    except Exception:
        draw.rectangle([x, y, x + rect_width, y + rect_height], fill=rect_color)

    # Draw text in white
    text_x = x + padding
    text_y = y + padding
    draw.multiline_text(
        (text_x, text_y),
        wrapped_text,
        font=font,
        fill=(255, 255, 255, 255),
        spacing=4,
        align="center",
        stroke_width=stroke_width,
        stroke_fill=stroke_color,
    )

    # Composite overlay onto image
    composed = Image.alpha_composite(image, overlay)
    return composed.convert("RGB")


def choose_interactively(images: List[str]) -> int:
    print("Found images:")
    for idx, path in enumerate(images):
        print(f"  [{idx}] {os.path.basename(path)}")
    while True:
        try:
            choice = input("Enter image number to use: ").strip()
            if choice == "":
                continue
            index = int(choice)
            if 0 <= index < len(images):
                return index
        except ValueError:
            pass
        print("Invalid selection. Try again.")


def choose_color_interactively() -> str | None:
    """Interactively choose a stroke color. Returns color name or None for no stroke."""
    colors = sorted(COLOR_MAP.keys())
    print("Available stroke colors:")
    print("  [none] No stroke (default)")
    for idx, color in enumerate(colors):
        print(f"  [{idx}] {color}")
    while True:
        try:
            choice = input("Enter color number or 'none' to skip: ").strip().lower()
            if choice == "" or choice == "none":
                return None
            index = int(choice)
            if 0 <= index < len(colors):
                return colors[index]
        except ValueError:
            pass
        print("Invalid selection. Try again.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create cover.webp with semi-transparent text overlay from a pipeline image.")
    parser.add_argument("pipeline_dir", help="Path to pipeline directory (containing images/)")
    parser.add_argument("--index", type=int, default=None, help="Index of image to use (0-based). If omitted, will prompt.")
    parser.add_argument("--text", type=str, default=None, help="Text to place on the cover. If omitted, will prompt.")
    parser.add_argument("--font", type=str, default=None, help="Path to a .ttf/.otf font to use.")
    parser.add_argument("--position", choices=["top", "middle", "bottom"], default="bottom", help="Vertical position of the text box.")
    parser.add_argument("--opacity", type=int, default=140, help="Opacity of background box (0-255, default 140).")
    parser.add_argument("--margin", type=float, default=None, help="Backward-compatible: sets both --padding and --edge to this value.")
    parser.add_argument("--padding", type=float, default=0.05, help="Inner padding around text inside the box (0-0.5, default 0.05).")
    parser.add_argument("--edge", type=float, default=0.05, help="Outer margin of the box from image edges (0-0.5, default 0.05).")
    parser.add_argument("--radius", type=int, default=None, help="Corner radius in pixels (default: auto-calculated).")
    parser.add_argument(
        "--stroke-color",
        type=str,
        default=None,
        help=f"Stroke color for text outline (choices: {', '.join(sorted(COLOR_MAP.keys()))}). Default: no stroke.",
    )
    parser.add_argument("--output", type=str, default="cover.jpg", help="Output filename (default cover.webp)")

    args = parser.parse_args()

    pipeline_dir = os.path.abspath(args.pipeline_dir)
    images_dir = os.path.join(pipeline_dir, "images")
    try:
        images = list_images(images_dir)
    except Exception as e:
        print(f"Error: {e}")
        return 1

    if not images:
        print(f"No images found in {images_dir}")
        return 1

    index = args.index if args.index is not None else choose_interactively(images)
    if index < 0 or index >= len(images):
        print(f"Index out of range: {index}")
        return 1

    selected = images[index]
    text = args.text
    if text is None:
        text = input("Enter text for the cover: ").strip()
    if not text:
        print("No text provided. Aborting.")
        return 1

    try:
        with Image.open(selected) as im:
            # Resolve margins with backward compatibility
            if args.margin is not None:
                padding_ratio = max(0.0, min(0.5, float(args.margin)))
                edge_margin_ratio = padding_ratio
            else:
                padding_ratio = max(0.0, min(0.5, float(args.padding)))
                edge_margin_ratio = max(0.0, min(0.5, float(args.edge)))

            # Parse stroke color if provided, or choose interactively
            stroke_color_arg = args.stroke_color
            if stroke_color_arg:
                try:
                    stroke_color = parse_color_name(stroke_color_arg)
                    stroke_width = STROKE_WIDTH
                except ValueError as e:
                    print(f"Error: {e}")
                    return 1
            else:
                # Interactive color selection
                chosen_color = choose_color_interactively()
                if chosen_color:
                    stroke_color = parse_color_name(chosen_color)
                    stroke_width = STROKE_WIDTH
                else:
                    stroke_color = (0, 0, 0, 255)
                    stroke_width = 0

            result = add_text_overlay(
                im,
                text=text,
                font_path=args.font,
                opacity=max(0, min(255, int(args.opacity))),
                padding_ratio=padding_ratio,
                edge_margin_ratio=edge_margin_ratio,
                vertical_position=args.position,
                radius=args.radius,
                stroke_width=stroke_width,
                stroke_color=stroke_color,
            )
            out_path = os.path.join(pipeline_dir, args.output)
            result.save(out_path, format="JPEG", quality=95, method=6)
            print(f"Saved: {out_path}")
    except Exception as e:
        print(f"Failed to create cover: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())


