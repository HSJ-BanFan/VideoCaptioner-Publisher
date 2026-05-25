import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "skills" / "scripts" / "batch_extract_subtitle_clips.py"


def load_script() -> ModuleType:
    sys.path.insert(0, str(SCRIPT_PATH.parent))
    spec = importlib.util.spec_from_file_location("batch_extract_subtitle_clips", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_batch_extract_uses_manifest_directories_and_master_subtitle(tmp_path: Path) -> None:
    script = load_script()
    source = tmp_path / "master_zh.srt"
    manifest = tmp_path / "manifest.json"
    output_root = tmp_path / "cut"
    source.write_text(
        """1
00:00:00,160 --> 00:00:02,550
开头字幕

2
00:00:02,560 --> 00:00:06,230
第二句

3
00:01:46,000 --> 00:01:48,000
第二章开头
""",
        encoding="utf-8",
    )
    manifest.write_text(
        json.dumps(
            [
                {
                    "index": 1,
                    "title": "Intro",
                    "start": "00:00:00.000",
                    "end": "00:01:46.000",
                    "directory": "clips_all_22/01_Intro",
                },
                {
                    "index": 2,
                    "title": "Quiz",
                    "start": "00:01:46.000",
                    "end": "00:02:00.000",
                    "directory": "clips_all_22/02_Quiz",
                },
            ]
        ),
        encoding="utf-8",
    )

    results = script.batch_extract_srt_clips(
        source,
        manifest,
        output_root,
        "clip_zh_from_full.srt",
    )

    assert [result.count for result in results] == [2, 1]
    first_clip = output_root / "01_Intro" / "clip_zh_from_full.srt"
    second_clip = output_root / "02_Quiz" / "clip_zh_from_full.srt"
    assert first_clip.read_text(encoding="utf-8").startswith(
        "1\n00:00:00,160 --> 00:00:02,550\n开头字幕"
    )
    assert "00:00:00,000 --> 00:00:02,000\n第二章开头" in second_clip.read_text(
        encoding="utf-8"
    )


def test_batch_extract_rejects_missing_manifest_fields(tmp_path: Path) -> None:
    script = load_script()
    source = tmp_path / "master.srt"
    manifest = tmp_path / "manifest.json"
    source.write_text("", encoding="utf-8")
    manifest.write_text(json.dumps([{"start": "00:00:00.000"}]), encoding="utf-8")

    with pytest.raises(ValueError, match="manifest item 1 missing fields"):
        script.batch_extract_srt_clips(source, manifest, tmp_path / "cut")


def test_batch_extract_rejects_invalid_manifest_timestamp(tmp_path: Path) -> None:
    script = load_script()
    source = tmp_path / "master.srt"
    manifest = tmp_path / "manifest.json"
    source.write_text("", encoding="utf-8")
    manifest.write_text(
        json.dumps(
            [
                {
                    "index": 1,
                    "title": "Intro",
                    "start": "bad-time",
                    "end": "00:01:46.000",
                    "directory": "clips/01_Intro",
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="manifest item 1 has invalid timestamp"):
        script.batch_extract_srt_clips(source, manifest, tmp_path / "cut")


def test_batch_extract_reports_chapter_context_on_extraction_failure(
    tmp_path: Path,
) -> None:
    script = load_script()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "index": 1,
                    "title": "Intro",
                    "start": "00:00:00.000",
                    "end": "00:01:46.000",
                    "directory": "clips/01_Intro",
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="failed processing manifest item 1 \\(Intro\\)"):
        script.batch_extract_srt_clips(tmp_path / "missing.srt", manifest, tmp_path / "cut")
