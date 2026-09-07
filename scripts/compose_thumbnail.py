#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.thumbnail_typography import compose_refined_upper_left_thumbnail


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compose restrained upper-left typography over an existing cover image.",
    )
    parser.add_argument("--source", required=True, help="Text-free source cover image.")
    parser.add_argument("--output", required=True, help="Destination thumbnail path.")
    parser.add_argument("--text", required=True, help="One-line thumbnail phrase.")
    parser.add_argument("--font", default="", help="Optional explicit TrueType/OpenType font path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    metrics = compose_refined_upper_left_thumbnail(
        args.source,
        args.output,
        args.text,
        font_path=args.font or None,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "output": args.output,
                "font_path": str(metrics.font_path),
                "font_size": metrics.font_size,
                "letter_spacing": metrics.letter_spacing,
                "text_box": {
                    "left": metrics.text_left,
                    "top": metrics.text_top,
                    "width": metrics.text_width,
                    "height": metrics.text_height,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
