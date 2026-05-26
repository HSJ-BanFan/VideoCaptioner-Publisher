import importlib.util
import json
from pathlib import Path
from types import ModuleType

SCRIPT_PATH = Path(__file__).parents[2] / "skills" / "scripts" / "generate_workflow_report.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_workflow_report", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_translate_report_writes_summary_and_metadata(tmp_path: Path) -> None:
    script = load_script()
    output_dir = tmp_path / "outputs" / "abc123_demo"

    report = script.WorkflowReport(
        url="https://youtube.com/watch?v=abc123",
        video_id="abc123",
        title="Demo Video",
        duration=123.45,
        workflow="translate",
        subtitle_source=script.SubtitleSource(language="en", kind="manual", format="vtt"),
        llm=script.LlmConfig(
            translator="llm",
            target_language="zh-Hans",
            reflect=True,
            layout="target-above",
        ),
        outputs=(
            "subtitles/bilingual.srt",
            "subtitles/zh-Hans.srt",
            "subtitles/optimized_source.srt",
            "video/subtitled.mp4",
        ),
        clips=(),
        degradations=("used firefox cookies",),
        media=None,
    )

    script.write_report(report, output_dir)

    summary = (output_dir / "summary.md").read_text(encoding="utf-8")
    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    assert "# Demo Video" in summary
    assert "translate" in summary
    assert "manual vtt" in summary
    assert "video/subtitled.mp4" in summary
    assert metadata["url"] == "https://youtube.com/watch?v=abc123"
    assert metadata["subtitle_source"] == {
        "language": "en",
        "kind": "manual",
        "format": "vtt",
    }
    assert metadata["llm"]["reflect"] is True
    assert metadata["outputs"] == [
        "subtitles/bilingual.srt",
        "subtitles/zh-Hans.srt",
        "subtitles/optimized_source.srt",
        "video/subtitled.mp4",
    ]


def test_generate_clip_report_includes_clips(tmp_path: Path) -> None:
    script = load_script()
    output_dir = tmp_path / "outputs" / "abc123_demo"
    report = script.WorkflowReport(
        url="https://youtube.com/watch?v=abc123",
        video_id="abc123",
        title="Demo Video",
        duration=123.45,
        workflow="clip",
        subtitle_source=script.SubtitleSource(language="en", kind="auto", format="vtt"),
        llm=script.LlmConfig(
            translator="llm",
            target_language="zh-Hans",
            reflect=True,
            layout="target-above",
        ),
        outputs=("clips/manifest.json",),
        clips=(
            script.ClipMetadata(
                index=1,
                title="开场",
                start="00:00:00.000",
                end="00:01:30.000",
                directory="clips/01_intro",
            ),
        ),
        degradations=(),
        media=None,
    )

    script.write_report(report, output_dir)

    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    summary = (output_dir / "summary.md").read_text(encoding="utf-8")
    assert metadata["clips"] == [
        {
            "index": 1,
            "title": "开场",
            "start": "00:00:00.000",
            "end": "00:01:30.000",
            "directory": "clips/01_intro",
        }
    ]
    assert "## 剪辑片段" in summary
    assert "00:00:00.000 - 00:01:30.000" in summary


def test_build_metadata_includes_media_when_present() -> None:
    script = load_script()
    media = script.MediaMetadata(
        path="video/subtitled.mp4",
        size_bytes=123456,
        duration=1841.67,
        video_codec="h264",
        resolution="1280x720",
        frame_rate="30000/1001",
        audio_codec="opus",
        sample_rate="48000",
    )
    report = script.WorkflowReport(
        url="https://youtube.com/watch?v=abc123",
        video_id="abc123",
        title="Demo Video",
        duration=123.45,
        workflow="translate",
        subtitle_source=script.SubtitleSource(language="en", kind="manual", format="vtt"),
        llm=script.LlmConfig(translator="llm", target_language="zh-Hans", reflect=True, layout="target-above"),
        outputs=("video/subtitled.mp4",),
        clips=(),
        degradations=(),
        media=media,
    )

    metadata = script.build_metadata(report)

    assert metadata["media"] == {
        "path": "video/subtitled.mp4",
        "size_bytes": 123456,
        "duration": 1841.67,
        "video_codec": "h264",
        "resolution": "1280x720",
        "frame_rate": "30000/1001",
        "audio_codec": "opus",
        "sample_rate": "48000",
    }


def test_probe_media_returns_metadata(tmp_path: Path, monkeypatch) -> None:
    script = load_script()
    video = tmp_path / "subtitled.mp4"
    video.write_bytes(b"fake video")

    ffprobe_output = {
        "format": {"duration": "1841.67"},
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720, "avg_frame_rate": "30000/1001"},
            {"codec_type": "audio", "codec_name": "opus", "sample_rate": "48000"},
        ],
    }

    class Result:
        returncode = 0
        stdout = json.dumps(ffprobe_output)
        stderr = ""

    monkeypatch.setattr(script.subprocess, "run", lambda *_args, **_kwargs: Result())

    media = script.probe_media(video)

    assert media == script.MediaMetadata(
        path=str(video),
        size_bytes=len(b"fake video"),
        duration=1841.67,
        video_codec="h264",
        resolution="1280x720",
        frame_rate="30000/1001",
        audio_codec="opus",
        sample_rate="48000",
    )


def test_probe_media_failure_becomes_degradation(tmp_path: Path, monkeypatch) -> None:
    script = load_script()
    video = tmp_path / "subtitled.mp4"
    video.write_bytes(b"fake video")

    class Result:
        returncode = 1
        stdout = ""
        stderr = "ffprobe failed"

    monkeypatch.setattr(script.subprocess, "run", lambda *_args, **_kwargs: Result())

    media, degradations = script.resolve_media(video, ())

    assert media is None
    assert degradations == ("media probe failed: ffprobe failed",)
