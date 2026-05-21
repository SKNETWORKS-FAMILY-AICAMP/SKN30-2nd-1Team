"""채널 이탈 예측 (XGBoost + SHAP).

notebooks/02_modeling/churn_prediction_system.ipynb 의 로직을 앱용으로 이식.
첫 호출 시 학습 후 saved_models/churn_model.pkl 에 캐시되고,
이후 호출은 Streamlit @st.cache_resource 로 메모리 캐시 재사용한다.
"""

from __future__ import annotations

import re
from typing import Callable, Optional

import joblib
import numpy as np
import pandas as pd
import shap
import streamlit as st
from scipy.stats import linregress
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from data_loader import PROJECT_ROOT, load_long, load_wide

CHURN_DAYS = 180
RANDOM_STATE = 42

MODEL_PATH = PROJECT_ROOT / "saved_models" / "churn_model.pkl"

WIDE_FEATURES = [
    "subscriber_count", "view_count", "total_video_count",
    "avg_upload_interval_days", "std_upload_interval_days",
    "max_gap_days", "hiatus_count_30d",
    "avg_view_count", "std_view_count",
    "avg_like_count", "avg_comment_count", "avg_engagement_rate",
    "shorts_ratio", "avg_shorts_view", "avg_normal_view",
    "view_per_subscriber", "view_cv",
]
LONG_FEATURES = ["upload_slope", "recent_view_ratio", "days_between_last2"]
SCORE_FEATURE_FILES: dict[str, tuple[str, str]] = {
    "volatility_prob":     ("view_volatility_output.csv",  "volatility_prob"),
    "regularity_score":    ("upload_regularity_score.csv", "regularity_score"),
    "active_viewer_score": ("active_viewer_score.csv",     "active_viewer_score"),
    "sensitive_score":     ("sensitive_keyword_score.csv", "sensitive_score"),
}

FEATURE_KO = {
    "subscriber_count":         "구독자 수",
    "view_count":               "채널 누적 조회수",
    "total_video_count":        "전체 영상 수",
    "avg_upload_interval_days": "평균 업로드 간격(일)",
    "std_upload_interval_days": "업로드 간격 불규칙성",
    "max_gap_days":             "최대 공백 기간(일)",
    "hiatus_count_30d":         "30일+ 공백 횟수",
    "avg_view_count":           "평균 조회수",
    "std_view_count":           "조회수 변동성",
    "avg_like_count":           "평균 좋아요 수",
    "avg_comment_count":        "평균 댓글 수",
    "avg_engagement_rate":      "평균 참여율",
    "shorts_ratio":             "Shorts 비율",
    "avg_shorts_view":          "Shorts 평균 조회수",
    "avg_normal_view":          "일반 영상 평균 조회수",
    "view_per_subscriber":      "구독자 대비 조회수",
    "view_cv":                  "조회수 변동계수",
    "upload_slope":             "업로드 추세(기울기)",
    "recent_view_ratio":        "최근 조회수 추세",
    "days_between_last2":       "마지막 두 영상 간격",
    "volatility_prob":          "조회수 변동성 점수",
    "regularity_score":         "업로드 규칙성 점수",
    "active_viewer_score":      "활성 시청자 점수",
    "sensitive_score":          "민감 키워드 점수",
}

_CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
_URL_CHANNEL_RE = re.compile(r"youtube\.com/channel/(UC[\w-]{22})")


# ─────────────────────────────────────────────────────────────────────────────
# 학습 데이터셋 구성
# ─────────────────────────────────────────────────────────────────────────────

def _extract_long_features(group: pd.DataFrame, now_ts: pd.Timestamp) -> pd.Series:
    g = group.sort_values("published_at")
    ym = g["published_at"].dt.to_period("M")
    monthly = g.groupby(ym).size().reset_index(name="cnt")
    slope = linregress(range(len(monthly)), monthly["cnt"])[0] if len(monthly) >= 3 else np.nan
    views = g["view_count"].dropna().tolist()
    view_ratio = (
        round(np.mean(views[-10:]) / (np.mean(views) + 1e-9), 4)
        if len(views) >= 10 else np.nan
    )
    dates = g["published_at"].dropna().tolist()
    days_last2 = (dates[-1] - dates[-2]).days if len(dates) >= 2 else np.nan
    return pd.Series({
        "upload_slope": slope,
        "recent_view_ratio": view_ratio,
        "days_between_last2": days_last2,
    })


def _build_training_dataset() -> tuple[pd.DataFrame, list[str]]:
    wide_df = load_wide().copy()
    long_df = load_long().copy()

    wide_df["is_churned"] = (wide_df["days_since_last_upload"] >= CHURN_DAYS).astype(int)
    wide_df["view_cv"] = wide_df["std_view_count"] / (wide_df["avg_view_count"] + 1e-9)
    wide_df["view_per_subscriber"] = wide_df["avg_view_count"] / (wide_df["subscriber_count"] + 1e-9)
    wide_df["avg_shorts_view"] = wide_df["avg_shorts_view"].fillna(0)
    wide_df["avg_normal_view"] = wide_df["avg_normal_view"].fillna(0)
    wide_df["avg_engagement_rate"] = wide_df["avg_engagement_rate"].clip(0, 1)

    now_ts = long_df["published_at"].max()
    long_feats = (
        long_df.groupby("channel_id")
        .apply(lambda g: _extract_long_features(g, now_ts), include_groups=False)
        .reset_index()
    )

    merged = wide_df.merge(long_feats, on="channel_id", how="left")

    score_features: list[str] = []
    raw_dir = PROJECT_ROOT / "data" / "raw"
    for feat_name, (filename, col) in SCORE_FEATURE_FILES.items():
        path = raw_dir / filename
        if not path.exists():
            continue
        s = pd.read_csv(path, encoding="utf-8-sig")[["channel_id", col]].rename(
            columns={col: feat_name}
        )
        merged = merged.merge(s, on="channel_id", how="left")
        score_features.append(feat_name)

    all_features = WIDE_FEATURES + LONG_FEATURES + score_features
    for f in all_features:
        merged[f] = merged[f].fillna(merged[f].median())

    return merged, all_features


# ─────────────────────────────────────────────────────────────────────────────
# 모델 로드/학습 (Streamlit 캐시)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="이탈 예측 모델 준비 중...")
def get_model_bundle() -> dict:
    """모델 + 설명자 + DB 캐시. 디스크 캐시(.pkl) 우선, 없으면 학습."""
    merged_df, all_features = _build_training_dataset()

    if MODEL_PATH.exists():
        bundle = joblib.load(MODEL_PATH)
        if bundle.get("features") == all_features:
            bundle["merged_df"] = merged_df
            return bundle

    X = merged_df[all_features]
    y = merged_df["is_churned"]
    X_train, _, y_train, _ = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)

    model = XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=pos_weight, eval_metric="logloss",
        random_state=RANDOM_STATE, verbosity=0,
    )
    model.fit(X_train, y_train)
    explainer = shap.TreeExplainer(model)

    bundle = {
        "model": model,
        "explainer": explainer,
        "features": all_features,
        "feature_medians": {f: float(merged_df[f].median()) for f in all_features},
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, MODEL_PATH)
    bundle["merged_df"] = merged_df
    return bundle


# ─────────────────────────────────────────────────────────────────────────────
# 입력 → channel_id / DB 조회
# ─────────────────────────────────────────────────────────────────────────────

def extract_channel_id_from_query(query: str) -> Optional[str]:
    q = query.strip()
    if _CHANNEL_ID_RE.match(q):
        return q
    m = _URL_CHANNEL_RE.search(q)
    if m:
        return m.group(1)
    return None


def get_db_features(channel_id: str, bundle: dict) -> Optional[tuple[pd.DataFrame, str]]:
    merged = bundle["merged_df"]
    row = merged[merged["channel_id"] == channel_id]
    if len(row) == 0:
        return None
    name = str(row.iloc[0]["title"]) if "title" in row.columns else "알 수 없음"
    return row[bundle["features"]].copy().reset_index(drop=True), name


# ─────────────────────────────────────────────────────────────────────────────
# yt-dlp dump → 피처
# ─────────────────────────────────────────────────────────────────────────────

def compute_features_from_dump(dump: dict, bundle: dict) -> tuple[pd.DataFrame, str, str]:
    entries = dump.get("entries") or []
    valid = [e for e in entries if e and not e.get("error") and e.get("view_count") is not None]
    if not valid:
        raise ValueError("유효한 영상 정보가 없습니다.")

    channel_name = (
        dump.get("channel") or dump.get("title")
        or valid[0].get("channel") or valid[0].get("uploader") or "알 수 없음"
    )
    channel_id = dump.get("channel_id") or valid[0].get("channel_id") or ""

    df_v = pd.DataFrame([{
        "view_count": e.get("view_count") or 0,
        "like_count": e.get("like_count") or 0,
        "comment_count": e.get("comment_count") or 0,
        "duration": e.get("duration") or 0,
        "upload_date": e.get("upload_date"),
    } for e in valid])
    df_v["published_at"] = pd.to_datetime(
        df_v["upload_date"], format="%Y%m%d", errors="coerce", utc=True
    )
    df_v["is_shorts"] = df_v["duration"] <= 60
    df_v = df_v.sort_values("published_at").reset_index(drop=True)

    sub_cnt = dump.get("channel_follower_count") or 0
    tot_vids = dump.get("playlist_count") or len(valid)

    dates = df_v["published_at"].dropna().tolist()
    intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)] if len(dates) > 1 else [0]

    monthly = df_v.dropna(subset=["published_at"]).copy()
    monthly["ym"] = monthly["published_at"].dt.to_period("M")
    monthly_g = monthly.groupby("ym").size().reset_index(name="cnt")
    slope_val = (
        linregress(range(len(monthly_g)), monthly_g["cnt"])[0]
        if len(monthly_g) >= 3 else np.nan
    )

    views = df_v["view_count"].dropna().tolist()
    view_ratio = (
        round(np.mean(views[-10:]) / (np.mean(views) + 1e-9), 4)
        if len(views) >= 10 else np.nan
    )
    d_last2 = (dates[-1] - dates[-2]).days if len(dates) >= 2 else np.nan

    shorts = df_v[df_v["is_shorts"]]
    normal = df_v[~df_v["is_shorts"]]
    avg_view = float(df_v["view_count"].mean()) if len(df_v) else 0.0
    std_view = float(df_v["view_count"].std()) if len(df_v) > 1 else 0.0

    eng = ((df_v["like_count"] + df_v["comment_count"]) / (df_v["view_count"] + 1e-9)).mean()

    feat: dict[str, float] = {
        "subscriber_count":         sub_cnt,
        "view_count":               float(df_v["view_count"].sum()),
        "total_video_count":        tot_vids,
        "avg_upload_interval_days": float(np.mean(intervals)) if intervals else 0.0,
        "std_upload_interval_days": float(np.std(intervals)) if intervals else 0.0,
        "max_gap_days":             float(max(intervals)) if intervals else 0.0,
        "hiatus_count_30d":         float(sum(1 for d in intervals if d >= 30)),
        "avg_view_count":           avg_view,
        "std_view_count":           std_view,
        "avg_like_count":           float(df_v["like_count"].mean()) if len(df_v) else 0.0,
        "avg_comment_count":        float(df_v["comment_count"].mean()) if len(df_v) else 0.0,
        "avg_engagement_rate":      float(min(eng, 1)) if pd.notna(eng) else 0.0,
        "shorts_ratio":             len(shorts) / (len(df_v) + 1e-9),
        "avg_shorts_view":          float(shorts["view_count"].mean()) if len(shorts) > 0 else 0.0,
        "avg_normal_view":          float(normal["view_count"].mean()) if len(normal) > 0 else 0.0,
        "view_per_subscriber":      avg_view / (sub_cnt + 1e-9),
        "view_cv":                  std_view / (avg_view + 1e-9),
        "upload_slope":             slope_val,
        "recent_view_ratio":        view_ratio,
        "days_between_last2":       d_last2,
    }

    # score 피처는 yt-dlp 만으로는 못 구하므로 학습셋 median 으로 대체
    for f in bundle["features"]:
        if f not in feat:
            feat[f] = bundle["feature_medians"].get(f, 0.0)

    df = pd.DataFrame([feat])[bundle["features"]]
    medians = pd.Series(bundle["feature_medians"])
    df = df.fillna(medians).fillna(0)
    return df, str(channel_name), str(channel_id)


# ─────────────────────────────────────────────────────────────────────────────
# 메인 예측 진입점
# ─────────────────────────────────────────────────────────────────────────────

def _risk_level(prob: float) -> str:
    if prob >= 0.7:
        return "🔴 고위험"
    if prob >= 0.4:
        return "🟡 주의"
    return "🟢 안전"


def predict_for_query(
    query: str,
    dump: Optional[dict] = None,
    on_stage: Optional[Callable[[str, float], None]] = None,
    force_fetch: bool = False,
) -> dict:
    """채널 검색 입력 → 예측 결과 dict.

    1) channel_id 추출 가능하면 DB 조회
    2) DB에 없거나 channel_id 못 알아내면 yt-dlp 수집
    3) 모델 예측 + SHAP Top 3

    on_stage(label, fraction) 콜백이 주어지면 단계마다 호출된다 (0.0~1.0).
    """
    def _report(label: str, frac: float) -> None:
        if on_stage is not None:
            on_stage(label, max(0.0, min(1.0, frac)))

    _report("모델 준비 중...", 0.02)
    bundle = get_model_bundle()
    model = bundle["model"]
    explainer = bundle["explainer"]
    features = bundle["features"]
    _report("모델 준비 완료", 0.10)

    source: Optional[str] = None
    feat_df: Optional[pd.DataFrame] = None
    channel_name = "알 수 없음"
    channel_id = extract_channel_id_from_query(query) or ""

    _report("DB에서 채널 조회 중...", 0.15)
    if channel_id and not force_fetch:
        db_res = get_db_features(channel_id, bundle)
        if db_res is not None:
            feat_df, channel_name = db_res
            source = "DB"
            _report("DB에서 발견 — 피처 로드 완료", 0.90)

    if feat_df is None:
        _fetch_source = "live"
        if dump is None:
            from data_loader import YOUTUBE_FETCH_BACKEND

            def _make_progress_cb(label_tpl: str):
                def _cb(done: int, total: int) -> None:
                    if total <= 0:
                        return
                    frac = 0.20 + 0.65 * (done / total)
                    _report(label_tpl.format(done=done, total=total), frac)
                return _cb

            _fetch_source = "unknown"

            if YOUTUBE_FETCH_BACKEND == "google":
                _report("YouTube API로 채널 수집 중...", 0.18)
                try:
                    from youtube_api_fetcher import fetch_channel_dump as _api_fetch
                    dump = _api_fetch(
                        query,
                        video_limit=50,
                        on_progress=_make_progress_cb("YouTube API 영상 수집 {done}/{total}..."),
                    )
                    _fetch_source = "YouTube API"
                except Exception as _api_err:
                    _report(f"YouTube API 실패 → yt-dlp로 재시도 중...", 0.18)
                    try:
                        from yt_dlp_fetcher import fetch_channel_dump as _yt_fetch
                    except ModuleNotFoundError as e:
                        raise RuntimeError(
                            "YouTube API 실패 + yt-dlp 패키지 없음.\n"
                            "→ `.venv/bin/python -m pip install yt-dlp` 후 다시 시도하세요."
                        ) from e
                    dump = _yt_fetch(
                        query,
                        video_limit=50,
                        on_progress=_make_progress_cb("yt-dlp 영상 수집 {done}/{total}..."),
                    )
                    _fetch_source = "yt-dlp"
            else:
                _report("yt-dlp 채널 수집 중...", 0.18)
                try:
                    from yt_dlp_fetcher import fetch_channel_dump as _yt_fetch
                except ModuleNotFoundError as e:
                    raise RuntimeError(
                        "DB에 없는 채널입니다. yt-dlp 수집이 필요한데 "
                        "venv에 `yt-dlp` 패키지가 없습니다.\n"
                        "→ `.venv/bin/python -m pip install yt-dlp` 후 다시 시도하세요."
                    ) from e
                dump = _yt_fetch(
                    query,
                    video_limit=50,
                    on_progress=_make_progress_cb("yt-dlp 영상 수집 {done}/{total}..."),
                )
                _fetch_source = "yt-dlp"

        _report("피처 계산 중...", 0.88)
        feat_df, channel_name, ytdlp_cid = compute_features_from_dump(dump, bundle)
        channel_id = channel_id or ytdlp_cid
        source = _fetch_source
        if channel_id:
            db_res = get_db_features(channel_id, bundle)
            if db_res is not None:
                feat_df, channel_name = db_res
                source = "DB"

    _report("모델 예측 + SHAP 계산 중...", 0.93)
    churn_prob = float(model.predict_proba(feat_df)[0][1])

    # EDA 기반 확률이 있으면 우선 사용
    if channel_id:
        from data_loader import get_eda_churn_prob
        eda_prob = get_eda_churn_prob(channel_id)
        if eda_prob is not None:
            churn_prob = eda_prob

    churn_pred = int(churn_prob >= 0.5)

    sv = explainer.shap_values(feat_df)
    shap_s = pd.Series(sv[0], index=features)
    top_idx = shap_s.abs().sort_values(ascending=False).head(3).index

    top_reasons = []
    for f in top_idx:
        sv_val = float(shap_s[f])
        top_reasons.append({
            "feature": f,
            "ko_name": FEATURE_KO.get(f, f),
            "value": float(feat_df[f].values[0]),
            "shap": sv_val,
            "direction": "이탈 위험 ↑" if sv_val > 0 else "이탈 위험 ↓",
        })

    _report("완료", 1.0)

    channel_meta = None
    if dump is not None:
        valid_vids = [e for e in (dump.get("entries") or []) if e and not e.get("error")]
        views    = [e.get("view_count")   or 0 for e in valid_vids]
        likes    = [e.get("like_count")   or 0 for e in valid_vids]
        comments = [e.get("comment_count") or 0 for e in valid_vids]
        durations = [e.get("duration")    or 0 for e in valid_vids]

        last_date = max((e.get("upload_date") or "") for e in valid_vids) if valid_vids else None

        # 업로드 간격 (날짜 정렬 후 연속 diff)
        date_strs = sorted(
            e.get("upload_date") for e in valid_vids if e.get("upload_date")
        )
        if len(date_strs) >= 2:
            date_objs = pd.to_datetime(date_strs, format="%Y%m%d", errors="coerce", utc=True).dropna()
            intervals = np.diff(date_objs.asi8) / 1e9 / 86400  # ns → days
            avg_interval = float(np.mean(intervals)) if len(intervals) else 0.0
        else:
            avg_interval = 0.0

        # 참여율: (like + comment) / view 평균
        eng_per_vid = [
            (l + c) / (v + 1e-9) for v, l, c in zip(views, likes, comments)
        ]
        engagement_rate = float(np.mean(eng_per_vid)) if eng_per_vid else 0.0

        # Shorts 비율 (duration ≤ 60s)
        shorts_ratio = sum(1 for d in durations if d <= 60) / (len(durations) + 1e-9)

        # 최근 5개 vs 직전 5개 조회수 변화율
        if len(views) >= 10:
            recent_trend = (np.mean(views[-5:]) - np.mean(views[-10:-5])) / (np.mean(views[-10:-5]) + 1e-9) * 100
        else:
            recent_trend = 0.0

        avg_view_5 = (
            sum(views[-5:]) / len(views[-5:]) if len(views) >= 5
            else (sum(views) / len(views) if views else 0)
        )

        channel_meta = {
            "subscriber_count":      dump.get("channel_follower_count"),
            "total_video_count":     dump.get("playlist_count") or len(valid_vids),
            "collected_video_count": len(valid_vids),
            "total_channel_views":   dump.get("view_count"),
            "handle":              dump.get("uploader_id"),
            "last_upload_date":    last_date,
            "avg_view_5":          avg_view_5,
            "avg_like":            float(np.mean(likes))    if likes    else 0.0,
            "avg_comment":         float(np.mean(comments)) if comments else 0.0,
            "engagement_rate":     engagement_rate,
            "shorts_ratio":        float(shorts_ratio),
            "avg_upload_interval": avg_interval,
            "recent_view_trend":   float(recent_trend),
        }

    video_entries = None
    if dump is not None:
        valid_vids_for_entries = [e for e in (dump.get("entries") or []) if e and not e.get("error")]
        video_entries = [
            {
                "upload_date":   e.get("upload_date"),
                "view_count":    e.get("view_count")    or 0,
                "like_count":    e.get("like_count")    or 0,
                "comment_count": e.get("comment_count") or 0,
                "duration":      e.get("duration")      or 0,
                "title":         e.get("title")         or "",
                "thumbnail":     e.get("thumbnail")     or "",
                "webpage_url":   e.get("webpage_url")   or "",
            }
            for e in valid_vids_for_entries
        ]

    return {
        "source": source or "unknown",
        "channel_id": channel_id,
        "channel_name": channel_name,
        "churn_prob": churn_prob,
        "churn_pred": churn_pred,
        "prediction_label": "이탈 위험" if churn_pred else "활동 유지",
        "risk_level": _risk_level(churn_prob),
        "top_reasons": top_reasons,
        "channel_meta": channel_meta,
        "video_entries": video_entries,
    }
