import pytest
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock

from videocaptioner.cli import exit_codes as EXIT
from videocaptioner.cli.commands import synthesize

def _args(video, subtitle, output, no_hwaccel=False):
    return Namespace(
        video=str(video),
        subtitle=str(subtitle),
        output=str(output) if output else None,
        quiet=True,
        verbose=False,
        style=None,
        style_override=None,
        render_mode=None,
        no_hwaccel=no_hwaccel
    )

def _config():
    return {
        "synthesize": {
            "subtitle_mode": "hard",
            "quality": "high",
            "render_mode": "ass",
            "style": "default",
            "layout": "target-above"
        }
    }

def test_synthesize_creates_output_parent_for_hard_subtitles(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_text("fake video")
    subtitle = tmp_path / "sub.srt"
    subtitle.write_text("fake sub")
    output = tmp_path / "nested" / "dir" / "out.mp4"

    args = _args(video, subtitle, output)
    config = _config()

    mock_render = MagicMock()
    monkeypatch.setattr("videocaptioner.core.subtitle.ass_renderer.render_ass_video", mock_render)
    # Also mock validate_video_input and ASRData.from_subtitle_file to avoid heavy logic
    monkeypatch.setattr("videocaptioner.cli.validators.validate_video_input", lambda x: None)
    monkeypatch.setattr("videocaptioner.core.asr.asr_data.ASRData.from_subtitle_file", lambda x: MagicMock())

    # We expect it to succeed now (after implementation)
    res = synthesize.run(args, config)

    assert res == EXIT.SUCCESS
    assert output.parent.exists()
    # Check if use_hwaccel was passed as True by default
    assert mock_render.call_args[1]["use_hwaccel"] is True

def test_synthesize_no_hwaccel_passes_false_to_ass_renderer(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_text("fake video")
    subtitle = tmp_path / "sub.srt"
    subtitle.write_text("fake sub")
    output = tmp_path / "out.mp4"

    args = _args(video, subtitle, output, no_hwaccel=True)
    config = _config()

    mock_render = MagicMock()
    monkeypatch.setattr("videocaptioner.core.subtitle.ass_renderer.render_ass_video", mock_render)
    monkeypatch.setattr("videocaptioner.cli.validators.validate_video_input", lambda x: None)
    monkeypatch.setattr("videocaptioner.core.asr.asr_data.ASRData.from_subtitle_file", lambda x: MagicMock())

    res = synthesize.run(args, config)

    assert res == EXIT.SUCCESS
    assert mock_render.call_args[1]["use_hwaccel"] is False

def test_synthesize_retries_ass_renderer_without_hwaccel_after_cuda_failure(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_text("fake video")
    subtitle = tmp_path / "sub.srt"
    subtitle.write_text("fake sub")
    output = tmp_path / "out.mp4"

    args = _args(video, subtitle, output)
    config = _config()

    mock_render = MagicMock()
    # First call fails with CUDA error, second succeeds
    mock_render.side_effect = [RuntimeError("FFmpeg CUDA hwaccel failed"), None]

    monkeypatch.setattr("videocaptioner.core.subtitle.ass_renderer.render_ass_video", mock_render)
    monkeypatch.setattr("videocaptioner.cli.validators.validate_video_input", lambda x: None)
    monkeypatch.setattr("videocaptioner.core.asr.asr_data.ASRData.from_subtitle_file", lambda x: MagicMock())

    res = synthesize.run(args, config)

    assert res == EXIT.SUCCESS
    assert mock_render.call_count == 2
    # Verify sequence of use_hwaccel
    assert mock_render.call_args_list[0][1]["use_hwaccel"] is True
    assert mock_render.call_args_list[1][1]["use_hwaccel"] is False
