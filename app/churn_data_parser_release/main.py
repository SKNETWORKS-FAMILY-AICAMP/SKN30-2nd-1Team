"""
churn_data_parser - 채널 단건 메타데이터 + 댓글 수집기
채널 ID를 받아 채널 정보, 최근 영상 50개 메타데이터, 최근 10개 영상 댓글을 JSON으로 출력합니다.

시스템 요구사항:
  - Deno (https://deno.com) — 댓글 수집 시 필요. PATH에 설치되어 있어야 합니다.
  - --no-comments 사용 시 Deno 불필요

실행:
  uv run python main.py <channel_id>
  uv run python main.py UC0kp1x32b-Y4cvP5r3vW_hw
  uv run python main.py UC0kp1x32b-Y4cvP5r3vW_hw --output result.json
  uv run python main.py UC0kp1x32b-Y4cvP5r3vW_hw --no-comments
"""

import argparse
import json
import logging
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yt_dlp

MAX_VIDEOS = 50
COMMENT_VIDEOS = 10
LIVE_STATUSES = {"is_live", "is_upcoming", "post_live"}


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )
    return logging.getLogger(__name__)


def ensure_deno() -> None:
    if shutil.which("deno") is None:
        raise RuntimeError(
            "Deno가 설치되어 있지 않습니다. https://deno.com 에서 설치 후 PATH에 추가하세요."
        )


def is_live(entry: dict) -> bool:
    return entry.get("is_live") or entry.get("live_status") in LIVE_STATUSES


def fetch_channel_and_video_ids(channel_id: str, log: logging.Logger) -> tuple[dict, list[str]]:
    """채널 메타데이터와 영상 ID 목록(채널 노출 순서)을 반환한다."""
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": MAX_VIDEOS * 4,
        "ignoreerrors": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise RuntimeError(f"채널 정보를 가져올 수 없음: {channel_id}")

    title = info.get("uploader") or info.get("channel") or info.get("title") or ""

    channel_meta = {
        "channel_id": info.get("channel_id") or channel_id,
        "channel_title": title,
        "subscriber_count": info.get("channel_follower_count"),
        "description": info.get("description") or "",
    }

    video_ids: list[str] = []
    for entry in info.get("entries") or []:
        if entry is None:
            continue
        if is_live(entry):
            continue
        video_ids.append(entry["id"])
        if len(video_ids) >= MAX_VIDEOS:
            break

    return channel_meta, video_ids


def fetch_video_metadata(video_id: str) -> dict | None:
    """단일 영상 메타데이터를 반환한다. 라이브/예정 영상은 None."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(
            f"https://www.youtube.com/watch?v={video_id}", download=False
        )

    if not info or is_live(info):
        return None

    raw_date = info.get("upload_date") or ""
    published_at = (
        f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        if len(raw_date) == 8
        else raw_date
    )
    duration = info.get("duration") or 0

    return {
        "video_id": info.get("id", video_id),
        "video_title": info.get("title", ""),
        "published_at": published_at,
        "timestamp": info.get("timestamp"),
        "duration_sec": duration,
        "is_shorts": int(0 < duration <= 60),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
    }


def fetch_video_comments(video_id: str) -> list[dict]:
    """영상 댓글을 top 순서로 반환한다.
    정책: root comment만, 업로더 댓글 제외, 최대 60개 fetch (total=60, root=60, replies=0).
    subprocess + Deno 방식으로 실행."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--skip-download",
            "--write-info-json",
            "--write-comments",
            "--quiet",
            "--no-warnings",
            "--js-runtimes", "deno",
            "--extractor-args", "youtube:max_comments=60,60,0;comment_sort=top",
            "--output", str(tmp_path / "%(id)s.%(ext)s"),
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        info_file = tmp_path / f"{video_id}.info.json"
        if not info_file.exists():
            return []

        with open(info_file, encoding="utf-8-sig") as f:
            data = json.load(f)

    seen: set[str] = set()
    result = []
    for c in data.get("comments") or []:
        if c.get("parent", "root") != "root":
            continue
        if c.get("author_is_uploader", False):
            continue

        cid = c.get("id")
        if cid:
            if cid in seen:
                continue
            seen.add(cid)

        ts = c.get("timestamp")
        result.append({
            "id": cid or "",
            "text": c.get("text", ""),
            "author_id": c.get("author_id", ""),
            "like_count": c.get("like_count", 0),
            "timestamp": (
                datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                if ts else None
            ),
            "is_pinned": c.get("is_pinned", False),
            "is_favorited": c.get("is_favorited", False),
        })

    return result


def collect(channel_id: str, log: logging.Logger, include_comments: bool = True) -> dict:
    if include_comments:
        ensure_deno()
    log.info(f"수집 시작: {channel_id}")

    channel_meta, video_ids = fetch_channel_and_video_ids(channel_id, log)
    log.info(f"채널: {channel_meta['channel_title']} | 영상 {len(video_ids)}개")

    videos = []
    for i, vid_id in enumerate(video_ids, 1):
        log.info(f"  [{i}/{len(video_ids)}] 영상 메타데이터: {vid_id}")
        meta = fetch_video_metadata(vid_id)
        if meta is None:
            log.warning(f"  스킵 (라이브/예정): {vid_id}")
            continue

        video_number = len(videos) + 1
        meta["video_number"] = f"V{video_number:03d}"

        if include_comments and video_number <= COMMENT_VIDEOS:
            log.info(f"  [{i}/{len(video_ids)}] 댓글 수집: {vid_id}")
            meta["comments"] = fetch_video_comments(vid_id)
            log.info(f"    댓글 {len(meta['comments'])}개")
        else:
            meta["comments"] = []

        videos.append(meta)

    return {
        **channel_meta,
        "collected_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "videos": videos,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="채널 단건 메타데이터 + 댓글 수집기")
    parser.add_argument("channel_id", help="YouTube 채널 ID (UC...)")
    parser.add_argument("--output", "-o", help="출력 JSON 파일 경로 (기본: stdout)")
    parser.add_argument("--no-comments", action="store_true", help="댓글 수집 생략 (Deno 불필요)")
    args = parser.parse_args()

    log = setup_logging()

    try:
        result = collect(args.channel_id, log, include_comments=not args.no_comments)
    except Exception as e:
        log.error(f"수집 실패: {e}")
        sys.exit(1)

    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        log.info(f"저장 완료: {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
