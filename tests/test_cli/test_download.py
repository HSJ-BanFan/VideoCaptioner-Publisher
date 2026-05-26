import sys
from argparse import Namespace
from unittest.mock import MagicMock, Mock

from videocaptioner.cli import exit_codes as EXIT
from videocaptioner.cli.commands import download


def _mock_ytdl(monkeypatch):
    mock_ytdl = Mock()
    mock_instance = MagicMock()
    mock_instance.__enter__.return_value = mock_instance
    mock_ytdl.YoutubeDL.return_value = mock_instance
    monkeypatch.setitem(sys.modules, "yt_dlp", mock_ytdl)
    return mock_ytdl


def test_download_passes_cookies_from_browser_to_ytdlp(monkeypatch) -> None:
    mock_ytdl = _mock_ytdl(monkeypatch)

    result = download.run(
        Namespace(
            url="https://example.com/video",
            output="downloads",
            quiet=True,
            cookies_from_browser="firefox",
            format=None,
            proxy=None,
        ),
        {},
    )

    assert result == EXIT.SUCCESS
    ydl_opts = mock_ytdl.YoutubeDL.call_args[0][0]
    assert "cookiesfrombrowser" in ydl_opts
    assert ydl_opts["cookiesfrombrowser"][0] == "firefox"


def test_download_passes_custom_format_to_ytdlp(monkeypatch) -> None:
    mock_ytdl = _mock_ytdl(monkeypatch)

    result = download.run(
        Namespace(
            url="https://example.com/video",
            output="downloads",
            quiet=True,
            cookies_from_browser=None,
            format="18/best[height<=360]",
            proxy=None,
        ),
        {},
    )

    assert result == EXIT.SUCCESS
    ydl_opts = mock_ytdl.YoutubeDL.call_args[0][0]
    assert ydl_opts["format"] == "18/best[height<=360]"


def test_download_omits_cookies_and_proxy_when_not_set(monkeypatch) -> None:
    mock_ytdl = _mock_ytdl(monkeypatch)

    result = download.run(
        Namespace(
            url="https://example.com/video",
            output="downloads",
            quiet=True,
            cookies_from_browser=None,
            format=None,
            proxy=None,
        ),
        {},
    )

    assert result == EXIT.SUCCESS
    ydl_opts = mock_ytdl.YoutubeDL.call_args[0][0]
    assert "cookiesfrombrowser" not in ydl_opts
    assert "proxy" not in ydl_opts


def test_download_passes_proxy_to_ytdlp(monkeypatch) -> None:
    mock_ytdl = _mock_ytdl(monkeypatch)

    result = download.run(
        Namespace(
            url="https://example.com/video",
            output="downloads",
            quiet=True,
            cookies_from_browser=None,
            format=None,
            proxy="http://127.0.0.1:7897",
        ),
        {},
    )

    assert result == EXIT.SUCCESS
    ydl_opts = mock_ytdl.YoutubeDL.call_args[0][0]
    assert ydl_opts["proxy"] == "http://127.0.0.1:7897"


def test_download_hints_for_outdated_ytdlp(monkeypatch, capsys) -> None:
    mock_ytdl = _mock_ytdl(monkeypatch)
    mock_instance = mock_ytdl.YoutubeDL.return_value.__enter__.return_value
    mock_instance.download.side_effect = Exception("ERROR: yt-dlp is older than 90 days")

    result = download.run(
        Namespace(
            url="https://example.com/video",
            output="downloads",
            quiet=True,
            cookies_from_browser=None,
            format=None,
            proxy=None,
        ),
        {},
    )

    assert result == EXIT.RUNTIME_ERROR
    err = capsys.readouterr().err
    assert "Update yt-dlp: pip install -U yt-dlp" in err


def test_download_hints_for_youtube_bot_check(monkeypatch, capsys) -> None:
    mock_ytdl = _mock_ytdl(monkeypatch)
    mock_instance = mock_ytdl.YoutubeDL.return_value.__enter__.return_value
    mock_instance.download.side_effect = Exception("Sign in to confirm you are not a bot")

    result = download.run(
        Namespace(
            url="https://example.com/video",
            output="downloads",
            quiet=True,
            cookies_from_browser=None,
            format=None,
            proxy=None,
        ),
        {},
    )

    assert result == EXIT.RUNTIME_ERROR
    err = capsys.readouterr().err
    assert "YouTube bot-check: retry with --cookies-from-browser firefox" in err


def test_download_hints_for_youtube_429(monkeypatch, capsys) -> None:
    mock_ytdl = _mock_ytdl(monkeypatch)
    mock_instance = mock_ytdl.YoutubeDL.return_value.__enter__.return_value
    mock_instance.download.side_effect = Exception("HTTP Error 429: Too Many Requests")

    result = download.run(
        Namespace(
            url="https://example.com/video",
            output="downloads",
            quiet=True,
            cookies_from_browser=None,
            format=None,
            proxy=None,
        ),
        {},
    )

    assert result == EXIT.RUNTIME_ERROR
    err = capsys.readouterr().err
    assert "YouTube rate-limited the current exit IP" in err
