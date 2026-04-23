from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import Settings
from app.models.playlist import Playlist


class CoverArtService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def _font(size: int) -> ImageFont.ImageFont:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except OSError:
            return ImageFont.load_default()

    def generate_cover(self, playlist: Playlist) -> str:
        meta = playlist.metadata_json or {}
        title = playlist.title
        prompt = meta.get("cover_prompt") or "AI music playlist"
        destination = self.settings.playlists_dir / f"{playlist.id}-cover.png"

        image = Image.new("RGB", (1280, 720), "#10141d")
        draw = ImageDraw.Draw(image)

        for y in range(720):
            ratio = y / 719
            red = int(16 + (244 - 16) * ratio)
            green = int(20 + (107 - 20) * ratio)
            blue = int(29 + (69 - 29) * ratio)
            draw.line([(0, y), (1280, y)], fill=(red, green, blue))

        draw.ellipse((30, 40, 430, 440), fill=(247, 198, 107, 35))
        draw.ellipse((860, -40, 1240, 340), fill=(255, 255, 255, 25))
        draw.rectangle((88, 88, 274, 102), fill="#f7c66b")

        title_font = self._font(56)
        body_font = self._font(24)
        small_font = self._font(18)

        draw.text((92, 124), "AI MUSIC PLAYLIST", font=small_font, fill="#f7c66b")
        draw.multiline_text((92, 178), title, font=title_font, fill="#f4efe7", spacing=10)
        draw.multiline_text((92, 340), prompt, font=body_font, fill="#efe5d8", spacing=8)
        draw.text((92, 654), f"Playlist ID: {playlist.id}", font=small_font, fill="#d0c4b4")
        draw.text((92, 682), "Generated from approved Suno queue", font=small_font, fill="#d0c4b4")

        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, format="PNG")
        return str(destination)
