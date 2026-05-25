#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

_TIMESTAMP_RE = re.compile(r"^(?:(\d{2}):)?(\d{2}):(\d{2})([.,]\d{3})$")


def parse_timestamp(value: str) -> float:
    match = _TIMESTAMP_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"invalid timestamp: {value}")
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    millis = int(match.group(4)[1:])
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def format_timestamp(seconds: float) -> str:
    millis_total = round(seconds * 1000)
    hours, remainder = divmod(millis_total, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def build_clip_command(
    ffmpeg: str,
    input_path: Path,
    start: str,
    end: str,
    output_path: Path,
) -> list[str]:
    start_seconds = parse_timestamp(start)
    end_seconds = parse_timestamp(end)
    if start_seconds >= end_seconds:
        raise ValueError("start time must be before end time")

    return [
        ffmpeg,
        "-ss",
        format_timestamp(start_seconds),
        "-i",
        str(input_path),
        "-t",
        format_timestamp(end_seconds - start_seconds),
        "-c",
        "copy",
        "-y",
        str(output_path),
    ]


def clip_video(
    input_path: Path,
    start: str,
    end: str,
    output_path: Path,
    ffmpeg: str = "ffmpeg",
) -> Path:
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"input video not found: {input_path}")
    if shutil.which(ffmpeg) is None and Path(ffmpeg).name == ffmpeg:
        raise RuntimeError(f"ffmpeg executable not found: {ffmpeg}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_clip_command(ffmpeg, input_path, start, end, output_path)
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg clip failed")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a video segment with FFmpeg.")
    parser.add_argument("input")
    parser.add_argument("start")
    parser.add_argument("end")
    parser.add_argument("output")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()

    output = clip_video(
        Path(args.input),
        args.start,
        args.end,
        Path(args.output),
        ffmpeg=args.ffmpeg,
    )
    print(output)


if __name__ == "__main__":
    main()
