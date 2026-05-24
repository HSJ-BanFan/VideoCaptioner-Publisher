from argparse import Namespace
from unittest.mock import Mock

from videocaptioner.cli import exit_codes as EXIT
from videocaptioner.cli.commands import download


def test_download_passes_cookies_from_browser_to_ytdlp(monkeypatch) -> None:
    run_mock = Mock(return_value=Mock(returncode=0, stderr=""))
    monkeypatch.setattr(download.shutil, "which", lambda _: "yt-dlp")
    monkeypatch.setattr(download.subprocess, "run", run_mock)

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
    command = run_mock.call_args.args[0]
    assert "--cookies-from-browser" in command
    assert command[command.index("--cookies-from-browser") + 1] == "firefox"


def test_download_passes_custom_format_to_ytdlp(monkeypatch) -> None:
    run_mock = Mock(return_value=Mock(returncode=0, stderr=""))
    monkeypatch.setattr(download.shutil, "which", lambda _: "yt-dlp")
    monkeypatch.setattr(download.subprocess, "run", run_mock)

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
    command = run_mock.call_args.args[0]
    assert command[command.index("-f") + 1] == "18/best[height<=360]"


def test_download_omits_cookies_flag_when_not_set(monkeypatch) -> None:
    run_mock = Mock(return_value=Mock(returncode=0, stderr=""))
    monkeypatch.setattr(download.shutil, "which", lambda _: "yt-dlp")
    monkeypatch.setattr(download.subprocess, "run", run_mock)

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
    command = run_mock.call_args.args[0]
    assert "--cookies-from-browser" not in command
