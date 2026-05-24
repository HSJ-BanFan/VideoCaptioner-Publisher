#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path
from typing import Any

_TIMESTAMP_RE = re.compile(r"^(?:(\d{2}):)?(\d{2}):(\d{2})([.,]\d{3})$")
_SRT_TIME_RE = re.compile(r"^(.+?)\s+-->\s+(.+?)$")


def parse_timestamp(value: str) -> float:
    match = _TIMESTAMP_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"invalid timestamp: {value}")
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    millis = int(match.group(4)[1:])
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def format_timestamp_short(seconds: float) -> str:
    millis_total = round(max(0.0, seconds) * 1000)
    hours, remainder = divmod(millis_total, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, _ = divmod(remainder, 1000)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def analyze_srt(file_path: Path) -> dict[str, Any]:
    if not file_path.is_file():
        raise FileNotFoundError(f"Subtitle file not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    blocks: list[dict[str, Any]] = []

    for raw_block in re.split(r"\n\s*\n", content.strip()):
        lines = [line.strip() for line in raw_block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue

        time_line = lines[1] if lines[0].isdigit() else lines[0]
        time_match = _SRT_TIME_RE.fullmatch(time_line)
        if time_match is None:
            continue

        text_start = 2 if lines[0].isdigit() else 1
        start_sec = parse_timestamp(time_match.group(1))
        end_sec = parse_timestamp(time_match.group(2))
        text = " ".join(lines[text_start:])

        blocks.append({
            "start": start_sec,
            "end": end_sec,
            "start_fmt": format_timestamp_short(start_sec),
            "end_fmt": format_timestamp_short(end_sec),
            "text": text
        })

    if not blocks:
        return {"total_duration": 0, "count": 0, "text_content": ""}

    total_duration = blocks[-1]["end"]

    # Merge blocks into larger chunks for LLM reading (approx 30s per chunk)
    chunks: list[str] = []
    current_chunk: list[str] = []
    chunk_start = blocks[0]["start"]

    for block in blocks:
        current_chunk.append(block["text"])
        if block["end"] - chunk_start >= 30:
            chunks.append(f"[{format_timestamp_short(chunk_start)} - {block['end_fmt']}] {' '.join(current_chunk)}")
            current_chunk = []
            chunk_start = block["end"]

    if current_chunk:
        chunks.append(f"[{format_timestamp_short(chunk_start)} - {blocks[-1]['end_fmt']}] {' '.join(current_chunk)}")

    return {
        "total_duration": total_duration,
        "total_duration_fmt": format_timestamp_short(total_duration),
        "count": len(blocks),
        "text_content": "\n".join(chunks)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze SRT for AI semantic chapter generation.")
    parser.add_argument("input", help="Input SRT file path")
    args = parser.parse_args()

    result = analyze_srt(Path(args.input))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
