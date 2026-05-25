"""download command — download online video via yt-dlp."""

from argparse import Namespace
from pathlib import Path
from typing import Any

from videocaptioner.cli import exit_codes as EXIT
from videocaptioner.cli import output


def run(args: Namespace, config: dict) -> int:
    url = args.url
    out_dir = getattr(args, "output", None) or "."
    quiet = getattr(args, "quiet", False)
    download_format = getattr(args, "format", None) or "bestvideo+bestaudio/best"
    cookies_from_browser = getattr(args, "cookies_from_browser", None)

    try:
        import yt_dlp
    except ImportError:
        output.error("yt-dlp is not available")
        output.hint("Install the official package with: pip install videocaptioner")
        return EXIT.DEPENDENCY_MISSING

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    progress = None if quiet else output.ProgressLine(f"Downloading {url}").start()

    try:
        ydl_opts: dict[str, Any] = {
            "format": download_format,
            "outtmpl": f"{out_dir}/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": quiet,
            "no_warnings": quiet,
        }
        if cookies_from_browser:
            ydl_opts["cookiesfrombrowser"] = (cookies_from_browser, None, None, None)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
            ydl.download([url])

        if progress:
            progress.finish(f"Downloaded to {out_dir}/")
        return EXIT.SUCCESS

    except Exception as e:
        if progress:
            progress.fail(str(e))
        else:
            output.error(str(e))
        return EXIT.RUNTIME_ERROR
