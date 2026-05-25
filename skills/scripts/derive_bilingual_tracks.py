#!/usr/bin/env python3

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

_TIMING_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}$"
)


@dataclass(frozen=True)
class Cue:
    index: str
    timing: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class DeriveResult:
    cue_count: int


def parse_srt(path: Path) -> list[Cue]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    cues: list[Cue] = []
    for block_number, block in enumerate(re.split(r"\n\s*\n", text), start=1):
        lines = [line.rstrip() for line in block.splitlines()]
        if len(lines) < 3 or not lines[0].isdigit() or not _TIMING_RE.match(lines[1]):
            msg = f"invalid SRT block {block_number}"
            raise ValueError(msg)
        cues.append(Cue(index=lines[0], timing=lines[1], lines=tuple(lines[2:])))
    return cues


def format_cues(cues: list[Cue]) -> str:
    blocks = []
    for number, cue in enumerate(cues, start=1):
        blocks.append("\n".join([str(number), cue.timing, *cue.lines]))
    return "\n\n".join(blocks) + ("\n\n" if blocks else "")


def derive_tracks(bilingual_path: Path, target_path: Path, source_path: Path) -> DeriveResult:
    bilingual_cues = parse_srt(bilingual_path)
    target_cues: list[Cue] = []
    source_cues: list[Cue] = []

    for cue in bilingual_cues:
        if len(cue.lines) < 2:
            msg = f"cue {cue.index} must contain target and source text"
            raise ValueError(msg)
        target_cues.append(Cue(index=cue.index, timing=cue.timing, lines=(cue.lines[0],)))
        source_cues.append(Cue(index=cue.index, timing=cue.timing, lines=tuple(cue.lines[1:])))

    target_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(format_cues(target_cues), encoding="utf-8")
    source_path.write_text(format_cues(source_cues), encoding="utf-8")
    return DeriveResult(cue_count=len(bilingual_cues))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Derive target-language and source-language SRT files from a target-above bilingual SRT."
    )
    parser.add_argument("bilingual", type=Path, help="Input bilingual SRT")
    parser.add_argument("target", type=Path, help="Output target-language SRT")
    parser.add_argument("source", type=Path, help="Output optimized source-language SRT")
    args = parser.parse_args()

    result = derive_tracks(args.bilingual, args.target, args.source)
    print(f"derived {result.cue_count} cues")


if __name__ == "__main__":
    main()
