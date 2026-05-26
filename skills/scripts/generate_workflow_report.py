#!/usr/bin/env python3

import argparse
import json
import subprocess
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
class MediaMetadata:
    path: str
    size_bytes: int
    duration: float
    video_codec: str
    resolution: str
    frame_rate: str
    audio_codec: str
    sample_rate: str


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
    media: MediaMetadata | None = None


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
    if report.media is not None:
        metadata["media"] = asdict(report.media)
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
    ]
    if report.media is not None:
        lines.append(
            "- 媒体: "
            f"{report.media.video_codec} {report.media.resolution} {report.media.frame_rate}, "
            f"audio={report.media.audio_codec} {report.media.sample_rate}Hz, "
            f"size={report.media.size_bytes}"
        )
    lines.extend([
        "",
        "## 输出文件",
        "",
    ])
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


def _first_stream(data: dict[str, object], codec_type: str) -> dict[str, object]:
    streams = data.get("streams", [])
    if not isinstance(streams, list):
        return {}
    for stream in streams:
        if isinstance(stream, dict) and stream.get("codec_type") == codec_type:
            return stream
    return {}


def probe_media(path: Path) -> MediaMetadata:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")

    data = json.loads(result.stdout)
    video = _first_stream(data, "video")
    audio = _first_stream(data, "audio")
    format_info = data.get("format", {})
    try:
        duration = float(format_info.get("duration", 0)) if isinstance(format_info, dict) else 0.0
    except (ValueError, TypeError):
        duration = 0.0
    width = video.get("width", 0)
    height = video.get("height", 0)
    return MediaMetadata(
        path=str(path),
        size_bytes=path.stat().st_size,
        duration=duration,
        video_codec=str(video.get("codec_name", "")),
        resolution=f"{width}x{height}" if width and height else "",
        frame_rate=str(video.get("avg_frame_rate", "")),
        audio_codec=str(audio.get("codec_name", "")),
        sample_rate=str(audio.get("sample_rate", "")),
    )


def resolve_media(path: Path | None, degradations: tuple[str, ...]) -> tuple[MediaMetadata | None, tuple[str, ...]]:
    if path is None:
        return None, degradations
    try:
        return probe_media(path), degradations
    except Exception as exc:
        return None, (*degradations, f"media probe failed: {exc}")


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
    parser.add_argument("--probe-video", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    outputs = tuple(item.strip() for item in args.outputs.split(",") if item.strip())
    degradations = tuple(item.strip() for item in args.degradations.split(",") if item.strip())
    media, degradations = resolve_media(args.probe_video, degradations)
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
        media=media,
    )
    write_report(report, args.output_dir)
    print(args.output_dir)


if __name__ == "__main__":
    main()
