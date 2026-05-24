import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "skills" / "scripts" / "extract_subtitle_clip.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("extract_subtitle_clip", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extract_srt_clip_resets_timestamps_and_clips_boundaries(tmp_path: Path) -> None:
    script = load_script()
    source = tmp_path / "source.srt"
    output = tmp_path / "clip.srt"
    source.write_text(
        """1
00:04:59,500 --> 00:05:01,000
Opening overlap

2
00:05:02,000 --> 00:05:04,000
Inside clip

3
00:05:09,000 --> 00:05:12,000
Ending overlap

4
00:05:12,500 --> 00:05:13,000
Outside clip
""",
        encoding="utf-8",
    )

    count = script.extract_srt_clip(source, "00:05:00.000", "00:05:10.000", output)

    assert count == 3
    assert output.read_text(encoding="utf-8") == """1
00:00:00,000 --> 00:00:01,000
Opening overlap

2
00:00:02,000 --> 00:00:04,000
Inside clip

3
00:00:09,000 --> 00:00:10,000
Ending overlap

"""


def test_extract_srt_clip_rejects_invalid_timestamp(tmp_path: Path) -> None:
    script = load_script()
    source = tmp_path / "source.srt"
    source.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid timestamp"):
        script.extract_srt_clip(source, "5 minutes", "00:05:10.000", tmp_path / "clip.srt")
