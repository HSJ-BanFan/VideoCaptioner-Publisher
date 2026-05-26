---
name: videocaptioner
description: Process video subtitles and clips — download videos, transcribe speech, optimize/translate subtitles, extract semantic highlights, export video clips, and burn styled subtitles into video. Use when you need subtitles, transcription, translation, subtitle styling, online video download, or YouTube-clipper-style short video extraction.
allowed-tools:
  - Bash(videocaptioner *)
  - Bash(ffprobe *)
  - Bash(ffmpeg -ss *)
  - Bash(yt-dlp *)
  - Bash(python skills/scripts/*.py *)
  - Bash(python3 skills/scripts/*.py *)
---

# VideoCaptioner CLI

AI-powered video captioning and clipping: download video → transcribe speech → analyze subtitles → select highlight chapters → clip segments → translate subtitles → burn styled subtitles.

## When to use

- User wants to **clip highlights or topic segments from a video** (YouTube-clipper workflow)
- User wants to **download and subtitle online videos**
- User wants to **add subtitles to a video**
- User wants to **transcribe audio/video** to text
- User wants to **translate subtitles** to another language
- User wants to **customize subtitle appearance** (colors, fonts, rounded backgrounds)
- User wants to make **short bilingual clips** from a long video

## YouTube 视频智能处理专家 Role

Use this Role when the input is a YouTube URL and the user wants translation, subtitles, bilingual hard-subtitled video, chapter clipping, or YouTube-clipper-style output.

Role 只负责编排 VideoCaptioner commands and helper scripts，不重新定义字幕合并、拆分、时间轴算法；those remain inside `videocaptioner subtitle` and existing VideoCaptioner internals.

### Intent routing

If the user provides only a YouTube URL or says only "download", ask whether they want download-only output or translation/subtitle processing.

Translation triggers:

```text
翻译、字幕、双语、中文、zh-Hans、外语、看不懂、生成字幕、烧录字幕
```

Clipping triggers:

```text
剪辑、切片、裁剪、clip、shorts、提取片段、高光、章节
```

## Before you start

**Always run `videocaptioner <command> --help` first** to check the latest options and defaults before executing a command. The examples below are common patterns, but --help is the source of truth.

- Install: `pip install videocaptioner`
- FFmpeg required for clipping and video synthesis (`brew install ffmpeg` on macOS)
- **Free (no API key):** transcription (bijian/jianying), translation (Bing/Google)
- **Requires LLM API key:** subtitle optimization, subtitle re-segmentation, LLM translation. Set via `OPENAI_API_KEY` env var or `--api-key` flag
- Repo `skills/` directory is source of truth. Sync to `.claude/skills/videocaptioner/` only after implementation and tests pass so installed skill stays consistent.
- Skill helper scripts live in `skills/scripts/` in this repository. When installed to Claude Code, copy the whole `skills/` directory so all scripts remain available.

---

## YouTube-clipper-style workflow

Use this workflow when the user wants useful short clips from an online or local long video. This integrates the reference YouTube clipper skill pattern with VideoCaptioner's existing CLI instead of duplicating download, translation, and subtitle burning logic.

### Phase 1: Environment check

```bash
videocaptioner --help
videocaptioner download --help
videocaptioner transcribe --help
videocaptioner subtitle --help
videocaptioner synthesize --help
ffprobe -version
ffmpeg -version
```

If hard subtitles are requested, confirm FFmpeg has subtitle filter support:

```bash
ffmpeg -filters 2>&1 | grep subtitles
```

Look for `subtitles` filter in output. If missing, tell the user to install an FFmpeg build with libass support (`brew install ffmpeg-full` on macOS, `sudo apt install ffmpeg libass-dev` on Ubuntu).

### Phase 2: Get source video

For online video, use browser-cookie auto-detection by default. Supported browsers: firefox、chrome、edge. The `--cookies-from-browser` flag reuses the logged-in browser session to bypass age-gating and 403 errors.

```bash
# List available formats with cookies
yt-dlp --cookies-from-browser <browser> -F "VIDEO_URL"

# Download with auto-detected cookies
videocaptioner download "VIDEO_URL" --cookies-from-browser firefox

# Write available subtitles (manual + auto-generated)
yt-dlp --cookies-from-browser <browser> --write-subs --write-auto-subs --sub-langs "en-orig,en" --sub-format "vtt" --skip-download "VIDEO_URL"
```

If YouTube returns `HTTP Error 403: Forbidden`, retry with a lower-resolution format:

```bash
videocaptioner download "VIDEO_URL" --cookies-from-browser firefox -f "18/best[height<=360]"
```

If YouTube is blocked in the current network, set proxy env vars before running download:

```bash
# PowerShell
$env:HTTP_PROXY="http://127.0.0.1:7897"
$env:HTTPS_PROXY="http://127.0.0.1:7897"
$env:ALL_PROXY="http://127.0.0.1:7897"
videocaptioner download "VIDEO_URL" --cookies-from-browser firefox
```

If download quality or availability looks suspicious, use these recovery commands and checks:

```powershell
python -m pip install -U yt-dlp
videocaptioner download "VIDEO_URL" --cookies-from-browser firefox --proxy http://127.0.0.1:7897
videocaptioner download "VIDEO_URL" --cookies-from-browser firefox --proxy http://127.0.0.1:7897 -f "18/best[height<=360]"
```

- `HTTP Error 429` means current exit IP may be rate-limited by YouTube. Switch proxy node or retry later.
- `Sign in to confirm you're not a bot` means retry with browser cookies and switch proxy node or network exit.
- If video download keeps failing but subtitle tracks are still available, subtitle-only path can continue first and video synthesis can happen later.

For local video, use the provided file path. Then inspect media details:

```bash
ffprobe input.mp4
```

Report duration, video stream, audio stream, and any obvious format issues.

### YouTube subtitle source priority

Before processing subtitles, check which subtitle tracks are available and select the best source:

1. 原语言作者人工 VTT (author-uploaded, highest quality)
2. 原语言作者人工 SRT
3. 原语言 YouTube 自动 VTT (auto-generated, acceptable quality)
4. 原语言 YouTube 自动 SRT

If all tracks are missing (无字幕轨), 询问是否启用 ASR. There is no default ASR — the user must explicitly opt in.

### LLM config check before subtitle processing

Before running any LLM-dependent subtitle command (`--translator llm` or subtitle optimization), verify the LLM configuration:

```bash
videocaptioner config show
```

If the API key, base URL, or model is missing, set them:

```bash
videocaptioner config set llm.api_key <key>
videocaptioner config set llm.api_base <url>
videocaptioner config set llm.model <model-name>
```

Alternatively, set the environment variable in your shell:

```bash
# PowerShell
$env:OPENAI_API_KEY = "<key>"
# CMD
set OPENAI_API_KEY=<key>
# Bash
export OPENAI_API_KEY="<key>"
```

**Warning:** Never print or persist real API keys in output files, logs, or screenshots.

### Phase 3: Create full-video subtitles before clipping

For YouTube or any source with VTT captions, prefer the full VTT as the subtitle source. Do **not** cut raw YouTube VTT into chapter VTT files before subtitle processing; YouTube VTT often contains incremental cues and timing quirks that degrade downstream segmentation and translation.

Recommended high-quality order:

```text
full VTT
→ subtitle segmentation
→ LLM optimization
→ LLM translation
→ full high-quality SRT/VTT
→ chapter subtitle extraction
→ video clipping
→ subtitle synthesis
```

Download full VTT captions first when available:

```bash
yt-dlp --cookies-from-browser <browser> --write-subs --write-auto-subs --sub-langs "en-orig,en" --sub-format "vtt" --skip-download "VIDEO_URL"
```

Then run VideoCaptioner's high-quality subtitle pipeline on the full subtitle file:

```bash
videocaptioner subtitle raw_subtitle.vtt --translator llm --target-language zh-Hans --layout target-above --reflect -o subtitles/bilingual.srt
```

Derive separate mono-lingual tracks from the bilingual SRT:

```bash
python3 skills/scripts/derive_bilingual_tracks.py subtitles/bilingual.srt subtitles/zh-Hans.srt subtitles/optimized_source.srt
```

The bilingual SRT is the source of truth: line 1 is target Chinese, line 2+ is optimized source. The same workflow applies when the input is SRT instead of VTT.

If no usable VTT/SRT captions exist, transcribe the full video first:

```bash
videocaptioner transcribe input.mp4 --asr bijian -o input.srt
```

If the language is not supported by `bijian`/`jianying`, use a supported ASR engine shown by `videocaptioner transcribe --help`, such as `whisper-api` or `whisper-cpp`.

### Phase 4: Clipping analysis contract

Analyze video metadata plus original captions. Present chapter candidates in Chinese (or the user's preferred language). Default chaptering goal: 覆盖全片章节，尽量完整.

Output directory layout for each processed video:

```text
<video_id_sanitized_title>/
├── raw/                    — Original downloaded video and raw subtitles
├── subtitles/              — Processed subtitle files
│   ├── bilingual.srt       — Full-video bilingual subtitles (source of truth)
│   ├── zh-Hans.srt         — Chinese-only subtitle track
│   └── optimized_source.srt — Optimized source-language subtitle track
├── video/                  — Full processed video (if burned)
├── clips/                  — Per-chapter clip directories
│   └── <chapter_title>/
│       ├── clip.mp4        — Lossless-cut video clip
│       └── subtitled.mp4   — Hard-subtitled clip (if burned)
├── summary.md              — Workflow summary
└── metadata.json           — Video metadata and chapter definitions
```

First, run the analyze script to get structured subtitle data:

```bash
python3 skills/scripts/analyze_subtitles.py input.srt
```

This outputs JSON with `total_duration`, `count`, and `text_content` (timestamped, chunked for LLM reading). **Read and analyze this output:**

- Understand content semantics and topic transition points.
- Identify natural boundaries where topics shift.
- Propose chapters at **2-5 minute** granularity (avoid mechanical time-splitting).
- Ensure all content is covered with no gaps.

For each chapter, generate:

- **Title**: concise topic summary (10-20 chars recommended)
- **Time range**: start and end timestamps (format: `HH:MM:SS.mmm`)
- **Overview**: 1-2 sentences summarizing the segment (50-100 chars)
- **Keywords**: 3-5 core concept words

Present candidates clearly:

```text
1. [00:01:23.000 - 00:03:45.000] Main idea title
   Overview: What this segment says and why it stands alone.
   Keywords: keyword1, keyword2, keyword3

2. [00:08:10.000 - 00:10:40.000] Second clip title
   Overview: Another coherent topic or strong quote moment.
   Keywords: keyword1, keyword2, keyword3
```

Ask the user to confirm clip selections and processing options before executing any export commands (unless user already supplied exact timestamps):

- Which clips to export? (select by number, supports multi-select)
- Export original clip only?
- Extract matching subtitle clip?
- Translate subtitle clip? (target language?)
- Burn hard subtitles into video?
- Generate social media summary?

### Phase 5: Export selected clips

For each confirmed clip, create a dedicated output directory and run:

```bash
# 1. Lossless video clip
python3 skills/scripts/clip_video.py input.mp4 00:01:23.000 00:03:45.000 clips/Main_Idea/clip.mp4

# 2. One-off subtitle segments from full-video master subtitles, with timestamps reset to 00:00:00
python3 skills/scripts/extract_subtitle_clip.py input_bilingual.srt 00:01:23.000 00:03:45.000 clips/Main_Idea/clip_bilingual.srt
python3 skills/scripts/extract_subtitle_clip.py input_zh.srt 00:01:23.000 00:03:45.000 clips/Main_Idea/clip_zh.srt
```

For many chapters, write or reuse a `manifest.json` with `index`, `title`, `start`, `end`, and `directory`, then batch-cut subtitles from the full-video master SRT files:

```bash
python3 skills/scripts/batch_extract_subtitle_clips.py input_bilingual.srt clips/manifest.json clips --output-name clip_bilingual.srt
python3 skills/scripts/batch_extract_subtitle_clips.py input_zh.srt clips/manifest.json clips --output-name clip_zh.srt
```

If only original-language subtitles are needed, extract from the full processed original-language subtitle instead. Avoid extracting from raw YouTube VTT unless the user explicitly accepts lower subtitle quality.

For direct FFmpeg clipping without helper script:

```bash
ffmpeg -ss 00:01:23.000 -i input.mp4 -t 00:02:22.000 -c copy -y clips/Main_Idea/clip.mp4
```

Use `-t` duration after calculating `end - start`; avoid passing unvalidated timestamps from user text directly into shell commands.

### Phase 6: Default bilingual hard-subtitle burn-in

For each clip, burn the bilingual subtitle track into the video by default:

```bash
videocaptioner synthesize clips/Main_Idea/clip.mp4 -s clips/Main_Idea/clip_bilingual.srt --subtitle-mode hard --quality high -o clips/Main_Idea/subtitled.mp4
```

If ASS rendering hits GPU or CUDA issues, retry on CPU:

```powershell
videocaptioner synthesize video/source.mp4 -s subtitles/bilingual.srt --subtitle-mode hard --quality high --no-hwaccel -o video/subtitled.mp4
```

If the user prefers to keep the original clip without burned subtitles (e.g., for storage optimization or separate subtitle delivery), skip synthesize entirely and deliver `clip.mp4` plus external subtitle files.

For styled output, use `videocaptioner style` and `--style` / `--render-mode` / `--style-override` as needed.

### Phase 7: Optional social media summary

Generate a markdown summary for each clip:

```bash
python3 skills/scripts/generate_summary.py \
  --title "Main idea title" \
  --overview "What this segment says and why it stands alone." \
  --keywords "keyword1,keyword2,keyword3" \
  --time-range "00:01:23-00:03:45" \
  --video-title "Original Video Title" \
  --output clips/Main_Idea/summary.md
```

### Phase 8: Output report

Show the complete file tree per clip:

```text
Output directory: clips/Main_Idea/
├── clip.mp4              — Original clip (lossless cut)
├── clip_bilingual.srt    — Bilingual subtitles (timestamps reset)
├── clip_zh.srt           — Target-language subtitle segment
├── subtitled.mp4         — Hard-subtitled clip (if burned)
└── summary.md            — Social media summary (if generated)
```

Offer to continue with other selected clips or exit.

---

## Helper scripts

| Script | Purpose |
|--------|---------|
| `skills/scripts/clip_video.py` | Validate timestamps, calculate duration, and run `ffmpeg -ss ... -t ... -c copy` with list-style subprocess args |
| `skills/scripts/extract_subtitle_clip.py` | Extract overlapping SRT subtitles for a time range and reset clip timestamps to `00:00:00,000` |
| `skills/scripts/batch_extract_subtitle_clips.py` | Batch-cut a full processed SRT into chapter SRT files using a manifest with `index`, `title`, `start`, `end`, and `directory` |
| `skills/scripts/analyze_subtitles.py` | Parse SRT, output structured JSON with timestamped text chunks for AI semantic chapter analysis |
| `skills/scripts/generate_summary.py` | Generate markdown social media summary from chapter title, overview, keywords, and time range |
| `skills/scripts/derive_bilingual_tracks.py` | Split bilingual SRT into separate target-language and optimized source-language tracks |
| `skills/scripts/generate_workflow_report.py` | Generate a workflow report summarizing all processing steps and output files |

These scripts are intentionally small. VideoCaptioner already provides download, ASR, translation, style, and subtitle burn-in commands.

## Common scenarios

### 1. Give a Chinese video English subtitles (one command, all free)

```bash
videocaptioner process video.mp4 --asr bijian --translator bing --target-language en \
  --subtitle-mode hard --quality high -o output.mp4
```

### 2. Transcribe a video to SRT (free)

```bash
videocaptioner transcribe video.mp4 --asr bijian -o output.srt

# Output as JSON format to a directory
videocaptioner transcribe video.mp4 --asr bijian --format json -o ./subtitles/
```

### 3. Translate existing subtitles

```bash
# Free Bing → English, bilingual output with translation above original
videocaptioner subtitle input.srt --translator bing --target-language en --layout target-above -o translated.srt

# Free Google → Japanese, translation only (discard original text)
videocaptioner subtitle input.srt --translator google --target-language ja --no-optimize --layout target-only -o output_ja.srt

# High quality LLM translation with reflective mode
videocaptioner subtitle input.srt --translator llm --target-language en --reflect \
  --api-key $OPENAI_API_KEY -o output_en.srt
```

### 4. Full pipeline with beautiful styled subtitles

```bash
# Anime-style subtitles (warm color + orange outline), high quality video
videocaptioner process video.mp4 --asr bijian --translator bing --target-language ja \
  --subtitle-mode hard --style anime --quality high -o output_ja.mp4

# Modern rounded background subtitles
videocaptioner process video.mp4 --asr bijian --translator google --target-language ko \
  --subtitle-mode hard --render-mode rounded -o output_ko.mp4

# Custom colors: white text with red outline, ultra quality
videocaptioner process video.mp4 --asr bijian --translator bing --target-language en \
  --subtitle-mode hard --quality ultra \
  --style-override '{"outline_color": "#ff0000", "primary_color": "#ffffff"}' -o output_en.mp4
```

### 5. Subtitle only, output as ASS format (no video synthesis)

```bash
videocaptioner process video.mp4 --asr bijian --translator bing --target-language en \
  --format ass --no-synthesize -o ./output/
```

### 6. Step-by-step control (transcribe → translate → synthesize separately)

```bash
# Step 1: Transcribe
videocaptioner transcribe video.mp4 --asr bijian -o video.srt

# Step 2: Translate (bilingual, translation above original)
videocaptioner subtitle video.srt --translator bing --target-language en --layout target-above -o video_en.srt

# Step 3: Burn into video with rounded background, high quality
videocaptioner synthesize video.mp4 -s video_en.srt --subtitle-mode hard \
  --render-mode rounded --quality high -o video_with_subs.mp4
```

### 7. Process audio file (auto-skips video synthesis)

```bash
videocaptioner process podcast.mp3 --asr bijian --translator bing --target-language en -o ./output/
```

### 8. Transcribe other languages (whisper-api)

```bash
videocaptioner transcribe french_video.mp4 --asr whisper-api \
  --whisper-api-key $OPENAI_API_KEY --language fr -o french.srt
```

### 9. Only optimize subtitles with LLM (fix ASR errors, no translation)

```bash
videocaptioner subtitle raw_subtitle.srt --no-translate --api-key $OPENAI_API_KEY -o optimized.srt
```

### 10. Custom rounded background style with custom font

```bash
videocaptioner synthesize video.mp4 -s subtitle.srt --subtitle-mode hard \
  --style-override '{"text_color": "#ffffff", "bg_color": "#000000cc", "corner_radius": 10, "font_size": 36}' \
  --font-file ./NotoSansSC.ttf --quality high -o styled_video.mp4
```

### 11. Clip confirmed timestamps from a local video

```bash
python3 skills/scripts/clip_video.py video.mp4 00:05:00.000 00:07:30.000 clips/topic/clip.mp4
python3 skills/scripts/extract_subtitle_clip.py video_bilingual_master.srt 00:05:00.000 00:07:30.000 clips/topic/bilingual.srt
```

### 12. Create bilingual hard-subtitled short clips

```bash
videocaptioner subtitle video.vtt --translator llm --target-language zh-Hans --layout target-above --reflect -o video_bilingual_master.srt
python3 skills/scripts/extract_subtitle_clip.py video_bilingual_master.srt 00:05:00.000 00:07:30.000 clips/topic/bilingual.srt
videocaptioner synthesize clips/topic/clip.mp4 -s clips/topic/bilingual.srt --subtitle-mode hard --quality high -o clips/topic/subtitled.mp4
```

## Command reference

| Command | Purpose |
|---------|---------|
| `transcribe` | Speech → subtitles. Engines: `bijian`(free) `jianying`(free) `whisper-api` `whisper-cpp` |
| `subtitle` | Optimize (LLM) and/or translate (LLM/Bing/Google) subtitle files |
| `synthesize` | Burn subtitles into video with customizable styles |
| `process` | Full pipeline: transcribe → optimize → translate → synthesize |
| `download` | Download video from YouTube, Bilibili, etc. |
| `config` | Manage settings (`show` `set` `get` `path` `init`) |
| `style` | List all subtitle style presets with parameters |

Run `videocaptioner <command> --help` for full options.

## Subtitle styles

Two rendering modes for beautiful subtitles:

**ASS mode** (default) — outline/shadow style:
- Presets: `default` (white+black outline), `anime` (warm+orange outline), `vertical` (portrait videos)
- Customizable fields: `font_name`, `font_size`, `primary_color`, `outline_color`, `outline_width`, `bold`, `spacing`, `margin_bottom`

**Rounded mode** — modern rounded background boxes:
- Preset: `rounded` (dark text on semi-transparent background)
- Customizable fields: `font_name`, `font_size`, `text_color`, `bg_color` (#rrggbbaa), `corner_radius`, `padding_h`, `padding_v`, `margin_bottom`

Style options only work with `--subtitle-mode hard`.

## Target languages

BCP 47 codes: `zh-Hans` `zh-Hant` `en` `ja` `ko` `fr` `de` `es` `ru` `pt` `it` `ar` `th` `vi` `id` and 23 more.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | LLM API key |
| `OPENAI_BASE_URL` | LLM API base URL |

## Exit codes

`0` success · `2` bad arguments · `3` file not found · `4` missing dependency · `5` runtime error

## Tips

- Use `-q` for scripting (stdout = result path only)
- Bing/Google translation is free, no API key needed
- `bijian`/`jianying` ASR is free but only supports Chinese & English
- Run `videocaptioner style` to see all style presets
- For clipper workflows, always confirm semantic clip boundaries with the user before exporting unless exact timestamps were provided
- On macOS, `ffmpeg-full` is required for subtitle burning (`brew install ffmpeg-full`)
