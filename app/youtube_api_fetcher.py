"""YouTube Data API v3로 채널 데이터를 가져오는 유틸.

yt_dlp_fetcher.fetch_channel_dump()와 동일한 반환 구조를 유지하므로
churn_predictor.compute_features_from_dump()를 그대로 재사용할 수 있다.
"""

from __future__ import annotations

import os
import re
from typing import Callable, Optional

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

_CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
_URL_CHANNEL_ID_RE = re.compile(r"youtube\.com/channel/(UC[\w-]{22})")
_URL_HANDLE_RE = re.compile(r"youtube\.com/@([\w.-]+)")
_URL_USER_RE = re.compile(r"youtube\.com/user/([\w.-]+)")
_ISO_DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def _parse_iso_duration(duration: str) -> int:
    """ISO 8601 duration (PT1H2M3S) → 초 단위 정수."""
    if not duration:
        return 0
    m = _ISO_DURATION_RE.match(duration)
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mins = int(m.group(2) or 0)
    secs = int(m.group(3) or 0)
    return h * 3600 + mins * 60 + secs


def _get_client():
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "YOUTUBE_API_KEY 환경변수가 없습니다. .env 파일을 확인하세요."
        )
    return build("youtube", "v3", developerKey=api_key)


def _resolve_channel_id(youtube, channel_url_or_id: str) -> str:
    """채널 URL / 핸들 / ID → channel_id (UC...)."""
    s = channel_url_or_id.strip()

    if _CHANNEL_ID_RE.match(s):
        return s

    m = _URL_CHANNEL_ID_RE.search(s)
    if m:
        return m.group(1)

    m = _URL_HANDLE_RE.search(s)
    if m:
        handle = "@" + m.group(1)
        resp = youtube.channels().list(forHandle=handle, part="id").execute()
        items = resp.get("items", [])
        if items:
            return items[0]["id"]

    if s.startswith("@"):
        resp = youtube.channels().list(forHandle=s, part="id").execute()
        items = resp.get("items", [])
        if items:
            return items[0]["id"]

    m = _URL_USER_RE.search(s)
    if m:
        resp = youtube.channels().list(forUsername=m.group(1), part="id").execute()
        items = resp.get("items", [])
        if items:
            return items[0]["id"]

    resp = youtube.search().list(q=s, type="channel", part="id", maxResults=1).execute()
    items = resp.get("items", [])
    if items:
        return items[0]["id"]["channelId"]

    raise ValueError(f"채널을 찾을 수 없습니다: {channel_url_or_id}")


def fetch_channel_dump(
    channel_url_or_id: str,
    video_limit: int = 50,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> dict:
    """YouTube Data API v3로 채널 dump를 반환.

    yt_dlp_fetcher.fetch_channel_dump()와 동일한 구조의 dict를 반환하므로
    compute_features_from_dump()에 바로 전달할 수 있다.
    """
    try:
        youtube = _get_client()
    except Exception as e:
        raise RuntimeError(str(e)) from e

    try:
        channel_id = _resolve_channel_id(youtube, channel_url_or_id)
    except HttpError as e:
        _raise_if_quota(e)
        raise ValueError(f"채널 조회 실패: {e}") from e

    try:
        ch_resp = youtube.channels().list(
            id=channel_id,
            part="snippet,statistics,contentDetails",
        ).execute()
    except HttpError as e:
        _raise_if_quota(e)
        raise

    ch_items = ch_resp.get("items", [])
    if not ch_items:
        raise ValueError(f"채널 정보를 가져올 수 없습니다: {channel_id}")

    ch = ch_items[0]
    snippet = ch.get("snippet", {})
    stats = ch.get("statistics", {})
    uploads_playlist = (
        ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", "")
    )

    dump: dict = {
        "channel_id":             channel_id,
        "channel":                snippet.get("title", ""),
        "title":                  snippet.get("title", ""),
        "channel_follower_count": _to_int(stats.get("subscriberCount")),
        "view_count":             _to_int(stats.get("viewCount")),
        "playlist_count":         _to_int(stats.get("videoCount")),
        "description":            snippet.get("description", ""),
        "uploader_id":            snippet.get("customUrl", ""),
    }

    # 업로드 플레이리스트에서 video_id 목록 수집
    video_ids: list[str] = []
    next_page_token = None
    while len(video_ids) < video_limit:
        remaining = min(video_limit - len(video_ids), 50)
        try:
            pl_kwargs: dict = dict(
                playlistId=uploads_playlist,
                part="contentDetails",
                maxResults=remaining,
            )
            if next_page_token:
                pl_kwargs["pageToken"] = next_page_token
            pl_resp = youtube.playlistItems().list(**pl_kwargs).execute()
        except HttpError as e:
            _raise_if_quota(e)
            break

        for item in pl_resp.get("items", []):
            vid_id = item.get("contentDetails", {}).get("videoId")
            if vid_id:
                video_ids.append(vid_id)

        next_page_token = pl_resp.get("nextPageToken")
        if not next_page_token:
            break

    total = len(video_ids)
    if on_progress is not None:
        on_progress(0, total)

    entries: list[dict] = []
    channel_title = snippet.get("title", "")

    for batch_start in range(0, total, 50):
        batch = video_ids[batch_start : batch_start + 50]
        try:
            v_resp = youtube.videos().list(
                id=",".join(batch),
                part="snippet,contentDetails,statistics",
            ).execute()
        except HttpError as e:
            _raise_if_quota(e)
            break

        for item in v_resp.get("items", []):
            v_snippet = item.get("snippet", {})
            v_stats = item.get("statistics", {})
            v_content = item.get("contentDetails", {})

            pub_at: str = v_snippet.get("publishedAt", "") or ""
            upload_date = pub_at[:10].replace("-", "") if pub_at else None

            thumbnails = v_snippet.get("thumbnails", {})
            thumb_url = (
                (thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default") or {})
                .get("url", "")
            )

            entries.append({
                "id":            item["id"],
                "title":         v_snippet.get("title", ""),
                "webpage_url":   f"https://www.youtube.com/watch?v={item['id']}",
                "duration":      _parse_iso_duration(v_content.get("duration", "")),
                "upload_date":   upload_date,
                "timestamp":     None,
                "view_count":    _to_int(v_stats.get("viewCount")),
                "like_count":    _to_int(v_stats.get("likeCount")),
                "comment_count": _to_int(v_stats.get("commentCount")),
                "channel":       channel_title,
                "channel_id":    channel_id,
                "uploader":      channel_title,
                "tags":          v_snippet.get("tags", []),
                "categories":    [],
                "description":   v_snippet.get("description", ""),
                "thumbnail":     thumb_url,
            })

        done = min(batch_start + 50, total)
        if on_progress is not None:
            on_progress(done, total)

    dump["entries"] = entries
    return dump


def _to_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _raise_if_quota(e: HttpError) -> None:
    _QUOTA_REASONS = {
        "quotaExceeded", "rateLimitExceeded",
        "dailyLimitExceeded", "userRateLimitExceeded",
    }
    try:
        reason = e.error_details[0].get("reason", "") if e.error_details else ""
    except Exception:
        reason = ""
    if e.status_code == 403 or reason in _QUOTA_REASONS:
        raise RuntimeError(
            f"YouTube API 할당량 초과 또는 접근 거부 ({reason or e.status_code}). "
            "yt-dlp로 전환합니다."
        ) from e
