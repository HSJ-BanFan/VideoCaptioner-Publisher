from pathlib import Path

SKILL_PATH = Path(__file__).parents[2] / "skills" / "SKILL.md"


def read_skill() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_youtube_role_defaults_are_documented() -> None:
    content = read_skill()

    assert "YouTube 视频智能处理专家" in content
    assert "firefox、chrome、edge" in content
    assert "--cookies-from-browser <browser>" in content
    assert "--translator llm" in content
    assert "--target-language zh-Hans" in content
    assert "--layout target-above" in content
    assert "--reflect" in content
    assert "--subtitle-mode hard" in content


def test_subtitle_source_priority_is_documented() -> None:
    content = read_skill()

    expected_items = [
        "1. 原语言作者人工 VTT",
        "2. 原语言作者人工 SRT",
        "3. 原语言 YouTube 自动 VTT",
        "4. 原语言 YouTube 自动 SRT",
        "无字幕轨",
        "询问是否启用 ASR",
    ]
    for item in expected_items:
        assert item in content


def test_role_boundary_keeps_subtitle_algorithms_inside_videocaptioner() -> None:
    content = read_skill()

    assert "Role 只负责编排" in content
    assert "不重新定义字幕合并、拆分、时间轴算法" in content
    assert "videocaptioner subtitle" in content


def test_output_contract_is_documented() -> None:
    content = read_skill()

    expected_items = [
        "video_id_sanitized_title",
        "raw/",
        "subtitles/",
        "video/",
        "clips/",
        "summary.md",
        "metadata.json",
        "bilingual.srt",
        "zh-Hans.srt",
        "optimized_source.srt",
        "clip.mp4",
        "subtitled.mp4",
        "--subtitle-mode none",
    ]
    for item in expected_items:
        assert item in content


def test_llm_missing_config_guidance_is_documented() -> None:
    content = read_skill()

    expected_items = [
        "videocaptioner config show",
        "videocaptioner config set llm.api_key",
        "videocaptioner config set llm.api_base",
        "videocaptioner config set llm.model",
        "PowerShell",
        "CMD",
        "Bash",
        "OPENAI_API_KEY",
    ]
    for item in expected_items:
        assert item in content
