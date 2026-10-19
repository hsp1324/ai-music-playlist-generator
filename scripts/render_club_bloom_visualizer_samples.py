#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path


FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


@dataclass(frozen=True)
class Concept:
    slug: str
    label: str
    grade: str
    details: str
    visualizer: str
    overlay: str


def drawtext(text: str, *, x: str, y: str, size: int, color: str, font: str = FONT_SANS) -> str:
    escaped = text.replace("'", r"\'").replace(":", r"\:")
    return (
        f"drawtext=fontfile='{font}':text='{escaped}':x={x}:y={y}:"
        f"fontsize={size}:fontcolor={color}:borderw=0"
    )


def concepts() -> list[Concept]:
    return [
        Concept(
            slug="01_vinyl_afterglow",
            label="VINYL AFTERGLOW",
            grade="eq=brightness=-0.035:contrast=1.08:saturation=0.90:gamma=0.98,colorbalance=rs=.035:gs=.012:bs=-.025",
            details=",".join(
                [
                    "drawbox=x=54:y=54:w=2:h=116:color=0xE7B26A@0.90:t=fill",
                    drawtext("CLUB BLOOM / SELECTS 001", x="78", y="58", size=15, color="0xF4DFC0@0.90"),
                    drawtext("CLOCK-OUT", x="78", y="87", size=36, color="0xFFF6E9", font=FONT_SERIF),
                    drawtext("CIPHER", x="78", y="126", size=36, color="0xFFF6E9", font=FONT_SERIF),
                    drawtext("KOREAN BOOM BAP  /  88 BPM", x="80", y="181", size=14, color="0xE7B26A"),
                    "drawbox=x=80:y=216:w=180:h=1:color=0xE7B26A@0.75:t=fill",
                    drawtext("SIDE A / VISUAL GROOVE", x="1040", y="674", size=12, color="0xF4DFC0@0.65"),
                ]
            ),
            visualizer=(
                "avectorscope=s=178x178:mode=polar:draw=line:scale=sqrt:"
                "rc=255:gc=255:bc=255:rf=1:gf=1:bf=1:af=8:zoom=1.25,"
                "format=rgba,colorkey=black:0.025:0.04,"
                "lutrgb=r=val*0.92:g=val*0.56:b=val*0.18,colorchannelmixer=aa=0.46[viz]"
            ),
            overlay="overlay=x=866:y=500:format=auto:shortest=1",
        ),
        Concept(
            slug="02_tape_window",
            label="TAPE WINDOW",
            grade="eq=brightness=-0.055:contrast=1.10:saturation=0.72:gamma=0.96,colorbalance=rs=.018:gs=.025:bs=-.018",
            details=",".join(
                [
                    "drawbox=x=54:y=522:w=594:h=132:color=0x0A0D0C@0.68:t=fill",
                    "drawbox=x=54:y=522:w=594:h=132:color=0xD9B77A@0.42:t=1",
                    "drawbox=x=74:y=546:w=554:h=68:color=0x050706@0.72:t=fill",
                    drawtext("A", x="77", y="628", size=16, color="0xD9B77A"),
                    drawtext("CLOCK-OUT CIPHER", x="105", y="627", size=15, color="0xF1E8D7"),
                    drawtext("88 BPM", x="544", y="627", size=14, color="0xD9B77A"),
                    drawtext("REC  ●", x="1126", y="62", size=14, color="0xE56C55"),
                    drawtext("AFTER WORK / TAPE 01", x="1010", y="88", size=13, color="0xF1E8D7@0.72"),
                ]
            ),
            visualizer=(
                "showfreqs=s=534x48:mode=line:ascale=cbrt:fscale=log:win_size=2048:"
                "averaging=5:colors=0xD9B77A|0xF1E8D7,format=rgba,"
                "colorkey=black:0.035:0.05,colorchannelmixer=aa=0.72[viz]"
            ),
            overlay="overlay=x=84:y=557:format=auto:shortest=1",
        ),
        Concept(
            slug="03_last_train_wave",
            label="LAST TRAIN WAVE",
            grade="eq=brightness=-0.065:contrast=1.07:saturation=0.68:gamma=0.94,colorbalance=rs=-.025:gs=.015:bs=.045",
            details=",".join(
                [
                    "drawbox=x=92:y=586:w=1096:h=1:color=0xBCE8DE@0.45:t=fill",
                    "drawbox=x=92:y=650:w=1096:h=1:color=0xBCE8DE@0.28:t=fill",
                    "drawbox=x=92:y=580:w=4:h=76:color=0xEAF8F4@0.85:t=fill",
                    "drawbox=x=1184:y=580:w=4:h=76:color=0xEAF8F4@0.85:t=fill",
                    drawtext("PLATFORM 08", x="94", y="535", size=13, color="0xBCE8DE"),
                    drawtext("CLOCK-OUT CIPHER", x="94", y="554", size=22, color="0xF2FBF8", font=FONT_SANS_BOLD),
                    drawtext("SEOUL / 00:08 — 00:38", x="1004", y="554", size=12, color="0xBCE8DE@0.80"),
                    "drawbox=x=310:y=647:w=5:h=5:color=0xEAF8F4@0.75:t=fill",
                    "drawbox=x=638:y=647:w=5:h=5:color=0xEAF8F4@0.75:t=fill",
                    "drawbox=x=966:y=647:w=5:h=5:color=0xEAF8F4@0.75:t=fill",
                ]
            ),
            visualizer=(
                "showwaves=s=1040x44:mode=p2p:colors=0xDDF7F0|0x78AFA5:"
                "scale=sqrt:draw=full:rate=30,format=rgba,colorkey=black:0.045:0.06,"
                "colorchannelmixer=aa=0.68[viz]"
            ),
            overlay="overlay=x=120:y=597:format=auto:shortest=1",
        ),
        Concept(
            slug="04_crate_notes",
            label="CRATE NOTES",
            grade="hue=s=0.32,eq=brightness=-0.025:contrast=1.16:gamma=1.01,colorbalance=rs=.025:gs=.006:bs=-.012",
            details=",".join(
                [
                    "drawbox=x=45:y=45:w=292:h=630:color=0x090909@0.40:t=fill",
                    "drawbox=x=71:y=69:w=1:h=582:color=white@0.35:t=fill",
                    drawtext("CB / ARCHIVE", x="92", y="70", size=13, color="white@0.72"),
                    drawtext("88", x="91", y="104", size=72, color="0xE7533F", font=FONT_SERIF),
                    drawtext("BEATS PER MINUTE", x="96", y="180", size=11, color="white@0.58"),
                    drawtext("CLOCK-OUT", x="94", y="232", size=25, color="white", font=FONT_SANS_BOLD),
                    drawtext("CIPHER", x="94", y="260", size=25, color="white", font=FONT_SANS_BOLD),
                    drawtext("DRY DRUMS", x="94", y="309", size=11, color="white@0.62"),
                    drawtext("WARM RHODES", x="94", y="327", size=11, color="white@0.62"),
                    drawtext("UPRIGHT BASS", x="94", y="345", size=11, color="white@0.62"),
                    drawtext("1999 — 2004", x="94", y="621", size=11, color="0xE7533F"),
                ]
            ),
            visualizer=(
                "showfreqs=s=205x210:mode=line:ascale=cbrt:fscale=log:win_size=2048:"
                "averaging=5:colors=0xF4F1EA|0xE7533F,format=rgba,"
                "colorkey=black:0.04:0.07,colorchannelmixer=aa=0.76[viz]"
            ),
            overlay="overlay=x=94:y=385:format=auto:shortest=1",
        ),
        Concept(
            slug="05_needles_and_dust",
            label="NEEDLES & DUST",
            grade="eq=brightness=-0.045:contrast=1.06:saturation=0.82:gamma=0.98,colorbalance=rs=.020:gs=.006:bs=.008",
            details=",".join(
                [
                    "drawbox=x=56:y=55:w=1168:h=1:color=0xF5EEE2@0.38:t=fill",
                    drawtext("NEEDLES & DUST", x="56", y="73", size=14, color="0xF5EEE2@0.90"),
                    drawtext("KOREAN BOOM BAP / 88", x="1012", y="73", size=12, color="0xF5EEE2@0.62"),
                    "drawbox=x=56:y=602:w=1168:h=66:color=0x080706@0.44:t=fill",
                    "drawbox=x=56:y=634:w=1168:h=1:color=0xF5EEE2@0.25:t=fill",
                    drawtext("CLOCK-OUT CIPHER", x="74", y="646", size=13, color="0xF5EEE2@0.86"),
                    drawtext("CLUB BLOOM", x="1110", y="646", size=12, color="0xD7A45E@0.92"),
                    drawtext("01", x="56", y="544", size=44, color="0xD7A45E@0.88", font=FONT_SERIF),
                    drawtext("A QUIET ROOM / A HEAVY POCKET", x="104", y="566", size=12, color="0xF5EEE2@0.67"),
                ]
            ),
            visualizer=(
                "showwaves=s=750x38:mode=p2p:colors=0xF5EEE2|0xD7A45E:"
                "scale=cbrt:draw=full:rate=30,format=rgba,colorkey=black:0.04:0.06,"
                "colorchannelmixer=aa=0.74[viz]"
            ),
            overlay="overlay=x=267:y=616:format=auto:shortest=1",
        ),
    ]


def render(
    *,
    image: Path,
    audio: Path,
    output_dir: Path,
    start: float,
    duration: float,
    concept_slug: str | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fade_out = max(duration - 0.65, 0)
    for concept in concepts():
        if concept_slug and concept.slug != concept_slug:
            continue
        output = output_dir / f"{concept.slug}.mp4"
        background = (
            "[0:v]scale=1344:756:force_original_aspect_ratio=increase,"
            "crop=1280:720:x=32:y=18,"
            f"{concept.grade},vignette=PI/5,{concept.details},"
            f"tpad=stop_mode=clone:stop_duration={duration:.2f},fps=30,"
            f"fade=t=in:st=0:d=0.45,fade=t=out:st={fade_out:.2f}:d=0.65,"
            "format=yuv420p[styled]"
        )
        filter_graph = (
            f"{background};"
            f"[1:a]asplit=2[aout][analysis];"
            f"[analysis]{concept.visualizer};"
            f"[styled][viz]{concept.overlay}[vout]"
        )
        command = [
            "nice",
            "-n",
            "15",
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(image),
            "-ss",
            str(start),
            "-t",
            str(duration),
            "-i",
            str(audio),
            "-filter_complex",
            filter_graph,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-t",
            str(duration),
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-threads",
            "1",
            str(output),
        ]
        print(f"Rendering {concept.label}: {output}", flush=True)
        subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start", type=float, default=8.0)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--concept", choices=[item.slug for item in concepts()])
    args = parser.parse_args()
    render(
        image=args.image,
        audio=args.audio,
        output_dir=args.output_dir,
        start=args.start,
        duration=args.duration,
        concept_slug=args.concept,
    )


if __name__ == "__main__":
    main()
