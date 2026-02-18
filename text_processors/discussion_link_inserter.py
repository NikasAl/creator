#!/usr/bin/env python3
"""
Insert per-segment start-time links under each section header in discussion.txt
by matching segment content to transcript.json word/segment timestamps.

Usage:
  python text_processors/discussion_link_inserter.py \
    --pipeline-dir pipeline_VideoDiscussion_Fedorov_24102025 \
    --video-url "https://rutube.ru/video/xxxx/" \
    --regenerate-html \
    --title "Наше право подкреплено чем надо"
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def normalize_text(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def pick_probe(segment_text: str) -> str:
    # Prefer the first sentence up to ~180 chars
    text = segment_text.strip()
    # Split by sentence enders
    m = re.search(r"([\s\S]{1,180}?)[\.!?]\s", text)
    if m:
        probe = m.group(1)
    else:
        probe = text[:180]
    # Keep it not too short
    if len(probe) < 40 and len(text) > 40:
        probe = text[:120]
    return probe


def find_start_seconds_by_substring(
    segment_text: str, tr_segments: List[Dict[str, Any]]
) -> Optional[float]:
    """Find approximate start time by locating a probe substring across transcript segments.

    Strategy: concatenate small rolling windows (3-6 segments) to search the probe;
    on match, return the 'start' of the first transcript segment in that window.
    """
    probe = normalize_text(pick_probe(segment_text))
    if not probe:
        return None

    window_sizes = [6, 5, 4, 3]

    # Pre-normalize segment texts
    normalized_texts = [normalize_text(seg.get("text", "")) for seg in tr_segments]

    for win in window_sizes:
        for i in range(0, len(tr_segments)):
            j = min(len(tr_segments), i + win)
            block = " ".join(normalized_texts[i:j])
            if not block:
                continue
            if probe and probe in block:
                # Return the start of the first segment in the window
                return float(tr_segments[i].get("start", 0))

    return None


def find_start_seconds(segment: Dict[str, Any], transcript: Dict[str, Any]) -> Optional[float]:
    seg_text = (segment.get("content") or "").strip()
    if not seg_text:
        return None
    tr_segments: List[Dict[str, Any]] = transcript.get("segments", [])
    if not tr_segments:
        return None

    # Try substring window search first
    t = find_start_seconds_by_substring(seg_text, tr_segments)
    if t is not None:
        return t

    # Fallback: try with shorter probe from first ~12 words
    words = re.findall(r"\w+[\w-]*", seg_text, flags=re.UNICODE)
    if words:
        short_probe = normalize_text(" ".join(words[:12]))
        if short_probe:
            t = find_start_seconds_by_substring(short_probe, tr_segments)
            if t is not None:
                return t

    return None


def build_t_link(video_url: str, seconds: float) -> str:
    sec = int(round(seconds))
    sep = '&' if ('?' in video_url) else '?'
    return f"{video_url}{sep}t={sec}"


def insert_links_into_discussion(
    discussion_path: Path,
    segments: List[Dict[str, Any]],
    seg_index_to_seconds: Dict[int, float],
    video_url: str,
) -> None:
    lines = discussion_path.read_text(encoding='utf-8').splitlines()

    # Map title to index for matching headers reliably
    title_to_index: Dict[str, int] = {}
    for seg in segments:
        title = seg.get("title") or f"Фрагмент {seg.get('index')}"
        title_to_index[title.strip()] = int(seg.get("index"))

    out_lines: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out_lines.append(line)

        m = re.match(r"^##\s+(.*)$", line.strip())
        if m:
            header_title = m.group(1).strip()
            seg_idx = title_to_index.get(header_title)
            if seg_idx is not None and seg_idx in seg_index_to_seconds:
                # Check idempotency: if next non-empty line already contains a link, skip
                j = i + 1
                already = False
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                if j < len(lines) and re.search(r"\]\(.*\bt=\d+\)", lines[j]):
                    already = True
                if not already:
                    url = build_t_link(video_url, seg_index_to_seconds[seg_idx])
                    out_lines.append("")
                    out_lines.append(f"[Смотреть об этом в источнике]({url})")
                    out_lines.append("")

        i += 1

    discussion_path.write_text("\n".join(out_lines) + "\n", encoding='utf-8')


def regenerate_html(discussion_path: Path, html_title: str) -> None:
    # Reuse existing converter script
    from subprocess import run
    run([
        "python", "text_processors/markdown_to_html.py",
        str(discussion_path),
        "-o", str(discussion_path.with_suffix('.html')),
        "--title", html_title or discussion_path.stem,
    ], check=False)


def main() -> int:
    p = argparse.ArgumentParser(description="Добавление ссылок на начало фрагментов в discussion.txt")
    p.add_argument("--pipeline-dir", required=True, help="Каталог пайплайна (где discussion.txt, transcript.json, segments.json)")
    p.add_argument("--video-url", required=True, help="URL оригинального видео (будет добавлен параметр t=seconds)")
    p.add_argument("--regenerate-html", action="store_true", help="Пересоздать discussion.html после изменений")
    p.add_argument("--title", default="", help="Заголовок HTML (если пересоздаём)")
    args = p.parse_args()

    base = Path(args.pipeline_dir)
    discussion_path = base / "discussion.txt"
    segments_path = base / "segments.json"
    transcript_path = base / "transcript.json"

    if not discussion_path.exists():
        print(f"❌ Не найден файл: {discussion_path}")
        return 1
    if not segments_path.exists():
        print(f"❌ Не найден файл: {segments_path}")
        return 1
    if not transcript_path.exists():
        print(f"❌ Не найден файл: {transcript_path}")
        return 1

    try:
        segments_data = json.loads(segments_path.read_text(encoding='utf-8'))
        segments: List[Dict[str, Any]] = segments_data.get("segments", [])
        transcript: Dict[str, Any] = json.loads(transcript_path.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"❌ Ошибка чтения JSON: {e}")
        return 1

    # Build index->start map
    index_to_seconds: Dict[int, float] = {}
    for seg in segments:
        idx = int(seg.get("index"))
        t = find_start_seconds(seg, transcript)
        if t is not None:
            index_to_seconds[idx] = t
        else:
            # silently skip if not found
            pass

    if not index_to_seconds:
        print("⚠️ Не удалось определить таймкоды ни для одного сегмента")
    else:
        print(f"✅ Найдены таймкоды для {len(index_to_seconds)} сегментов")

    insert_links_into_discussion(discussion_path, segments, index_to_seconds, args.video_url)
    print(f"✅ Ссылки добавлены: {discussion_path}")

    if args.regenerate_html:
        regenerate_html(discussion_path, args.title or "")
        print(f"✅ HTML обновлён: {discussion_path.with_suffix('.html')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


