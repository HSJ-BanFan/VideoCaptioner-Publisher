#!/usr/bin/env python3

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class SubtitleSource:
    language: str
    kind: str
    format: str


@dataclass(frozen=True)
class LlmConfig:
    translator: str
    target_language: str
    reflect: bool
    layout: str


@dataclass(frozen=True)
class ClipMetadata:
    index: int
    title: str
    start: str
    end: str
    directory: str


@dataclass(frozen=True)
class WorkflowReport:
    url: str
    video_id: str
    title: str
    duration: float
    workflow: str
    subtitle_source: SubtitleSource
    llm: LlmConfig
    outputs: tuple[str, ...]
    clips: tuple[ClipMetadata, ...]
    degradations: tuple[str, ...]


def build_metadata(report: WorkflowReport) -> dict[str, object]:
    metadata: dict[str, object] = {
        "url": report.url,
        "video_id": report.video_id,
        "title": report.title,
        "duration": report.duration,
        "workflow": report.workflow,
        "subtitle_source": asdict(report.subtitle_source),
        "llm": asdict(report.llm),
        "outputs": list(report.outputs),
    }
    if report.clips:
        metadata["clips"] = [asdict(clip) for clip in report.clips]
    if report.degradations:
        metadata["degradations"] = list(report.degradations)
    return metadata


def build_summary(report: WorkflowReport) -> str:
    lines = [
        f"# {report.title}",
        "",
        f"- YouTube URL: {report.url}",
        f"- video_id: {report.video_id}",
        f"- 时长: {report.duration}",
        f"- 工作流: {report.workflow}",
        "- 字幕来源: "
        f"{report.subtitle_source.language} {report.subtitle_source.kind} {report.subtitle_source.format}",
        "- LLM: "
        f"{report.llm.translator}, {report.llm.target_language}, reflect={report.llm.reflect}, "
        f"layout={report.llm.layout}",
        "",
        "## 输出文件",
        "",
    ]
    lines.extend(f"- {output}" for output in report.outputs)
    lines.append("")

    if report.clips:
        lines.extend(["## 剪辑片段", ""])
        for clip in report.clips:
            lines.append(
                f"{clip.index}. {clip.title} — {clip.start} - {clip.end} — {clip.directory}"
            )
        lines.append("")

    if report.degradations:
        lines.extend(["## 异常和降级记录", ""])
        lines.extend(f"- {item}" for item in report.degradations)
        lines.append("")

    return "\n".join(lines)


def write_report(report: WorkflowReport, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.md").write_text(build_summary(report), encoding="utf-8")
    (output_dir / "metadata.json").write_text(
        json.dumps(build_metadata(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_clips(path: Path | None) -> tuple[ClipMetadata, ...]:
    if path is None:
        return ()
    data = json.loads(path.read_text(encoding="utf-8"))
    return tuple(ClipMetadata(**item) for item in data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate workflow summary.md and metadata.json.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--duration", required=True, type=float)
    parser.add_argument("--workflow", required=True, choices=("translate", "clip"))
    parser.add_argument("--subtitle-language", required=True)
    parser.add_argument("--subtitle-kind", required=True, choices=("manual", "auto", "asr"))
    parser.add_argument("--subtitle-format", required=True, choices=("vtt", "srt"))
    parser.add_argument("--target-language", default="zh-Hans")
    parser.add_argument("--layout", default="target-above")
    parser.add_argument("--outputs", required=True, help="Comma-separated output paths")
    parser.add_argument("--clips-json", type=Path)
    parser.add_argument("--degradations", default="", help="Comma-separated degradation notes")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    outputs = tuple(item.strip() for item in args.outputs.split(",") if item.strip())
    degradations = tuple(item.strip() for item in args.degradations.split(",") if item.strip())
    report = WorkflowReport(
        url=args.url,
        video_id=args.video_id,
        title=args.title,
        duration=args.duration,
        workflow=args.workflow,
        subtitle_source=SubtitleSource(
            language=args.subtitle_language,
            kind=args.subtitle_kind,
            format=args.subtitle_format,
        ),
        llm=LlmConfig(
            translator="llm",
            target_language=args.target_language,
            reflect=True,
            layout=args.layout,
        ),
        outputs=outputs,
        clips=parse_clips(args.clips_json),
        degradations=degradations,
    )
    write_report(report, args.output_dir)
    print(args.output_dir)


if __name__ == "__main__":
    main()
