import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "skills" / "scripts" / "analyze_subtitles.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("analyze_subtitles", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_analyze_srt_returns_structured_data(tmp_path: Path) -> None:
    script = load_script()
    source = tmp_path / "source.srt"
    source.write_text(
        """1
00:00:00,000 --> 00:00:02,000
First line

2
00:00:02,000 --> 00:00:05,000
Second line here

3
00:00:05,000 --> 00:00:08,000
Third example line
""",
        encoding="utf-8",
    )

    result = script.analyze_srt(source)

    assert result["total_duration"] == 8.0
    assert result["count"] == 3
    assert result["total_duration_fmt"] == "00:08"
    assert "First line" in result["text_content"]
    assert "Second line here" in result["text_content"]


def test_analyze_srt_handles_empty_file(tmp_path: Path) -> None:
    script = load_script()
    source = tmp_path / "empty.srt"
    source.write_text("", encoding="utf-8")

    result = script.analyze_srt(source)

    assert result["total_duration"] == 0
    assert result["count"] == 0
    assert result["text_content"] == ""


def test_analyze_srt_raises_on_missing_file(tmp_path: Path) -> None:
    script = load_script()
    missing = tmp_path / "nonexistent.srt"

    with pytest.raises(FileNotFoundError, match="Subtitle file not found"):
        script.analyze_srt(missing)
