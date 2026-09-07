from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


DEFAULT_FONT_CANDIDATES = (
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
)


@dataclass(frozen=True)
class ThumbnailTypographyMetrics:
    font_path: Path
    font_size: int
    letter_spacing: int
    text_left: int
    text_top: int
    text_width: int
    text_height: int


def resolve_thumbnail_font(font_path: str | Path | None = None) -> Path:
    if font_path:
        candidate = Path(font_path).expanduser().resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"Thumbnail font does not exist: {candidate}")
        return candidate

    for candidate in DEFAULT_FONT_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("No supported thumbnail font was found. Pass --font explicitly.")


def _tracked_text_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    letter_spacing: int,
) -> int:
    glyph_width = sum(float(draw.textlength(character, font=font)) for character in text)
    return round(glyph_width + (max(0, len(text) - 1) * letter_spacing))


def _draw_tracked_text(
    draw: ImageDraw.ImageDraw,
    *,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    letter_spacing: int,
    fill: tuple[int, int, int, int],
) -> None:
    x, y = position
    for character in text:
        draw.text((round(x), y), character, font=font, fill=fill)
        x += float(draw.textlength(character, font=font)) + letter_spacing


def compose_refined_upper_left_thumbnail(
    source_path: str | Path,
    output_path: str | Path,
    text: str,
    *,
    font_path: str | Path | None = None,
) -> ThumbnailTypographyMetrics:
    """Add restrained upper-left typography without changing the source photograph."""

    normalized_text = " ".join(text.strip().split())
    if not normalized_text:
        raise ValueError("Thumbnail text must not be empty.")
    if "\n" in text or "\r" in text:
        raise ValueError("The refined upper-left preset supports one line only.")

    source = Path(source_path).expanduser().resolve()
    destination = Path(output_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Thumbnail source image does not exist: {source}")

    resolved_font = resolve_thumbnail_font(font_path)
    with Image.open(source) as opened:
        base = opened.convert("RGBA")

    width, height = base.size
    if width < 320 or height < 180:
        raise ValueError("Thumbnail source must be at least 320x180.")

    measurement_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    measurement_draw = ImageDraw.Draw(measurement_layer)
    max_text_width = round(width * 0.38)
    font_size = max(20, round(height * 0.078))

    while True:
        font = ImageFont.truetype(str(resolved_font), font_size)
        letter_spacing = max(1, round(font_size * 0.11))
        text_width = _tracked_text_width(measurement_draw, normalized_text, font, letter_spacing)
        if text_width <= max_text_width or font_size <= 20:
            break
        font_size -= 1

    text_bbox = measurement_draw.textbbox((0, 0), normalized_text, font=font)
    text_height = text_bbox[3] - text_bbox[1]
    text_left = round(width * 0.04)
    text_top = round(height * 0.065)
    draw_y = text_top - text_bbox[1]

    # Keep the shadow perceptual rather than graphic: a tiny downward offset,
    # low opacity, and enough blur to avoid a duplicated-letter effect.
    shadow_offset = max(1, round(font_size * 0.025))
    shadow_blur = max(2, round(font_size * 0.045))
    shadow_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    _draw_tracked_text(
        ImageDraw.Draw(shadow_layer),
        position=(text_left, draw_y + shadow_offset),
        text=normalized_text,
        font=font,
        letter_spacing=letter_spacing,
        fill=(20, 17, 14, 48),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(shadow_blur))

    text_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    _draw_tracked_text(
        ImageDraw.Draw(text_layer),
        position=(text_left, draw_y),
        text=normalized_text,
        font=font,
        letter_spacing=letter_spacing,
        fill=(244, 239, 230, 255),
    )

    composed = Image.alpha_composite(Image.alpha_composite(base, shadow_layer), text_layer).convert("RGB")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.stem}.tmp{destination.suffix or '.png'}")
    image_format = Image.registered_extensions().get(destination.suffix.lower(), "PNG")
    composed.save(temporary, format=image_format, quality=95)
    temporary.replace(destination)

    return ThumbnailTypographyMetrics(
        font_path=resolved_font,
        font_size=font_size,
        letter_spacing=letter_spacing,
        text_left=text_left,
        text_top=text_top,
        text_width=text_width,
        text_height=text_height,
    )
