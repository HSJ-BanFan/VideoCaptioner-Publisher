#!/usr/bin/env python3

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

_TIMESTAMP_RE = re.compile(r"^(?:(\d{2}):)?(\d{2}):(\d{2})([.,]\d{3})$")
_SRT_TIME_RE = re.compile(r"^(.+?)\s+-->\s+(.+?)$")


@dataclass(frozen=True)
class SubtitleBlock:
    start: float
    end: float
    text: str


def parse_timestamp(value: str) -> float:
    match = _TIMESTAMP_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"invalid timestamp: {value}")
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    millis = int(match.group(4)[1:])
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def format_srt_timestamp(seconds: float) -> str:
    millis_total = round(max(0.0, seconds) * 1000)
    hours, remainder = divmod(millis_total, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def parse_srt_blocks(content: str) -> list[SubtitleBlock]:
    blocks: list[SubtitleBlock] = []
    for raw_block in re.split(r"\n\s*\n", content.strip()):
        lines = [line.strip() for line in raw_block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        time_line = lines[1] if lines[0].isdigit() else lines[0]
        time_match = _SRT_TIME_RE.fullmatch(time_line)
        if time_match is None:
            continue
        text_start = 2 if lines[0].isdigit() else 1
        blocks.append(
            SubtitleBlock(
                start=parse_timestamp(time_match.group(1)),
                end=parse_timestamp(time_match.group(2)),
                text="\n".join(lines[text_start:]),
            )
        )
    return blocks


def extract_srt_clip(source_path: Path, start: str, end: str, output_path: Path) -> int:
    source_path = Path(source_path)
    output_path = Path(output_path)
    start_seconds = parse_timestamp(start)
    end_seconds = parse_timestamp(end)
    if start_seconds >= end_seconds:
        raise ValueError("start time must be before end time")
    if not source_path.is_file():
        raise FileNotFoundError(f"subtitle file not found: {source_path}")

    output_blocks: list[SubtitleBlock] = []
    for block in parse_srt_blocks(source_path.read_text(encoding="utf-8")):
        if block.start >= end_seconds or block.end <= start_seconds:
            continue
        output_blocks.append(
            SubtitleBlock(
                start=max(block.start, start_seconds) - start_seconds,
                end=min(block.end, end_seconds) - start_seconds,
                text=block.text,
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for index, block in enumerate(output_blocks, 1):
            file.write(f"{index}\n")
            file.write(
                f"{format_srt_timestamp(block.start)} --> {format_srt_timestamp(block.end)}\n"
            )
            file.write(f"{block.text}\n\n")
    return len(output_blocks)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract an SRT subtitle segment and reset timestamps."
    )
    parser.add_argument("source")
    parser.add_argument("start")
    parser.add_argument("end")
    parser.add_argument("output")
    args = parser.parse_args()

    count = extract_srt_clip(
        Path(args.source),
        args.start,
        args.end,
        Path(args.output),
    )
    print(f"{count} subtitles written to {args.output}")


if __name__ == "__main__":
    main()
