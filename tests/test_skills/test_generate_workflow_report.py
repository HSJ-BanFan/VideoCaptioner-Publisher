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
