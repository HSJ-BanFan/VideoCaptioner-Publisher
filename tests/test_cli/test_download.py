import sys
from argparse import Namespace
from unittest.mock import MagicMock, Mock

from videocaptioner.cli import exit_codes as EXIT
from videocaptioner.cli.commands import download


def test_download_passes_cookies_from_browser_to_ytdlp(monkeypatch) -> None:
    mock_ytdl = Mock()
    mock_ytdl_instance = MagicMock()
    mock_ytdl_instance.__enter__.return_value = mock_ytdl_instance
    mock_ytdl.YoutubeDL.return_value = mock_ytdl_instance
    monkeypatch.setitem(sys.modules, "yt_dlp", mock_ytdl)

    result = download.run(
        Namespace(
            url="https://example.com/video",
            output="downloads",
            quiet=True,
            cookies_from_browser="firefox",
        ),
        {},
    )

    assert result == EXIT.SUCCESS
    ydl_opts = mock_ytdl.YoutubeDL.call_args[0][0]
    assert "cookiesfrombrowser" in ydl_opts
    assert ydl_opts["cookiesfrombrowser"][0] == "firefox"


def test_download_passes_custom_format_to_ytdlp(monkeypatch) -> None:
    mock_ytdl = Mock()
    mock_ytdl_instance = MagicMock()
    mock_ytdl_instance.__enter__.return_value = mock_ytdl_instance
    mock_ytdl.YoutubeDL.return_value = mock_ytdl_instance
    monkeypatch.setitem(sys.modules, "yt_dlp", mock_ytdl)

    result = download.run(
        Namespace(
            url="https://example.com/video",
            output="downloads",
            quiet=True,
            cookies_from_browser=None,
            format="18/best[height<=360]",
        ),
        {},
    )

    assert result == EXIT.SUCCESS
    ydl_opts = mock_ytdl.YoutubeDL.call_args[0][0]
    assert ydl_opts["format"] == "18/best[height<=360]"


def test_download_omits_cookies_flag_when_not_set(monkeypatch) -> None:
    mock_ytdl = Mock()
    mock_ytdl_instance = MagicMock()
    mock_ytdl_instance.__enter__.return_value = mock_ytdl_instance
    mock_ytdl.YoutubeDL.return_value = mock_ytdl_instance
    monkeypatch.setitem(sys.modules, "yt_dlp", mock_ytdl)

    result = download.run(
        Namespace(
            url="https://example.com/video",
            output="downloads",
            quiet=True,
            cookies_from_browser=None,
            format=None,
        ),
        {},
    )

    assert result == EXIT.SUCCESS
    ydl_opts = mock_ytdl.YoutubeDL.call_args[0][0]
    assert "cookiesfrombrowser" not in ydl_opts
