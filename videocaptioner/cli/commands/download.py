"""download command — download online video via yt-dlp."""

from argparse import Namespace
from pathlib import Path
from typing import Any

from videocaptioner.cli import exit_codes as EXIT
from videocaptioner.cli import output


def _emit_recovery_hints(error_text: str) -> None:
    """Print contextual hints based on known yt-dlp error patterns."""
    lower = error_text.lower()
    if "older than 90 days" in lower:
        output.hint("Update yt-dlp: pip install -U yt-dlp")
    if "sign in to confirm" in lower and "bot" in lower:
        output.hint("YouTube bot-check: retry with --cookies-from-browser firefox and switch proxy node/network exit")
    if "http error 429" in lower or "too many requests" in lower:
        output.hint("YouTube rate-limited the current exit IP; switch proxy node or retry later")


def run(args: Namespace, config: dict) -> int:
    url = args.url
    out_dir = getattr(args, "output", None) or "."
    quiet = getattr(args, "quiet", False)
    download_format = getattr(args, "format", None) or "bestvideo+bestaudio/best"
    cookies_from_browser = getattr(args, "cookies_from_browser", None)
    proxy = getattr(args, "proxy", None)

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
        if proxy:
            ydl_opts["proxy"] = proxy

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
            ydl.download([url])

        if progress:
            progress.finish(f"Downloaded to {out_dir}/")
        return EXIT.SUCCESS

    except Exception as e:
        msg = str(e)
        if progress:
            progress.fail(msg)
        else:
            output.error(msg)
        _emit_recovery_hints(msg)
        return EXIT.RUNTIME_ERROR
