#!/usr/bin/env python3

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from extract_subtitle_clip import extract_srt_clip, parse_timestamp

_DEFAULT_OUTPUT_NAME = "clip_from_full.srt"
_REQUIRED_MANIFEST_FIELDS = {"index", "title", "start", "end", "directory"}


@dataclass(frozen=True)
class BatchExtractResult:
    index: int
    title: str
    start: str
    end: str
    output_path: Path
    count: int


def load_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    manifest_path = Path(manifest_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("manifest must be a JSON array")
    return data


def validate_manifest_item(item: object, position: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"manifest item {position} must be an object")
    missing = sorted(_REQUIRED_MANIFEST_FIELDS - item.keys())
    if missing:
        raise ValueError(f"manifest item {position} missing fields: {', '.join(missing)}")

    try:
        start_seconds = parse_timestamp(str(item["start"]))
        end_seconds = parse_timestamp(str(item["end"]))
    except ValueError as exc:
        raise ValueError(f"manifest item {position} has invalid timestamp: {exc}") from exc
    if start_seconds >= end_seconds:
        raise ValueError(f"manifest item {position} start must be before end")
    return item


def batch_extract_srt_clips(
    source_path: Path,
    manifest_path: Path,
    output_root: Path,
    output_name: str = _DEFAULT_OUTPUT_NAME,
) -> list[BatchExtractResult]:
    source_path = Path(source_path)
    output_root = Path(output_root)
    results: list[BatchExtractResult] = []

    for position, raw_item in enumerate(load_manifest(Path(manifest_path)), 1):
        item = validate_manifest_item(raw_item, position)
        chapter_dir = Path(str(item["directory"])).name
        output_path = output_root / chapter_dir / output_name
        try:
            count = extract_srt_clip(
                source_path,
                str(item["start"]),
                str(item["end"]),
                output_path,
            )
        except Exception as exc:
            raise RuntimeError(
                f"failed processing manifest item {position} ({item['title']}): {exc}"
            ) from exc
        results.append(
            BatchExtractResult(
                index=int(item["index"]),
                title=str(item["title"]),
                start=str(item["start"]),
                end=str(item["end"]),
                output_path=output_path,
                count=count,
            )
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch extract chapter SRT files from a full processed subtitle using a clips manifest."
    )
    parser.add_argument("source", help="Full processed SRT subtitle file")
    parser.add_argument("manifest", help="Manifest JSON with chapter start/end/directory fields")
    parser.add_argument("output_root", help="Directory where chapter subtitle folders are created")
    parser.add_argument(
        "--output-name",
        default=_DEFAULT_OUTPUT_NAME,
        help="Subtitle file name written under each chapter directory",
    )
    args = parser.parse_args()

    results = batch_extract_srt_clips(
        Path(args.source),
        Path(args.manifest),
        Path(args.output_root),
        args.output_name,
    )
    total = sum(result.count for result in results)
    for result in results:
        print(
            f"{result.index:02d} {result.count:4d} {result.start}-{result.end} {result.output_path}"
        )
    print(f"TOTAL {total} subtitles across {len(results)} clips")


if __name__ == "__main__":
    main()
