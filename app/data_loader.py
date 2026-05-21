"""대시보드용 CSV 로더 + 집계 함수.

스냅샷 데이터 기준 (data/raw/filtered_dataset_wide.csv)을 메인 소스로 사용한다.
이탈 임계값은 광고주 추천 톤에 맞춰 180일로 설정.
"""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, unquote, urlparse

import pandas as pd
import pymysql
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

WIDE_PATH = PROJECT_ROOT / "data" / "raw" / "filtered_dataset_wide.csv"
LONG_PATH = PROJECT_ROOT / "data" / "raw" / "filtered_dataset_long.csv"
MASTER_PATH = PROJECT_ROOT / "data" / "raw" / "youtube_channels_filtered.csv"
CHURN_PATH = PROJECT_ROOT / "data" / "raw" / "churn_probability_output.csv"

CHURN_THRESHOLD_DAYS = 180
A_THRESHOLD_DAYS = 30

# Channel_Filtering.pdf — 원본 전체 채널 수 (필터링 전).
# 8,192 → 1차 필터 → 3,766 → 제외 후보 제거 → 3,421 → wide 정제 → 3,336.
ORIGINAL_POOL_TOTAL = 8192

# 채널 조회 페이지 기본 예시 (wide+churn 풀 안의 C등급).
DEFAULT_EXAMPLE_CHANNEL_ID = "UCnwNkaw2j8SGcWBvjJcSNIg"  # 스튜디오 호락호락

GRADE_A_COLOR = "#10B981"
GRADE_B_COLOR = "#F59E0B"
GRADE_C_COLOR = "#EF4444"

CATEGORY_EMOJI = {
    "게임": "🎮", "엔터테인먼트": "🎬", "음악/댄스/가수": "🎵", "음악": "🎵",
    "국내/해외/여행": "✈️", "여행": "✈️", "푸드/요리": "🍳", "푸드": "🍳",
    "뷰티/패션": "💄", "뷰티": "💄", "키즈/어린이": "🧸", "키즈": "🧸",
    "스포츠/운동": "⚽", "교육/강의": "📚", "동물/펫": "🐾",
    "리뷰/언박싱": "📦", "테크": "🖥️", "자동차": "🚗",
    "TV/방송": "📺", "취미/라이프": "🎨",
}

CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
VIDEO_KEEP_FIELDS = (
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


@st.cache_data(show_spinner=False)
def load_wide() -> pd.DataFrame:
    return pd.read_csv(WIDE_PATH, encoding="utf-8-sig")


@st.cache_data(show_spinner=False)
def load_long() -> pd.DataFrame:
    df = pd.read_csv(LONG_PATH, encoding="utf-8-sig")
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def load_master() -> pd.DataFrame:
    return pd.read_csv(MASTER_PATH, encoding="utf-8-sig")


@st.cache_data(show_spinner=False)
def load_churn_probs() -> pd.DataFrame:
    return pd.read_csv(CHURN_PATH, encoding="utf-8-sig")


def _secret_or_env(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        return os.getenv(name, default)


def _db_config() -> dict:
    return {
        "host": _secret_or_env("DB_HOST", "127.0.0.1"),
        "port": int(_secret_or_env("DB_PORT", "3306") or "3306"),
        "user": _secret_or_env("DB_USER"),
        "password": _secret_or_env("DB_PASSWORD"),
        "database": _secret_or_env("DB_NAME", "youtube_model_db"),
        "charset": _secret_or_env("DB_CHARSET", "utf8mb4"),
        "cursorclass": pymysql.cursors.DictCursor,
        "connect_timeout": 3,
        "read_timeout": 5,
        "autocommit": True,
    }


def _lookup_candidates(raw_query: str) -> list[str]:
    query = raw_query.strip()
    if not query:
        return []

    candidates = [query]
    parsed = urlparse(query if re.match(r"^https?://", query) else f"https://{query}")
    path_parts = [unquote(part) for part in parsed.path.split("/") if part]
    qs = parse_qs(parsed.query)

    if "v" in qs:
        candidates.extend(qs["v"])

    for idx, part in enumerate(path_parts):
        if part == "channel" and idx + 1 < len(path_parts):
            candidates.append(path_parts[idx + 1])
        elif part in {"watch", "shorts", "live"} and idx + 1 < len(path_parts):
            candidates.append(path_parts[idx + 1])
        elif part.startswith("@"):
            candidates.append(part[1:])

    uc_match = re.search(r"(UC[\w-]{20,})", query)
    if uc_match:
        candidates.append(uc_match.group(1))

    cleaned: list[str] = []
    for item in candidates:
        item = item.strip().strip("/")
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def _normalize_to_youtube_url(channel_url_or_id: str) -> str:
    s = channel_url_or_id.strip()
    if s.startswith(("http://", "https://")):
        return s
    if s.startswith("@"):
        return f"https://www.youtube.com/{s}"
    if CHANNEL_ID_RE.match(s):
        return f"https://www.youtube.com/channel/{s}"
    return f"https://www.youtube.com/{s}"


def _to_videos_tab(url: str) -> str:
    tab_suffixes = ("/videos", "/shorts", "/streams", "/playlists", "/community", "/about")
    if any(suffix in url for suffix in tab_suffixes):
        return url
    if "watch?v=" in url or "/playlist?" in url:
        return url
    return url.rstrip("/") + "/videos"


def _fetch_video_detail(video_url: str) -> dict:
    from yt_dlp import YoutubeDL

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "socket_timeout": 10,
        "extractor_retries": 1,
        "fragment_retries": 1,
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=False) or {}
    except Exception as exc:
        return {"webpage_url": video_url, "error": str(exc)}
    return {key: info.get(key) for key in VIDEO_KEEP_FIELDS}


def fetch_channel_dump(
    channel_url_or_id: str,
    video_limit: int = 50,
    max_workers: int = 8,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict:
    """yt-dlp로 채널과 최근 영상 메타데이터를 수집한다. 댓글은 수집하지 않는다."""
    from yt_dlp import YoutubeDL

    url = _to_videos_tab(_normalize_to_youtube_url(channel_url_or_id))
    flat_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "playlistend": video_limit,
        "socket_timeout": 10,
        "extractor_retries": 1,
    }
    with YoutubeDL(flat_opts) as ydl:
        data = ydl.extract_info(url, download=False) or {}

    entries = data.get("entries") or []
    video_urls = [
        entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
        for entry in entries
        if entry and (entry.get("id") or entry.get("url"))
    ]

    if not video_urls:
        return data

    total = len(video_urls)
    if on_progress is None:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            details = list(executor.map(_fetch_video_detail, video_urls))
    else:
        details = [None] * total
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_fetch_video_detail, url): i for i, url in enumerate(video_urls)}
            done = 0
            on_progress(0, total)
            for future in as_completed(futures):
                details[futures[future]] = future.result()
                done += 1
                on_progress(done, total)

    data["entries"] = details
    return data


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_channel_dump_for_ui(channel_url_or_id: str) -> tuple[dict | None, str | None]:
    try:
        dump = fetch_channel_dump(channel_url_or_id, video_limit=50, max_workers=8)
    except Exception as exc:
        return None, str(exc)
    if not dump or not dump.get("entries"):
        return None, "채널 또는 공개 영상을 가져오지 못했습니다."
    return dump, None


@st.cache_data(show_spinner=False, ttl=300)
def find_channel_by_sql_query(raw_query: str) -> tuple[dict | None, str | None]:
    """Channel ID, channel URL, or video URL을 MySQL 채널 레코드로 매핑한다."""
    candidates = _lookup_candidates(raw_query)
    if not candidates:
        return None, None

    sql = """
        SELECT
            ci.channel_identifier,
            ci.youtube_channel_id,
            ci.channel_name,
            ci.subscriber_count,
            ci.total_views,
            ci.video_count,
            ci.created_date,
            ci.latest_video_date,
            ci.days_since_latest_video,
            ci.is_churned,
            ca.collected_video_count,
            ca.days_since_last_upload,
            ca.avg_upload_interval_days,
            ca.std_upload_interval_days,
            ca.max_gap_days AS analytics_max_gap_days,
            ca.hiatus_count_30d,
            ca.upload_freq_change_rate,
            ca.avg_view_count,
            ca.std_view_count,
            ca.avg_like_count,
            ca.avg_comment_count,
            ca.avg_engagement_rate,
            ca.shorts_ratio,
            cp.churn_prob,
            cp.stagnation_prob,
            cp.volatility_prob,
            cs.active_viewer_score,
            cs.regularity_score,
            cs.sensitive_score,
            cs.fan_type_code,
            ft.fan_type_label,
            cats.category_names
        FROM channel_info_table ci
        LEFT JOIN channel_analytics_table ca
            ON ca.channel_identifier = ci.channel_identifier
        LEFT JOIN channel_prediction_table cp
            ON cp.channel_identifier = ci.channel_identifier
        LEFT JOIN channel_score_table cs
            ON cs.channel_identifier = ci.channel_identifier
        LEFT JOIN fan_type_table ft
            ON ft.fan_type_code = cs.fan_type_code
        LEFT JOIN (
            SELECT
                cct.channel_identifier,
                GROUP_CONCAT(ct.category_name ORDER BY ct.category_name SEPARATOR ', ') AS category_names
            FROM channel_category_table cct
            JOIN category_table ct
                ON ct.category_id = cct.category_id
            GROUP BY cct.channel_identifier
        ) cats
            ON cats.channel_identifier = ci.channel_identifier
        LEFT JOIN video_table vt
            ON vt.channel_identifier = ci.channel_identifier
        WHERE
            ci.youtube_channel_id IN %(candidates)s
            OR ci.channel_identifier IN %(candidates)s
            OR vt.video_id IN %(candidates)s
            OR ci.channel_name IN %(candidates)s
        LIMIT 1
    """

    try:
        with pymysql.connect(**_db_config()) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"candidates": tuple(candidates)})
                row = cur.fetchone()
        return row, None
    except Exception as exc:
        return None, str(exc)


def channel_exists_in_snapshot(channel_id: str) -> bool:
    wide = load_wide()
    return bool((wide["channel_id"] == channel_id).any())


def _format_int(n: float | int) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "-"


def _format_subs(n: float | int) -> str:
    """1.28M / 945K 같은 압축 표기."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "-"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return f"{n:,}"


def _grade_masks(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    dslu = df["days_since_last_upload"]
    a = dslu <= A_THRESHOLD_DAYS
    b = (dslu > A_THRESHOLD_DAYS) & (dslu <= CHURN_THRESHOLD_DAYS)
    c = dslu > CHURN_THRESHOLD_DAYS
    return a, b, c


def compute_kpis() -> list[dict]:
    df = load_wide()
    total = len(df)
    a, b, c = _grade_masks(df)
    n_a, n_b, n_c = int(a.sum()), int(b.sum()), int(c.sum())
    return [
        {
            "label": "수집 채널 수",
            "value": f"{ORIGINAL_POOL_TOTAL:,}",
            "unit": "개",
            "delta": f"필터 후 분석 대상 {total:,}개",
            "tone": "neutral",
        },
        {
            "label": "안심 채널 (A등급)",
            "value": f"{n_a:,}",
            "unit": "개",
            "delta": f"{n_a / total * 100:.1f}%",
            "tone": "positive",
        },
        {
            "label": "관찰 채널 (B등급)",
            "value": f"{n_b:,}",
            "unit": "개",
            "delta": f"{n_b / total * 100:.1f}%",
            "tone": "warning",
        },
        {
            "label": "주의 채널 (C등급)",
            "value": f"{n_c:,}",
            "unit": "개",
            "delta": f"{n_c / total * 100:.1f}%",
            "tone": "danger",
        },
    ]


def compute_grade_distribution() -> list[dict]:
    df = load_wide()
    total = len(df)
    a, b, c = _grade_masks(df)
    rows = [
        ("A등급 (안심)", int(a.sum()), GRADE_A_COLOR),
        ("B등급 (관찰)", int(b.sum()), GRADE_B_COLOR),
        ("C등급 (주의)", int(c.sum()), GRADE_C_COLOR),
    ]
    return [
        {"label": label, "count": count, "ratio": count / total, "color": color}
        for label, count, color in rows
    ]


def compute_subscriber_band_churn() -> dict:
    """구독자 구간별 '안심 채널(A등급)' 비율. 최근 30일 이내 업로드 기준."""
    df = load_wide()
    bands = [
        ("10만~20만", df["subscriber_count"] < 200_000),
        ("20만~30만", (df["subscriber_count"] >= 200_000) & (df["subscriber_count"] < 300_000)),
        ("30만~50만", (df["subscriber_count"] >= 300_000) & (df["subscriber_count"] < 500_000)),
        ("50만+", df["subscriber_count"] >= 500_000),
    ]
    labels: list[str] = []
    ratios: list[float] = []
    counts: list[int] = []
    totals: list[int] = []
    for label, mask in bands:
        n = int(mask.sum())
        safe = int(((df["days_since_last_upload"] <= A_THRESHOLD_DAYS) & mask).sum())
        labels.append(label)
        totals.append(n)
        counts.append(safe)
        ratios.append((safe / n * 100) if n > 0 else 0.0)
    return {"labels": labels, "ratios": ratios, "counts": counts, "totals": totals}


def compute_top_risky(n: int = 5) -> list[dict]:
    df = load_wide()
    top = df.sort_values(
        ["days_since_last_upload", "upload_freq_change_rate"],
        ascending=[False, True],
    ).head(n)
    return [
        {
            "rank": i,
            "name": row["title"],
            "days": int(row["days_since_last_upload"]),
        }
        for i, (_, row) in enumerate(top.iterrows(), start=1)
    ]


def compute_risk_signals() -> list[dict]:
    df = load_wide()
    total = len(df)

    pct_freq = (df["upload_freq_change_rate"] < 0).sum() / total * 100
    pct_hiatus = (df["hiatus_count_30d"] > 0).sum() / total * 100

    engagement = df["avg_engagement_rate"]
    pct_low_eng = (engagement < 0.01).sum() / engagement.notna().sum() * 100

    cv = df["std_view_count"] / df["avg_view_count"]
    pct_volatile = (cv > 1.0).sum() / cv.notna().sum() * 100

    return [
        {"icon": "📈", "label": "업로드 주기 증가", "value": round(pct_freq)},
        {"icon": "🛌", "label": "장기 공백 발생", "value": round(pct_hiatus)},
        {"icon": "👥", "label": "참여율 1% 미만", "value": round(pct_low_eng)},
        {"icon": "📉", "label": "조회수 변동 큼", "value": round(pct_volatile)},
    ]


# ─────────────────────────────────────────────────────────────
# 채널 단위 (1_채널_조회 페이지용)
# ─────────────────────────────────────────────────────────────


def _grade_from_dslu(dslu: float) -> str:
    if dslu <= A_THRESHOLD_DAYS:
        return "A"
    if dslu <= CHURN_THRESHOLD_DAYS:
        return "B"
    return "C"


def get_channel_overview(channel_id: str) -> dict:
    """좌측 '채널 기본 정보' 카드 데이터."""
    wide = load_wide()
    master = load_master()
    long = load_long()

    w = wide[wide["channel_id"] == channel_id].iloc[0]
    m_rows = master[master["youtube_channel_id"] == channel_id]
    m = m_rows.iloc[0] if len(m_rows) else None

    sub = long[long["channel_id"] == channel_id].sort_values("published_at")

    # 카테고리 / handle
    category = str(m["category"]) if m is not None else "기타"
    emoji = CATEGORY_EMOJI.get(category, "🎬")
    handle = f"@{w['title']}"

    # 가입일
    joined = pd.to_datetime(w["published_at"], utc=True, errors="coerce")
    joined_str = joined.strftime("%Y.%m.%d") if pd.notna(joined) else "-"

    # 마지막 업로드
    if len(sub) > 0:
        last_dt = sub["published_at"].iloc[-1]
        last_upload_date = last_dt.strftime("%Y.%m.%d")
    else:
        last_upload_date = "-"
    dslu = int(w["days_since_last_upload"])
    last_upload_days = f"{dslu:,}일 전"

    # 최근 30일 업로드 수 (마지막 영상 시점이 아니라 snapshot 기준)
    if len(sub) > 0:
        snap = sub["published_at"].max() + pd.Timedelta(days=dslu)
        thirty = snap - pd.Timedelta(days=30)
        uploads_30d = int(((sub["published_at"] >= thirty) & (sub["published_at"] <= snap)).sum())
    else:
        uploads_30d = 0

    # 평균 조회수(최근 5개) + 직전 5개 대비 변화율
    avg_view = float(w["avg_view_count"])
    if len(sub) >= 10:
        recent5 = sub["view_count"].tail(5).mean()
        prev5 = sub["view_count"].iloc[-10:-5].mean()
        if prev5 > 0:
            delta_pct = (recent5 - prev5) / prev5 * 100
            avg_view_delta = f"{delta_pct:+.0f}%"
            avg_view = recent5
        else:
            avg_view_delta = "-"
    else:
        avg_view_delta = "-"

    return {
        "handle": handle,
        "name": str(w["title"]),
        "category": category,
        "category_emoji": emoji,
        "subscriber_count": _format_subs(w["subscriber_count"]),
        "total_views": _format_int(w["view_count"]),
        "joined_at": joined_str,
        "last_upload_days": last_upload_days,
        "last_upload_date": last_upload_date,
        "uploads_30d": f"{uploads_30d}개",
        "avg_view": _format_int(avg_view),
        "avg_view_delta": avg_view_delta,
    }


def get_channel_prediction(channel_id: str) -> dict:
    """우측 '이탈 예측 결과' + 요약 지표."""
    wide = load_wide()
    churn = load_churn_probs()
    long = load_long()

    w = wide[wide["channel_id"] == channel_id].iloc[0]
    c_rows = churn[churn["channel_id"] == channel_id]
    grade = _grade_from_dslu(float(w["days_since_last_upload"]))
    if len(c_rows):
        risk_pct = round(float(c_rows.iloc[0]["churn_prob"]) * 100)
    else:
        risk_pct = {"A": 12, "B": 45, "C": 78}[grade]

    # 업로드 주기
    interval = float(w["avg_upload_interval_days"])
    freq_change = float(w["upload_freq_change_rate"])
    freq_tone = "danger" if freq_change < -0.3 else "warning" if freq_change < 0 else "positive"
    freq_delta = f"{freq_change * 100:+.0f}%" if freq_change != 0 else "변동 없음"

    # 조회수 변화 (최근 5개 vs 직전 5개)
    sub = long[long["channel_id"] == channel_id].sort_values("published_at")
    if len(sub) >= 10:
        recent5 = sub["view_count"].tail(5).mean()
        prev5 = sub["view_count"].iloc[-10:-5].mean()
        view_change = (recent5 - prev5) / prev5 * 100 if prev5 > 0 else 0
    else:
        view_change = 0.0
    view_tone = "danger" if view_change <= -30 else "warning" if view_change < 0 else "positive"
    view_label = "↑ 상승" if view_change > 0 else "↓ 하락" if view_change < 0 else "변동 없음"

    # 참여율
    eng = float(w["avg_engagement_rate"]) * 100
    eng_tone = "danger" if eng < 1.0 else "warning" if eng < 3.0 else "positive"

    summary = [
        {
            "label": "업로드 주기",
            "value": f"{interval:.0f}일",
            "delta": freq_delta,
            "tone": freq_tone,
        },
        {
            "label": "조회수 변화",
            "value": f"{view_change:+.0f}%",
            "delta": view_label,
            "tone": view_tone,
        },
        {
            "label": "참여율",
            "value": f"{eng:.1f}%",
            "delta": f"평균 좋아요 {_format_int(w['avg_like_count'])}",
            "tone": eng_tone,
        },
    ]

    return {"grade": grade, "risk_pct": risk_pct, "summary": summary}


def get_channel_top_reasons(channel_id: str, n: int = 3) -> list[dict]:
    """룰 기반 TOP N 사유."""
    wide = load_wide()
    w = wide[wide["channel_id"] == channel_id].iloc[0]

    candidates: list[tuple[float, dict]] = []

    dslu = float(w["days_since_last_upload"])
    if dslu > A_THRESHOLD_DAYS:
        candidates.append(
            (
                dslu,
                {
                    "title": "마지막 업로드 이후 장기 공백",
                    "desc": f"마지막 영상 이후 {int(dslu):,}일이 경과했습니다.",
                },
            )
        )

    freq_change = float(w["upload_freq_change_rate"])
    if freq_change < 0:
        candidates.append(
            (
                abs(freq_change) + 1,
                {
                    "title": "업로드 빈도 감소",
                    "desc": f"최근 3개월 업로드가 직전 3개월 대비 {abs(freq_change) * 100:.0f}% 감소했습니다.",
                },
            )
        )

    hiatus = float(w["hiatus_count_30d"])
    if hiatus > 0:
        candidates.append(
            (
                hiatus,
                {
                    "title": "반복적 30일+ 공백",
                    "desc": f"30일 이상 공백이 {int(hiatus)}회 발생했습니다.",
                },
            )
        )

    eng = float(w["avg_engagement_rate"])
    if eng < 0.01:
        candidates.append(
            (
                1.0 - eng * 100,
                {
                    "title": "참여율 미흡",
                    "desc": f"평균 참여율이 {eng * 100:.2f}%로 광고 효율 임계치를 밑돕니다.",
                },
            )
        )

    avg_v = float(w["avg_view_count"])
    std_v = float(w["std_view_count"])
    if avg_v > 0 and std_v / avg_v > 1.0:
        cv = std_v / avg_v
        candidates.append(
            (
                cv,
                {
                    "title": "조회수 변동성 큼",
                    "desc": f"영상별 조회수 편차가 평균 대비 {cv:.1f}배로 히트작 의존도가 높습니다.",
                },
            )
        )

    if not candidates:
        return [
            {
                "title": "주요 위험 신호 없음",
                "desc": "현재 wide 데이터 기준 트리거된 위험 신호가 없습니다.",
            }
        ]

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in candidates[:n]]


def get_channel_trends(channel_id: str, n_months: int = 12) -> dict:
    """월별 추이. 마지막 활동월 포함 최근 n_months 윈도우, 빈 월은 0."""
    long = load_long()
    sub = long[long["channel_id"] == channel_id].copy()
    if len(sub) == 0:
        empty: list[tuple[str, float]] = []
        return {
            "upload": empty,
            "view": empty,
            "engagement": empty,
            "like_ratio": empty,
            "comment_ratio": empty,
        }

    sub["ym"] = sub["published_at"].dt.tz_convert("UTC").dt.to_period("M")
    last_period = sub["ym"].max()
    first_period = last_period - (n_months - 1)
    rng = pd.period_range(first_period, last_period, freq="M")

    grouped = sub.groupby("ym")
    uploads = grouped.size().reindex(rng, fill_value=0)
    avg_view = grouped["view_count"].mean().reindex(rng).fillna(0)
    avg_like = grouped["like_count"].mean().reindex(rng).fillna(0)
    avg_comment = grouped["comment_count"].mean().reindex(rng).fillna(0)

    def _engagement(month_grp):
        likes = month_grp["like_count"].sum()
        comments = month_grp["comment_count"].sum()
        views = month_grp["view_count"].sum()
        return (likes + comments) / views * 100 if views > 0 else 0.0

    engagement = grouped.apply(_engagement).reindex(rng).fillna(0)
    like_ratio = (avg_like / avg_view.replace(0, pd.NA) * 100).fillna(0)
    comment_ratio = (avg_comment / avg_view.replace(0, pd.NA) * 100).fillna(0)

    labels = [p.strftime("%y.%m") for p in rng]

    def _pair(series):
        return [(labels[i], float(series.iloc[i])) for i in range(len(rng))]

    return {
        "upload": [(labels[i], int(uploads.iloc[i])) for i in range(len(rng))],
        "view": _pair(avg_view),
        "engagement": _pair(engagement),
        "like_ratio": _pair(like_ratio),
        "comment_ratio": _pair(comment_ratio),
    }


def get_channel_video_stats(channel_id: str) -> dict:
    """영상별 분포 + 요약 통계."""
    wide = load_wide()
    long = load_long()
    sub = long[long["channel_id"] == channel_id].sort_values("published_at")
    w = wide[wide["channel_id"] == channel_id].iloc[0]

    intervals = sub["published_at"].diff().dt.days.dropna().astype(int).tolist()
    views = sub["view_count"].fillna(0).astype(int).tolist()
    likes = sub["like_count"].fillna(0).astype(int).tolist()
    comments = sub["comment_count"].fillna(0).astype(int).tolist()

    avg_v = float(w["avg_view_count"]) if pd.notna(w["avg_view_count"]) else 0
    summary = {
        "avg_interval_days": float(w["avg_upload_interval_days"]) if pd.notna(w["avg_upload_interval_days"]) else 0,
        "max_gap_days": int(w["max_gap_days"]) if pd.notna(w["max_gap_days"]) else 0,
        "hiatus_count_30d": int(w["hiatus_count_30d"]) if pd.notna(w["hiatus_count_30d"]) else 0,
        "avg_view": avg_v,
        "std_view": float(w["std_view_count"]) if pd.notna(w["std_view_count"]) else 0,
        "max_view": max(views) if views else 0,
        "avg_engagement_rate": float(w["avg_engagement_rate"]) * 100 if pd.notna(w["avg_engagement_rate"]) else 0,
        "avg_like_rate": (sum(likes) / sum(views) * 100) if sum(views) > 0 else 0,
        "avg_comment_rate": (sum(comments) / sum(views) * 100) if sum(views) > 0 else 0,
        "shorts_ratio": float(w["shorts_ratio"]) if pd.notna(w["shorts_ratio"]) else 0,
    }

    return {
        "upload_intervals": intervals,
        "view_distribution": views,
        "like_per_video": likes,
        "comment_per_video": comments,
        "summary": summary,
    }


def get_channel_risk_signals(channel_id: str) -> list[dict]:
    """위험 신호 요약 4개 카드 (1_채널_조회 페이지 하단)."""
    wide = load_wide()
    w = wide[wide["channel_id"] == channel_id].iloc[0]

    def _level(value: float, danger_th: float, warn_th: float, higher_is_worse: bool = True) -> tuple[str, str]:
        worse = value >= danger_th if higher_is_worse else value <= danger_th
        warn = value >= warn_th if higher_is_worse else value <= warn_th
        if worse:
            return "높음", "danger"
        if warn:
            return "중간", "warning"
        return "낮음", "positive"

    # 1) 업로드 감소
    freq_change = float(w["upload_freq_change_rate"])
    f_level, f_tone = _level(-freq_change, 0.5, 0.1)  # 감소 폭이 클수록 worse
    s1 = {
        "label": "업로드 감소",
        "desc": (
            f"최근 3개월 업로드 빈도 {abs(freq_change) * 100:.0f}% "
            f"{'감소' if freq_change < 0 else '증가' if freq_change > 0 else '변동 없음'}"
        ),
        "level": f_level,
        "tone": f_tone,
    }

    # 2) 조회수 변동
    avg_v = float(w["avg_view_count"]) or 1
    std_v = float(w["std_view_count"])
    cv = std_v / avg_v if avg_v > 0 else 0
    c_level, c_tone = _level(cv, 1.5, 0.8)
    s2 = {
        "label": "조회수 변동",
        "desc": f"영상별 조회수 편차가 평균 대비 {cv:.1f}배",
        "level": c_level,
        "tone": c_tone,
    }

    # 3) 장기 공백
    dslu = float(w["days_since_last_upload"])
    d_level, d_tone = _level(dslu, 180, 30)
    s3 = {
        "label": "마지막 업로드 경과",
        "desc": f"마지막 영상 이후 {int(dslu):,}일",
        "level": d_level,
        "tone": d_tone,
    }

    # 4) 참여율 약화
    eng = float(w["avg_engagement_rate"]) * 100
    e_level, e_tone = _level(eng, 1.0, 3.0, higher_is_worse=False)  # 낮을수록 worse
    s4 = {
        "label": "참여율",
        "desc": f"평균 참여율 {eng:.1f}%",
        "level": e_level,
        "tone": e_tone,
    }

    return [s1, s2, s3, s4]


def get_channel_shap_proxy(channel_id: str) -> list[dict]:
    """SHAP 자리 — 룰 기반 위험 기여도 (정규화된 0~0.5 막대)."""
    wide = load_wide()
    w = wide[wide["channel_id"] == channel_id].iloc[0]

    dslu = float(w["days_since_last_upload"])
    freq_change = float(w["upload_freq_change_rate"])
    hiatus = float(w["hiatus_count_30d"])
    avg_v = float(w["avg_view_count"]) or 1
    std_v = float(w["std_view_count"])
    cv = std_v / avg_v if avg_v > 0 else 0
    eng = float(w["avg_engagement_rate"])

    def _clip(x: float) -> float:
        return max(0.0, min(0.5, round(x, 2)))

    factors = [
        ("마지막 업로드 경과", _clip(min(dslu, 500) / 1000)),  # 500일 → 0.5
        ("업로드 빈도 감소", _clip(max(0, -freq_change) * 0.5)),
        ("30일+ 공백 횟수", _clip(min(hiatus, 5) / 10)),
        ("조회수 변동성", _clip(min(cv, 3) / 6)),
        ("참여율 미흡", _clip(max(0, (0.05 - eng)) * 10)),
    ]
    factors.sort(key=lambda x: x[1], reverse=True)
    return [{"label": label, "value": value} for label, value in factors]
