#!/usr/bin/env python3

import argparse
import re
from pathlib import Path

_ILLEGAL_FILENAME_CHARS_RE = re.compile(r'[/\\:*?"<>|]')


def sanitize_filename(name: str) -> str:
    cleaned = _ILLEGAL_FILENAME_CHARS_RE.sub('', name)
    cleaned = cleaned.replace(' ', '_')
    return cleaned[:100] if len(cleaned) > 100 else cleaned


def generate_summary(
    title: str,
    overview: str,
    keywords: list[str],
    time_range: str,
    video_title: str = "",
) -> str:
    keyword_str = "、".join(keywords) if keywords else ""
    video_context = f"（出自：{video_title}）" if video_title else ""

    sections = [
        f"# {title}",
        "",
        f"**时间范围**：{time_range}{video_context}",
        "",
        "## 核心内容",
        "",
        overview,
        "",
    ]

    if keyword_str:
        sections.extend([
            "## 关键词",
            "",
            keyword_str,
            "",
        ])

    sections.extend([
        "## 推荐平台",
        "",
        "- 小红书：知识干货/观点分享",
        "- 抖音：短视频切片（60s以内）",
        "- 微信视频号：深度观点",
        "- B站：完整章节",
        "",
    ])

    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate social media summary markdown.")
    parser.add_argument("--title", required=True, help="Chapter title")
    parser.add_argument("--overview", required=True, help="1-2 sentence overview")
    parser.add_argument("--keywords", default="", help="Comma-separated keywords")
    parser.add_argument("--time-range", required=True, help="Time range e.g. 03:15-06:30")
    parser.add_argument("--video-title", default="", help="Source video title")
    parser.add_argument("--output", required=True, help="Output markdown file path")
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    content = generate_summary(
        title=args.title,
        overview=args.overview,
        keywords=keywords,
        time_range=args.time_range,
        video_title=args.video_title,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
