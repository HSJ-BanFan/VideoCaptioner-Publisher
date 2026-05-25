import importlib.util
from pathlib import Path
from types import ModuleType

SCRIPT_PATH = Path(__file__).parents[2] / "skills" / "scripts" / "generate_summary.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_summary", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_summary_produces_markdown() -> None:
    script = load_script()

    content = script.generate_summary(
        title="Test Chapter",
        overview="This is a test overview.",
        keywords=["keyword1", "keyword2"],
        time_range="00:00-03:00",
        video_title="Original Video",
    )

    assert "# Test Chapter" in content
    assert "00:00-03:00" in content
    assert "（出自：Original Video）" in content
    assert "## 核心内容" in content
    assert "This is a test overview." in content
    assert "## 关键词" in content
    assert "keyword1、keyword2" in content
    assert "## 推荐平台" in content
    assert "小红书" in content
    assert "抖音" in content


def test_generate_summary_without_video_title() -> None:
    script = load_script()

    content = script.generate_summary(
        title="Solo Chapter",
        overview="Overview text.",
        keywords=[],
        time_range="01:00-02:00",
    )

    assert "（出自：" not in content
    assert "## 关键词" not in content


def test_sanitize_filename_removes_special_chars() -> None:
    script = load_script()

    result = script.sanitize_filename('Chapter: "Best" Part 1/2')
    assert ":" not in result
    assert '"' not in result
    assert "/" not in result
    assert " " not in result
