from pathlib import Path

from PIL import Image, ImageChops

from app.utils.thumbnail_typography import compose_refined_upper_left_thumbnail


FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def test_refined_thumbnail_preserves_the_photo_outside_the_text_area(tmp_path) -> None:
    source = tmp_path / "cover.png"
    output = tmp_path / "thumbnail.png"
    Image.new("RGB", (1280, 720), (111, 132, 153)).save(source)

    metrics = compose_refined_upper_left_thumbnail(
        source,
        output,
        "INDIE POP",
        font_path=FONT_PATH,
    )

    with Image.open(source) as source_image, Image.open(output) as output_image:
        assert output_image.size == source_image.size
        untouched_source = source_image.crop((0, 220, 1280, 720))
        untouched_output = output_image.crop((0, 220, 1280, 720))
        assert ImageChops.difference(untouched_source, untouched_output).getbbox() is None

    assert metrics.text_width <= round(1280 * 0.38)
    assert metrics.font_size == round(720 * 0.078)
    assert metrics.letter_spacing == round(metrics.font_size * 0.11)


def test_refined_thumbnail_rejects_multiline_text(tmp_path) -> None:
    source = tmp_path / "cover.png"
    Image.new("RGB", (1280, 720), "white").save(source)

    try:
        compose_refined_upper_left_thumbnail(
            source,
            tmp_path / "thumbnail.png",
            "INDIE\nPOP",
            font_path=FONT_PATH,
        )
    except ValueError as exc:
        assert "one line" in str(exc)
    else:
        raise AssertionError("Expected multiline thumbnail text to be rejected")
