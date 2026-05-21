"""yt-dlp로 YouTube 채널 데이터를 가져오는 유틸."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

from yt_dlp import YoutubeDL

_CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")

# 각 영상에서 보존할 필드만 추려 응답을 가볍게 유지.
_VIDEO_KEEP_FIELDS = (
    "id",
    "title",
    "webpage_url",
    "duration",
    "upload_date",
    "timestamp",
    "view_count",
    "like_count",
    "comment_count",
    "channel",
    "channel_id",
    "uploader",
    "tags",
    "categories",
    "description",
    "thumbnail",
)


def _normalize_to_url(channel_url_or_id: str) -> str:
    s = channel_url_or_id.strip()
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if s.startswith("@"):
        return f"https://www.youtube.com/{s}"
    if _CHANNEL_ID_RE.match(s):
        return f"https://www.youtube.com/channel/{s}"
    return f"https://www.youtube.com/{s}"


def _to_videos_tab(url: str) -> str:
    tab_suffixes = ("/videos", "/shorts", "/streams", "/playlists", "/community", "/about")
    if any(t in url for t in tab_suffixes):
        return url
    if "watch?v=" in url or "/playlist?" in url:
        return url
    return url.rstrip("/") + "/videos"


def _fetch_video_detail(video_url: str) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=False) or {}
    except Exception as e:
        return {"webpage_url": video_url, "error": str(e)}
    return {k: info.get(k) for k in _VIDEO_KEEP_FIELDS}


def fetch_channel_dump(
    channel_url_or_id: str,
    video_limit: int = 50,
    max_workers: int = 8,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> dict:
    """채널 + 최신 영상 N개의 상세(view/like/comment 포함) dump를 dict로 반환.

    1) /videos 탭에서 flat 목록(영상 ID/URL)만 빠르게 수집 (extract_flat='in_playlist')
    2) 각 영상 페이지를 ThreadPool로 병렬 fetch해서 view/like/comment 등 채움

    on_progress(done, total) 콜백이 주어지면 각 영상 fetch 완료마다 호출된다.
    """
    url = _to_videos_tab(_normalize_to_url(channel_url_or_id))
    flat_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "playlistend": video_limit,
    }
    with YoutubeDL(flat_opts) as ydl:
        data = ydl.extract_info(url, download=False) or {}

    entries = data.get("entries") or []
    video_urls = [
        e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}"
        for e in entries
        if e.get("id") or e.get("url")
    ]

    if not video_urls:
        return data

    total = len(video_urls)
    if on_progress is None:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            details = list(ex.map(_fetch_video_detail, video_urls))
    else:
        # 원본 순서 유지하면서 완료 개수 콜백
        details = [None] * total
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_fetch_video_detail, u): i for i, u in enumerate(video_urls)}
            done = 0
            on_progress(0, total)
            for f in as_completed(futures):
                details[futures[f]] = f.result()
                done += 1
                on_progress(done, total)

    data["entries"] = details
    return data
