import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "skills" / "scripts" / "derive_bilingual_tracks.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("derive_bilingual_tracks", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_derive_tracks_splits_target_and_source_lines(tmp_path: Path) -> None:
    script = load_script()
    bilingual = tmp_path / "bilingual.srt"
    target = tmp_path / "zh-Hans.srt"
    source = tmp_path / "optimized_source.srt"
    bilingual.write_text(
        """1
00:00:01,000 --> 00:00:03,000
你好，世界。
Hello world.

2
00:00:04,000 --> 00:00:06,000
这是自然中文。
This is natural Chinese.

""",
        encoding="utf-8",
    )

    result = script.derive_tracks(bilingual, target, source)

    assert result == script.DeriveResult(cue_count=2)
    assert target.read_text(encoding="utf-8") == """1
00:00:01,000 --> 00:00:03,000
你好，世界。

2
00:00:04,000 --> 00:00:06,000
这是自然中文。

"""
    assert source.read_text(encoding="utf-8") == """1
00:00:01,000 --> 00:00:03,000
Hello world.

2
00:00:04,000 --> 00:00:06,000
This is natural Chinese.

"""


def test_derive_tracks_keeps_extra_source_lines_together(tmp_path: Path) -> None:
    script = load_script()
    bilingual = tmp_path / "bilingual.srt"
    target = tmp_path / "zh-Hans.srt"
    source = tmp_path / "optimized_source.srt"
    bilingual.write_text(
        """1
00:00:01,000 --> 00:00:03,000
中文译文。
First source line.
Second source line.

""",
        encoding="utf-8",
    )

    script.derive_tracks(bilingual, target, source)

    assert source.read_text(encoding="utf-8") == """1
00:00:01,000 --> 00:00:03,000
First source line.
Second source line.

"""


def test_derive_tracks_rejects_cues_without_source_line(tmp_path: Path) -> None:
    script = load_script()
    bilingual = tmp_path / "bad.srt"
    bilingual.write_text(
        """1
00:00:01,000 --> 00:00:03,000
只有中文。

""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cue 1 must contain target and source text"):
        script.derive_tracks(
            bilingual,
            tmp_path / "zh-Hans.srt",
            tmp_path / "optimized_source.srt",
        )


def test_derive_tracks_rejects_invalid_srt_block(tmp_path: Path) -> None:
    script = load_script()
    bilingual = tmp_path / "bad.srt"
    bilingual.write_text("not an srt block", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid SRT block 1"):
        script.derive_tracks(
            bilingual,
            tmp_path / "zh-Hans.srt",
            tmp_path / "optimized_source.srt",
        )
