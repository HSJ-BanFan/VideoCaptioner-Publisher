import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "skills" / "scripts" / "clip_video.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("clip_video", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_clip_command_uses_list_args_with_duration(tmp_path: Path) -> None:
    script = load_script()

    command = script.build_clip_command(
        ffmpeg="ffmpeg",
        input_path=tmp_path / "input video.mp4",
        start="00:01:23.000",
        end="00:02:45.000",
        output_path=tmp_path / "clip.mp4",
    )

    assert command == [
        "ffmpeg",
        "-ss",
        "00:01:23.000",
        "-i",
        str(tmp_path / "input video.mp4"),
        "-t",
        "00:01:22.000",
        "-c",
        "copy",
        "-y",
        str(tmp_path / "clip.mp4"),
    ]


def test_build_clip_command_rejects_invalid_time_range(tmp_path: Path) -> None:
    script = load_script()

    with pytest.raises(ValueError, match="start time must be before end time"):
        script.build_clip_command(
            ffmpeg="ffmpeg",
            input_path=tmp_path / "input.mp4",
            start="00:02:45.000",
            end="00:01:23.000",
            output_path=tmp_path / "clip.mp4",
        )


def test_clip_video_creates_output_directory_and_runs_ffmpeg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = load_script()
    input_path = tmp_path / "input.mp4"
    output_path = tmp_path / "clips" / "clip.mp4"
    input_path.write_bytes(b"video")
    run_mock = Mock(return_value=Mock(returncode=0, stderr=""))
    monkeypatch.setattr(script.subprocess, "run", run_mock)

    script.clip_video(input_path, "00:00:01.000", "00:00:03.500", output_path)

    assert output_path.parent.is_dir()
    run_mock.assert_called_once()
    assert run_mock.call_args.args[0][0] == "ffmpeg"
