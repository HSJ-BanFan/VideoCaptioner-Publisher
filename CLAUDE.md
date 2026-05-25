# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Use `uv` for development tasks; `pyproject.toml` declares the package, dev dependencies, pytest settings, ruff, and pyright.

```bash
uv sync
uv run videocaptioner --help
uv run videocaptioner transcribe video.mp4 --asr bijian -o output.srt
uv run videocaptioner subtitle input.vtt --translator llm --target-language zh-Hans -o output.srt
uv run videocaptioner synthesize video.mp4 -s subtitle.srt --subtitle-mode hard -o output.mp4
uv run videocaptioner process video.mp4 --target-language zh-Hans -o ./output/
uv run videocaptioner download "https://youtube.com/watch?v=xxx" --cookies-from-browser firefox -f "18/best[height<=360]"
```

GUI development:

```bash
uv sync --extra gui
uv run videocaptioner
```

Quality checks:

```bash
uv run pyright
uv run ruff check .
uv run ruff check --select I --fix .
uv run pytest -q
uv run pytest tests/test_cli/ -q
uv run pytest tests/test_cli/test_parser.py::TestDownloadParser::test_download_help_includes_cookies_from_browser -q
uv run pytest tests/test_skills --confcutdir=tests/test_skills -q
```

Build package:

```bash
uv build
```

On Windows in this worktree, the local virtualenv can also be used directly when needed:

```powershell
$env:PYTHONPATH=$PWD.Path
.venv\Scripts\python.exe -m pytest tests\test_skills --confcutdir=tests\test_skills -q
.venv\Scripts\python.exe -m videocaptioner.cli --help
```

## Architecture

VideoCaptioner is a Python CLI plus optional PyQt5/QFluentWidgets desktop app for:

```text
video/audio input → ASR → ASRData → subtitle split → LLM optimize → translate → subtitle file → video synthesis
```

Main layers:

- `videocaptioner/cli/main.py` builds the argparse CLI. Subcommands delegate into `videocaptioner/cli/commands/` (`transcribe`, `subtitle`, `synthesize`, `process`, `download`, `config`, `style`).
- `videocaptioner/cli/commands/process.py` orchestrates the CLI full pipeline by calling the transcribe, subtitle, and synthesize commands in sequence. URL input is intentionally downloaded first via `download`, then processed locally.
- `videocaptioner/core/entities.py` defines shared enums and task/config dataclasses used by CLI and GUI flows.
- `videocaptioner/core/asr/` contains ASR engines and chunk handling (`bijian`, `jianying`, `whisper-api`, `whisper-cpp`, Faster Whisper-related code, chunk merger).
- `videocaptioner/core/split/`, `videocaptioner/core/optimize/`, and `videocaptioner/core/translate/` implement subtitle segmentation, LLM optimization, and translator backends.
- `videocaptioner/core/subtitle/` renders subtitle styles, including ASS and rounded-background rendering. FFmpeg/libass support matters for hard subtitle synthesis.
- `videocaptioner/core/llm/` centralizes OpenAI-compatible LLM clients, context, checks, and request logging.
- `videocaptioner/core/tts/` contains TTS backends and data/status types.
- `videocaptioner/ui/` is the desktop app. `ui/task_factory.py` converts GUI settings into task dataclasses; `ui/thread/` runs background work; `ui/view/` and `ui/components/` implement screens and widgets.
- `videocaptioner/config.py` decides development vs installed paths. In source-tree development, `resource/`, `AppData/`, and `work-dir/` live under the repo; installed mode uses platform data directories and `~/VideoCaptioner`.

## Claude Code Skill

The repository includes a Claude Code skill under `skills/`. Install/update the project-local active copy with:

```bash
mkdir -p .claude/skills/videocaptioner
cp -r skills/* .claude/skills/videocaptioner/
```

For YouTube-clipper-style workflows, prefer full-subtitle-first processing:

```text
full VTT → subtitle segmentation → LLM optimization → LLM translation → full master SRT/VTT → manifest-based chapter subtitle extraction → video clipping/synthesis
```

Do not cut raw YouTube VTT into per-chapter VTT files before subtitle processing unless explicitly requested; YouTube VTT often contains incremental cues that degrade segmentation and translation quality.

## Tests

`pytest` is configured in `pyproject.toml` with verbose output and strict markers. Test groups mirror major modules (`tests/test_asr`, `tests/test_split`, `tests/test_translate`, `tests/test_subtitle`, `tests/test_thread`, `tests/test_cli`, `tests/test_skills`). Some tests require external services or heavy imports; use targeted test paths for focused changes.

For skill helper changes, run with `--confcutdir=tests/test_skills` to avoid unrelated root test setup.

## Fork Development Model

This repo is a **long-term fork** of `WEIFENG2333/VideoCaptioner`, not a temporary contributor branch. We maintain an independent product line and periodically absorb upstream patches.

### Branch Structure

| Branch | Role | Update Method |
|--------|------|---------------|
| `upstream/master` | Upstream reference (read-only) | `git fetch upstream` |
| `master` | Local sync anchor — tracks upstream only | `git merge --ff-only upstream/master` |
| `main` | Long-term custom development line | `git merge feature/*` or `git merge master` |
| `feature/*` | Individual development tasks | `git merge main` or `git rebase main` |

### Key Workflows

Sync upstream into our product line:
```bash
git switch master && git fetch upstream && git merge --ff-only upstream/master
git switch main && git merge master && git push origin main
```

Start a new feature:
```bash
git switch main && git switch -c feature/xxx
# develop...
git push -u origin feature/xxx
```

Merge completed feature:
```bash
git switch main && git merge --no-ff feature/xxx && git push origin main
```

### Rules

- Never develop directly on `master` — it is a pure sync anchor.
- Never force-push `master` or `main`.
- `master` uses `--ff-only` merge; `main` uses normal merge.
- Feature branches may rebase onto `main` only if single-developer.
- See `docs/fork-workflow.md` for full details.
