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


def _fetch_channel_base_meta(base_url: str) -> dict:
    """채널 base URL에서 채널 수준 메타데이터만 경량으로 가져온다.

    /videos 탭이 아닌 base URL 에서 추출해 총 조회수·@핸들·설명 등
    /videos 탭 flat 추출에서 누락될 수 있는 필드를 보충한다.
    playlistend=1 로 영상 목록 처리는 최소화.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "playlistend": 1,
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(base_url, download=False) or {}
        return {
            "view_count":             info.get("view_count"),
            "channel_follower_count": info.get("channel_follower_count"),
            "uploader_id":            info.get("uploader_id"),
            "description":            info.get("description"),
            "playlist_count":         info.get("playlist_count"),
            "channel_id":             info.get("channel_id") or info.get("id"),
            "channel":                info.get("channel") or info.get("uploader"),
        }
    except Exception:
        return {}


def fetch_channel_dump(
    channel_url_or_id: str,
    video_limit: int = 50,
    max_workers: int = 20,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> dict:
    """채널 + 최신 영상 N개의 상세(view/like/comment 포함) dump를 dict로 반환.

    1) /videos 탭에서 flat 목록(영상 ID/URL)만 빠르게 수집
    2) base 채널 URL 메타 fetch + 영상 상세 fetch 를 ThreadPool 에서 동시 실행
       (순차 → 병렬로 전환해 속도 개선)

    on_progress(done, total) 콜백이 주어지면 각 영상 fetch 완료마다 호출된다.
    """
    base_url = _normalize_to_url(channel_url_or_id)
    videos_url = _to_videos_tab(base_url)

    flat_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "playlistend": video_limit,
    }
    with YoutubeDL(flat_opts) as ydl:
        data = ydl.extract_info(videos_url, download=False) or {}

    entries = data.get("entries") or []
    video_urls = [
        e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}"
        for e in entries
        if e.get("id") or e.get("url")
    ]

    if not video_urls:
        return data

    total = len(video_urls)

    # base meta fetch 와 영상 상세 fetch 를 동일 ThreadPool 에서 동시 실행.
    # max_workers+1 : 메타 fetch 1개 + 영상 fetch max_workers 개 동시 처리.
    details: list = [None] * total
    with ThreadPoolExecutor(max_workers=max_workers + 1) as ex:
        meta_future = ex.submit(_fetch_channel_base_meta, base_url)
        video_futures = {
            ex.submit(_fetch_video_detail, u): i
            for i, u in enumerate(video_urls)
        }

        done = 0
        if on_progress is not None:
            on_progress(0, total)

        for f in as_completed(video_futures):
            details[video_futures[f]] = f.result()
            done += 1
            if on_progress is not None:
                on_progress(done, total)

        extra_meta = meta_future.result()

    # /videos 탭 flat 추출에 없던 필드만 보충 (기존 값 보호).
    # view_count·channel_follower_count 는 채널 base URL 값이 더 정확하므로 항상 덮어씀.
    _always_override = {"view_count", "channel_follower_count"}
    for k, v in extra_meta.items():
        if v is not None and (k in _always_override or data.get(k) is None):
            data[k] = v

    data["entries"] = details
    return data
