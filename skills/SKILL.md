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

## Before you start

**Always run `videocaptioner <command> --help` first** to check the latest options and defaults before executing a command. The examples below are common patterns, but --help is the source of truth.

- Install: `pip install videocaptioner`
- FFmpeg required for clipping and video synthesis (`brew install ffmpeg` on macOS)
- **Free (no API key):** transcription (bijian/jianying), translation (Bing/Google)
- **Requires LLM API key:** subtitle optimization, subtitle re-segmentation, LLM translation. Set via `OPENAI_API_KEY` env var or `--api-key` flag
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

For online video:

```bash
videocaptioner download "VIDEO_URL"
```

If YouTube returns `HTTP Error 403: Forbidden`, retry with browser cookies and, if needed, a safer format selector:

```bash
videocaptioner download "VIDEO_URL" --cookies-from-browser firefox
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

For long YouTube videos, avoid full best-quality download during exploration. Use `yt-dlp` directly to list formats or download a low-resolution sample/section through the proxy, then pass the local file to VideoCaptioner:

```bash
yt-dlp --proxy http://127.0.0.1:7897 -F "VIDEO_URL"
yt-dlp --proxy http://127.0.0.1:7897 -f "18/best[height<=360]" --no-playlist -o "clips/source.%(ext)s" "VIDEO_URL"
yt-dlp --proxy http://127.0.0.1:7897 -f "18/best[height<=360]" --download-sections "*00:00:00-00:05:00" -o "clips/sample.%(ext)s" "VIDEO_URL"
```

For local video, use the provided file path. Then inspect media details:

```bash
ffprobe input.mp4
```

Report duration, video stream, audio stream, and any obvious format issues.

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
yt-dlp --write-auto-subs --sub-langs "en-orig,en" --sub-format "vtt" --skip-download "VIDEO_URL"
```

Then run VideoCaptioner's complete subtitle pipeline on the full subtitle file before extracting chapter subtitles:

```bash
videocaptioner subtitle input.vtt --translator llm --target-language zh-Hans --layout source-above -o input_bilingual.srt
videocaptioner subtitle input.vtt --translator llm --target-language zh-Hans --layout target-only -o input_zh.srt
```

Use the resulting full-video SRT/VTT files as master subtitles for semantic analysis and chapter extraction.

If no usable VTT captions exist, transcribe the full video first:

```bash
videocaptioner transcribe input.mp4 --asr bijian -o input.srt
```

If the language is not supported by `bijian`/`jianying`, use a supported ASR engine shown by `videocaptioner transcribe --help`, such as `whisper-api` or `whisper-cpp`.

### Phase 4: Analyze transcript and propose semantic chapters

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

### Phase 6: Optional subtitle burn-in

Prefer burning chapter subtitles that were extracted from full-video master subtitles created in Phase 3. If translated output is needed, translate the full subtitle first, then extract per-chapter subtitle files.

Burn bilingual or Chinese subtitles into the video clip:

```bash
videocaptioner synthesize clips/Main_Idea/clip.mp4 -s clips/Main_Idea/clip_bilingual.srt --subtitle-mode hard --quality high -o clips/Main_Idea/clip_final_bilingual.mp4
videocaptioner synthesize clips/Main_Idea/clip.mp4 -s clips/Main_Idea/clip_zh.srt --subtitle-mode hard --quality high -o clips/Main_Idea/clip_final_zh.mp4
```

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
├── clip.srt              — Subtitle segment (timestamps reset)
├── clip_bilingual.srt    — Bilingual subtitles (if translated)
├── clip_final.mp4        — Hard-subtitled clip (if burned)
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

# Step 2: Translate (bilingual, original text above translation)
videocaptioner subtitle video.srt --translator bing --target-language en --layout source-above -o video_en.srt

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
python3 skills/scripts/clip_video.py video.mp4 00:05:00.000 00:07:30.000 clips/topic_clip.mp4
python3 skills/scripts/extract_subtitle_clip.py video_bilingual_master.srt 00:05:00.000 00:07:30.000 clips/topic_clip_bilingual.srt
```

### 12. Create bilingual hard-subtitled short clips

```bash
videocaptioner subtitle video.vtt --translator llm --target-language zh-Hans --layout source-above -o video_bilingual_master.srt
python3 skills/scripts/extract_subtitle_clip.py video_bilingual_master.srt 00:05:00.000 00:07:30.000 clips/topic_clip_bilingual.srt
videocaptioner synthesize clips/topic_clip.mp4 -s clips/topic_clip_bilingual.srt --subtitle-mode hard --quality high -o clips/topic_clip_final.mp4
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
