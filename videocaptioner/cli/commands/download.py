"""download command — download online video via yt-dlp."""

import shutil
import subprocess
from argparse import Namespace
from pathlib import Path

from videocaptioner.cli import exit_codes as EXIT
from videocaptioner.cli import output


def run(args: Namespace, config: dict) -> int:
    url = args.url
    out_dir = getattr(args, "output", None) or "."
    quiet = getattr(args, "quiet", False)
    fmt = getattr(args, "format", None) or "bestvideo+bestaudio/best"

    if not shutil.which("yt-dlp"):
        output.error("yt-dlp not found on PATH")
        output.hint("Install: pip install yt-dlp")
        return EXIT.DEPENDENCY_MISSING

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    progress = None if quiet else output.ProgressLine(f"Downloading {url}").start()

    try:
        cmd = [
            "yt-dlp",
            "-f", fmt,
            "-o", f"{out_dir}/%(title)s.%(ext)s",
            "--no-playlist",
        ]
        cookies_from_browser = getattr(args, "cookies_from_browser", None)
        if cookies_from_browser:
            cmd.extend(["--cookies-from-browser", cookies_from_browser])
        if quiet:
            cmd.append("--quiet")
        cmd.append(url)

        result = subprocess.run(cmd, capture_output=quiet, text=True)

        if result.returncode != 0:
            if progress:
                progress.fail("Download failed")
            if result.stderr:
                output.error(result.stderr.strip())
            return EXIT.RUNTIME_ERROR

        if progress:
            progress.finish(f"Downloaded to {out_dir}/")
        return EXIT.SUCCESS

    except Exception as e:
        if progress:
            progress.fail(str(e))
        else:
            output.error(str(e))
        return EXIT.RUNTIME_ERROR
