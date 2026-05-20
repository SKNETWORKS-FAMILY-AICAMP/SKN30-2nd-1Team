from __future__ import annotations

import json
import warnings
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
REPORT_DIR = ROOT / "reports" / "eda"
DOCS_SCHEMA_PATH = ROOT / "docs" / "eda_core_table_schema.md"
NOTEBOOK_PATH = ROOT / "notebooks" / "02_eda" / "01_core_tables_eda.ipynb"

COLLATION = "utf8mb4_unicode_ci"


SOURCE_FILES = {
    "channel_info_source": {
        "path": RAW / "youtube_channels_filtered.csv",
        "key": "youtube_channel_id",
        "description": "기존 DB channel_info_table 기준 소스",
    },
    "active_viewer_score": {
        "path": RAW / "active_viewer_score.csv",
        "key": "channel_id",
        "description": "활성 시청자 점수",
    },
    "sensitive_keyword_score": {
        "path": RAW / "sensitive_keyword_score.csv",
        "key": "channel_id",
        "description": "민감 키워드/위험도 점수",
    },
    "upload_regularity_score": {
        "path": RAW / "upload_regularity_score.csv",
        "key": "channel_id",
        "description": "업로드 규칙성 점수",
    },
    "churn_probability_output": {
        "path": RAW / "churn_probability_output.csv",
        "key": "channel_id",
        "description": "이탈 확률 모델 결과",
    },
    "stagnation_probability_output": {
        "path": RAW / "stagnation_probability_output.csv",
        "key": "channel_id",
        "description": "정체 확률 모델 결과",
    },
    "view_volatility_output": {
        "path": RAW / "view_volatility_output.csv",
        "key": "channel_id",
        "description": "조회수 변동성 모델 결과",
    },
    "filtered_dataset_long": {
        "path": RAW / "filtered_dataset_long.csv",
        "key": "video_id",
        "description": "영상 단위 원본 데이터",
    },
    "filtered_dataset_wide": {
        "path": RAW / "filtered_dataset_wide.csv",
        "key": "channel_id",
        "description": "channel_info_table과 중복되어 적재 스킵",
    },
}


EXISTING_DB_TABLES = [
    {
        "table": "channel_info_table",
        "status": "loaded",
        "key": "PK: channel_identifier",
        "description": "채널 기본 정보. 추가 적재 테이블은 youtube_channel_id를 FK 기준으로 사용",
    },
    {
        "table": "category_table",
        "status": "loaded",
        "key": "category key",
        "description": "카테고리 정보",
    },
    {
        "table": "channel_category_table",
        "status": "loaded",
        "key": "channel-category bridge",
        "description": "채널-카테고리 중간 테이블",
    },
    {
        "table": "band_table",
        "status": "loaded",
        "key": "band key",
        "description": "구독자 범위 구간 정보",
    },
    {
        "table": "comments_table",
        "status": "loaded",
        "key": "comment key",
        "description": "댓글 데이터. video_info_table과 video_id가 다를 수 있어 연결하지 않음",
    },
]


PLANNED_DB_TABLES = [
    {
        "table": "active_viewer_score_table",
        "source": "data/raw/active_viewer_score.csv",
        "load_strategy": "channel_id 기준 1:1 적재",
        "primary_key": "channel_id",
        "foreign_key": "channel_id -> channel_info_table.youtube_channel_id",
        "description": "활성 시청자 점수",
    },
    {
        "table": "sensitive_keyword_score_table",
        "source": "data/raw/sensitive_keyword_score.csv",
        "load_strategy": "channel_id 기준 1:1 적재",
        "primary_key": "channel_id",
        "foreign_key": "channel_id -> channel_info_table.youtube_channel_id",
        "description": "민감 키워드/위험도 점수",
    },
    {
        "table": "upload_regularity_score_table",
        "source": "data/raw/upload_regularity_score.csv",
        "load_strategy": "channel_id 기준 1:1 적재",
        "primary_key": "channel_id",
        "foreign_key": "channel_id -> channel_info_table.youtube_channel_id",
        "description": "업로드 규칙성 점수",
    },
    {
        "table": "channel_prediction_table",
        "source": "churn_probability_output.csv + view_volatility_output.csv + stagnation_probability_output.csv",
        "load_strategy": "3개 예측 결과를 channel_id 기준 outer merge 후 channel_info_table FK 가능 행만 적재",
        "primary_key": "channel_id",
        "foreign_key": "channel_id -> channel_info_table.youtube_channel_id",
        "description": "모델 예측 결과 통합 테이블",
    },
    {
        "table": "video_info_table",
        "source": "data/raw/filtered_dataset_long.csv",
        "load_strategy": "video_id 기준 영상 단위 적재",
        "primary_key": "video_id",
        "foreign_key": "channel_id -> channel_info_table.youtube_channel_id",
        "description": "영상 단위 원본 데이터",
    },
]


POST_LOAD_EDA_MARTS = [
    {
        "eda_view": "v_channel_score_eda",
        "grain": "채널 1개",
        "base_tables": "channel_info_table + active_viewer_score_table + sensitive_keyword_score_table + upload_regularity_score_table + channel_prediction_table",
        "purpose": "채널별 활성 시청자, 민감 키워드, 업로드 규칙성, 3종 예측 확률을 한 번에 보는 핵심 EDA 뷰",
    },
    {
        "eda_view": "v_category_score_eda",
        "grain": "카테고리 x 채널",
        "base_tables": "category_table + channel_category_table + v_channel_score_eda",
        "purpose": "카테고리별 위험/활성/민감도 분포 비교",
    },
    {
        "eda_view": "v_band_score_eda",
        "grain": "구독자 밴드 x 채널",
        "base_tables": "band_table + channel_info_table + v_channel_score_eda",
        "purpose": "구독자 규모 구간별 위험/예측 점수 분포 비교",
    },
    {
        "eda_view": "v_video_activity_eda",
        "grain": "영상 1개",
        "base_tables": "video_info_table + channel_info_table",
        "purpose": "영상 업로드 시계열, Shorts 비율, 조회/좋아요/댓글 분포 분석",
    },
    {
        "eda_view": "v_comment_community_eda",
        "grain": "댓글 1개",
        "base_tables": "comments_table",
        "purpose": "댓글 수, 작성 시점, 좋아요, 작성자/대댓글 구조 분석. video_info_table과는 FK 연결하지 않음",
    },
    {
        "eda_view": "v_prediction_model_eda",
        "grain": "채널 1개",
        "base_tables": "channel_prediction_table + channel_info_table",
        "purpose": "churn/stagnation/volatility 예측 확률 간 상관, 결측, 모델 커버리지 분석",
    },
]


DESIGN_DECISIONS = [
    {
        "decision": "FK 기준",
        "detail": "CSV의 channel_id는 유튜브 난수값이며 channel_info_table.youtube_channel_id에 연결한다.",
    },
    {
        "decision": "filtered_dataset_wide 스킵",
        "detail": "채널 단위 wide 피처는 channel_info_table과 역할이 중복되어 별도 테이블로 적재하지 않는다.",
    },
    {
        "decision": "댓글-영상 미연결",
        "detail": "video_info_table과 comments_table은 video_id가 다를 수 있어 FK를 만들지 않는다.",
    },
    {
        "decision": "예측 결과 통합",
        "detail": "churn, volatility, stagnation 결과는 channel_prediction_table 하나로 합친다.",
    },
    {
        "decision": "EDA 기준 시점",
        "detail": "아래 산출물은 기존 테이블과 추가 적재 테이블이 모두 적재 완료된 이후의 DB를 기준으로 구성한다.",
    },
    {
        "decision": "인코딩/정렬",
        "detail": f"신규 테이블은 DEFAULT CHARSET=utf8mb4 COLLATE={COLLATION} 기준으로 생성한다.",
    },
]


DB_COLUMN_SCHEMA = [
    # active_viewer_score_table
    ("active_viewer_score_table", "channel_id", "VARCHAR(64)", "PK, FK", "source channel_id"),
    ("active_viewer_score_table", "title", "VARCHAR(255)", "", "채널명"),
    ("active_viewer_score_table", "subscriber_count", "BIGINT UNSIGNED", "", "구독자 수"),
    ("active_viewer_score_table", "avg_view_count", "DOUBLE", "", "평균 조회수"),
    ("active_viewer_score_table", "view_per_sub", "DOUBLE", "", "구독자 대비 조회수"),
    ("active_viewer_score_table", "cluster", "TINYINT", "", "KMeans cluster"),
    ("active_viewer_score_table", "cluster_name", "VARCHAR(50)", "", "클러스터명"),
    ("active_viewer_score_table", "active_viewer_score", "DECIMAL(10,6)", "", "활성 시청자 점수"),
    # sensitive_keyword_score_table
    ("sensitive_keyword_score_table", "channel_id", "VARCHAR(64)", "PK, FK", "source channel_id"),
    ("sensitive_keyword_score_table", "channel_title", "VARCHAR(255)", "", "채널명"),
    ("sensitive_keyword_score_table", "sensitive_score", "DECIMAL(10,6)", "", "민감 키워드 점수"),
    ("sensitive_keyword_score_table", "n_sensitive_videos", "INT UNSIGNED", "", "민감 영상 수"),
    ("sensitive_keyword_score_table", "sensitive_video_ratio", "DECIMAL(10,6)", "", "민감 영상 비율"),
    ("sensitive_keyword_score_table", "cat_politics", "INT UNSIGNED", "", "정치 카테고리 매칭 수"),
    ("sensitive_keyword_score_table", "cat_hate", "INT UNSIGNED", "", "혐오 카테고리 매칭 수"),
    ("sensitive_keyword_score_table", "cat_aggro", "INT UNSIGNED", "", "어그로 카테고리 매칭 수"),
    ("sensitive_keyword_score_table", "cat_adult_illegal", "INT UNSIGNED", "", "성인/불법 카테고리 매칭 수"),
    # upload_regularity_score_table
    ("upload_regularity_score_table", "channel_id", "VARCHAR(64)", "PK, FK", "source channel_id"),
    ("upload_regularity_score_table", "channel_title", "VARCHAR(255)", "", "채널명"),
    ("upload_regularity_score_table", "regularity_score", "DECIMAL(10,6)", "", "업로드 규칙성 점수"),
    ("upload_regularity_score_table", "mean_interval_days", "DOUBLE", "", "평균 업로드 간격"),
    ("upload_regularity_score_table", "std_interval_days", "DOUBLE", "", "업로드 간격 표준편차"),
    ("upload_regularity_score_table", "max_gap_days", "DOUBLE", "", "최대 업로드 공백"),
    ("upload_regularity_score_table", "cv", "DOUBLE", "", "변동계수"),
    ("upload_regularity_score_table", "outlier_ratio", "DECIMAL(10,6)", "", "이상 간격 비율"),
    ("upload_regularity_score_table", "gap_ratio", "DECIMAL(10,6)", "", "공백 비율"),
    # channel_prediction_table
    ("channel_prediction_table", "channel_id", "VARCHAR(64)", "PK, FK", "source channel_id"),
    ("channel_prediction_table", "title", "VARCHAR(255)", "", "대표 채널명"),
    ("channel_prediction_table", "churn_actual_label", "TINYINT", "", "이탈 모델 라벨"),
    ("channel_prediction_table", "churn_prob_lr", "DECIMAL(10,6)", "", "LR 이탈 확률"),
    ("channel_prediction_table", "churn_prob_rf", "DECIMAL(10,6)", "", "RF 이탈 확률"),
    ("channel_prediction_table", "churn_prob_xgb", "DECIMAL(10,6)", "", "XGB 이탈 확률"),
    ("channel_prediction_table", "churn_prob", "DECIMAL(10,6)", "", "앙상블 이탈 확률"),
    ("channel_prediction_table", "stagnation_actual_label", "TINYINT", "", "정체 모델 라벨"),
    ("channel_prediction_table", "stagnation_prob_lr", "DECIMAL(10,6)", "", "LR 정체 확률"),
    ("channel_prediction_table", "stagnation_prob_rf", "DECIMAL(10,6)", "", "RF 정체 확률"),
    ("channel_prediction_table", "stagnation_prob_xgb", "DECIMAL(10,6)", "", "XGB 정체 확률"),
    ("channel_prediction_table", "stagnation_prob", "DECIMAL(10,6)", "", "앙상블 정체 확률"),
    ("channel_prediction_table", "volatility_actual_label", "TINYINT", "", "변동성 모델 라벨"),
    ("channel_prediction_table", "volatility_prob_lr", "DECIMAL(10,6)", "", "LR 변동성 확률"),
    ("channel_prediction_table", "volatility_prob_rf", "DECIMAL(10,6)", "", "RF 변동성 확률"),
    ("channel_prediction_table", "volatility_prob_xgb", "DECIMAL(10,6)", "", "XGB 변동성 확률"),
    ("channel_prediction_table", "volatility_prob", "DECIMAL(10,6)", "", "앙상블 변동성 확률"),
    ("channel_prediction_table", "has_churn", "TINYINT", "", "churn 결과 존재 여부"),
    ("channel_prediction_table", "has_stagnation", "TINYINT", "", "stagnation 결과 존재 여부"),
    ("channel_prediction_table", "has_volatility", "TINYINT", "", "volatility 결과 존재 여부"),
    # video_info_table
    ("video_info_table", "video_id", "VARCHAR(32)", "PK", "영상 ID"),
    ("video_info_table", "channel_id", "VARCHAR(64)", "FK", "channel_info_table.youtube_channel_id"),
    ("video_info_table", "channel_title", "VARCHAR(255)", "", "영상 수집 시점 채널명"),
    ("video_info_table", "video_title", "TEXT", "", "영상 제목"),
    ("video_info_table", "published_at", "DATETIME", "", "영상 업로드 시각"),
    ("video_info_table", "duration_sec", "DOUBLE", "", "영상 길이 초"),
    ("video_info_table", "is_shorts", "TINYINT", "", "Shorts 여부"),
    ("video_info_table", "view_count", "BIGINT UNSIGNED", "", "조회수"),
    ("video_info_table", "like_count", "BIGINT UNSIGNED", "", "좋아요 수"),
    ("video_info_table", "comment_count", "BIGINT UNSIGNED", "", "댓글 수"),
    ("video_info_table", "source_file", "VARCHAR(255)", "", "원천 파일"),
    ("video_info_table", "channel_created_at", "DATETIME", "", "채널 생성 시각"),
    ("video_info_table", "country", "VARCHAR(8)", "", "국가 코드"),
    ("video_info_table", "subscriber_count", "BIGINT UNSIGNED", "", "채널 구독자 수"),
    ("video_info_table", "channel_total_views", "BIGINT UNSIGNED", "", "채널 누적 조회수"),
    ("video_info_table", "total_video_count", "BIGINT UNSIGNED", "", "채널 전체 영상 수"),
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False, **kwargs)


def md_table(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "(empty)"
    frame = df.copy().replace([np.inf, -np.inf], np.nan).fillna("")
    cols = [str(c) for c in frame.columns]

    def clean(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", "<br>")

    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(clean(row[col]) for col in frame.columns) + " |")
    return "\n".join(lines)


def row_count(path: Path) -> int:
    header = read_csv(path, nrows=0)
    if header.empty and len(header.columns) == 0:
        return 0
    first_col = header.columns[0]
    rows = 0
    for chunk in pd.read_csv(
        path,
        encoding="utf-8-sig",
        usecols=[first_col],
        chunksize=200_000,
        low_memory=False,
    ):
        rows += len(chunk)
    return rows


def clean_report_dir() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    for path in REPORT_DIR.iterdir():
        if path.is_file():
            path.unlink()


def source_inventory() -> pd.DataFrame:
    rows = []
    for name, meta in SOURCE_FILES.items():
        path = meta["path"]
        if not path.exists():
            rows.append(
                {
                    "source_name": name,
                    "path": rel(path),
                    "exists": False,
                    "rows": 0,
                    "cols": 0,
                    "key_column": meta["key"],
                    "description": meta["description"],
                }
            )
            continue
        header = read_csv(path, nrows=0)
        rows.append(
            {
                "source_name": name,
                "path": rel(path),
                "exists": True,
                "rows": row_count(path),
                "cols": len(header.columns),
                "size_mb": round(path.stat().st_size / 1024 / 1024, 3),
                "key_column": meta["key"],
                "description": meta["description"],
            }
        )
    return pd.DataFrame(rows)


def load_sources() -> dict[str, pd.DataFrame]:
    return {
        name: read_csv(meta["path"])
        for name, meta in SOURCE_FILES.items()
        if meta["path"].exists()
    }


def rename_prediction_columns(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    rename_map = {
        "title": f"{prefix}_title",
        "actual_label": f"{prefix}_actual_label",
        "prob_lr": f"{prefix}_prob_lr",
        "prob_rf": f"{prefix}_prob_rf",
        "prob_xgb": f"{prefix}_prob_xgb",
    }
    return df.rename(columns=rename_map)


def build_channel_prediction(sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
    churn = rename_prediction_columns(sources["churn_probability_output"], "churn")
    stagnation = rename_prediction_columns(sources["stagnation_probability_output"], "stagnation")
    volatility = rename_prediction_columns(sources["view_volatility_output"], "volatility")

    pred = churn.merge(stagnation, on="channel_id", how="outer").merge(
        volatility, on="channel_id", how="outer"
    )
    title_cols = [c for c in ["churn_title", "stagnation_title", "volatility_title"] if c in pred]
    pred["title"] = pred[title_cols].bfill(axis=1).iloc[:, 0]
    pred["has_churn"] = pred["churn_prob"].notna().astype(int)
    pred["has_stagnation"] = pred["stagnation_prob"].notna().astype(int)
    pred["has_volatility"] = pred["volatility_prob"].notna().astype(int)

    ordered = [
        "channel_id",
        "title",
        "churn_actual_label",
        "churn_prob_lr",
        "churn_prob_rf",
        "churn_prob_xgb",
        "churn_prob",
        "stagnation_actual_label",
        "stagnation_prob_lr",
        "stagnation_prob_rf",
        "stagnation_prob_xgb",
        "stagnation_prob",
        "volatility_actual_label",
        "volatility_prob_lr",
        "volatility_prob_rf",
        "volatility_prob_xgb",
        "volatility_prob",
        "has_churn",
        "has_stagnation",
        "has_volatility",
    ]
    return pred[[c for c in ordered if c in pred.columns]]


def key_profile(df: pd.DataFrame, key: str, fk_ids: set[str] | None = None) -> dict[str, object]:
    profile = {
        "source_rows": len(df),
        "key": key,
        "null_key_rows": int(df[key].isna().sum()) if key in df else None,
        "duplicate_key_rows": int(df[key].duplicated().sum()) if key in df else None,
        "unique_keys": int(df[key].nunique(dropna=True)) if key in df else None,
    }
    if fk_ids is not None and key in df:
        matched = df[key].dropna().astype(str).isin(fk_ids)
        profile["fk_matched_rows"] = int(matched.sum())
        profile["fk_unmatched_rows"] = int((~matched).sum())
        profile["fk_match_rate"] = round(float(matched.mean() * 100), 3) if len(matched) else 0.0
    return profile


def db_load_quality_checks(
    sources: dict[str, pd.DataFrame], channel_prediction: pd.DataFrame
) -> pd.DataFrame:
    channel_ids = set(sources["channel_info_source"]["youtube_channel_id"].dropna().astype(str))
    checks = []

    mapping = [
        ("active_viewer_score_table", "active_viewer_score", "channel_id"),
        ("sensitive_keyword_score_table", "sensitive_keyword_score", "channel_id"),
        ("upload_regularity_score_table", "upload_regularity_score", "channel_id"),
        ("video_info_table", "filtered_dataset_long", "video_id"),
    ]
    for table, source_name, key in mapping:
        df = sources[source_name]
        profile = key_profile(df, key, None if key == "video_id" else channel_ids)
        if table == "video_info_table":
            fk_profile = key_profile(df, "channel_id", channel_ids)
            profile.update(
                {
                    "fk_matched_rows": fk_profile["fk_matched_rows"],
                    "fk_unmatched_rows": fk_profile["fk_unmatched_rows"],
                    "fk_match_rate": fk_profile["fk_match_rate"],
                }
            )
        profile["table"] = table
        profile["source"] = SOURCE_FILES[source_name]["path"].relative_to(ROOT).as_posix()
        profile["expected_loaded_rows"] = profile.get("fk_matched_rows", profile["source_rows"])
        profile["load_policy"] = (
            "load_all" if profile.get("fk_unmatched_rows", 0) == 0 else "filter_fk_matched_only"
        )
        checks.append(profile)

    pred_profile = key_profile(channel_prediction, "channel_id", channel_ids)
    pred_profile["table"] = "channel_prediction_table"
    pred_profile["source"] = "3 prediction CSV outer merge"
    pred_profile["expected_loaded_rows"] = pred_profile["fk_matched_rows"]
    pred_profile["load_policy"] = "filter_fk_matched_only"
    checks.append(pred_profile)

    cols = [
        "table",
        "source",
        "source_rows",
        "expected_loaded_rows",
        "load_policy",
        "key",
        "null_key_rows",
        "duplicate_key_rows",
        "unique_keys",
        "fk_matched_rows",
        "fk_unmatched_rows",
        "fk_match_rate",
    ]
    return pd.DataFrame(checks)[cols]


def channel_prediction_merge_profile(
    channel_prediction: pd.DataFrame, channel_info_ids: set[str]
) -> pd.DataFrame:
    profiles = []
    fk_matched = channel_prediction["channel_id"].astype(str).isin(channel_info_ids)
    profiles.append(
        {
            "metric": "outer merged prediction rows",
            "rows": len(channel_prediction),
            "pct_of_prediction_table": 100.0,
        }
    )
    profiles.append(
        {
            "metric": "FK-compatible prediction rows",
            "rows": int(fk_matched.sum()),
            "pct_of_prediction_table": round(float(fk_matched.mean() * 100), 3),
        }
    )
    flags = [
        ("has_churn", "churn only/coverage"),
        ("has_stagnation", "stagnation coverage"),
        ("has_volatility", "volatility coverage"),
    ]
    for flag, label in flags:
        profiles.append(
            {
                "metric": label,
                "rows": int(channel_prediction[flag].sum()),
                "pct_of_prediction_table": round(float(channel_prediction[flag].mean() * 100), 3),
            }
        )

    complete_all = (
        (channel_prediction["has_churn"] == 1)
        & (channel_prediction["has_stagnation"] == 1)
        & (channel_prediction["has_volatility"] == 1)
    )
    profiles.append(
        {
            "metric": "all three predictions present",
            "rows": int(complete_all.sum()),
            "pct_of_prediction_table": round(float(complete_all.mean() * 100), 3),
        }
    )
    return pd.DataFrame(profiles)


def planned_table_frames(
    sources: dict[str, pd.DataFrame], channel_prediction: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    schema = db_column_schema_df()
    video_cols = schema[schema["table"] == "video_info_table"]["column"].tolist()
    prediction_cols = schema[schema["table"] == "channel_prediction_table"]["column"].tolist()
    return {
        "active_viewer_score_table": sources["active_viewer_score"],
        "sensitive_keyword_score_table": sources["sensitive_keyword_score"],
        "upload_regularity_score_table": sources["upload_regularity_score"],
        "channel_prediction_table": channel_prediction[
            [c for c in prediction_cols if c in channel_prediction.columns]
        ],
        "video_info_table": sources["filtered_dataset_long"][
            [c for c in video_cols if c in sources["filtered_dataset_long"].columns]
        ],
    }


def column_profile_for_planned_tables(
    sources: dict[str, pd.DataFrame], channel_prediction: pd.DataFrame
) -> pd.DataFrame:
    table_frames = planned_table_frames(sources, channel_prediction)
    rows = []
    for table, df in table_frames.items():
        for col in df.columns:
            s = df[col]
            item = {
                "table": table,
                "column": col,
                "source_dtype": str(s.dtype),
                "non_null": int(s.notna().sum()),
                "null_pct": round(float(s.isna().mean() * 100), 3),
                "n_unique": int(s.nunique(dropna=True)),
                "sample": next((str(x)[:80] for x in s.dropna().head(3)), ""),
            }
            if pd.api.types.is_numeric_dtype(s):
                clean = s.replace([np.inf, -np.inf], np.nan)
                item.update(
                    {
                        "min": round(float(clean.min()), 6) if clean.notna().any() else np.nan,
                        "median": round(float(clean.median()), 6) if clean.notna().any() else np.nan,
                        "max": round(float(clean.max()), 6) if clean.notna().any() else np.nan,
                    }
                )
            rows.append(item)
    return pd.DataFrame(rows)


def comment_file_summary() -> pd.DataFrame:
    base = RAW / "comments"
    rows = []
    for band_dir in sorted(base.glob("band_*")):
        if not band_dir.is_dir():
            continue
        file_count = 0
        non_empty = 0
        row_count_total = 0
        for file in sorted(band_dir.glob("*.csv")):
            file_count += 1
            header = read_csv(file, nrows=0)
            if len(header.columns) == 0:
                continue
            first_col = header.columns[0]
            rows_in_file = 0
            for chunk in pd.read_csv(
                file,
                encoding="utf-8-sig",
                usecols=[first_col],
                chunksize=50_000,
                low_memory=False,
            ):
                rows_in_file += len(chunk)
            row_count_total += rows_in_file
            if rows_in_file > 0:
                non_empty += 1
        rows.append(
            {
                "band": band_dir.name,
                "files": file_count,
                "non_empty_files": non_empty,
                "comment_rows": row_count_total,
            }
        )
    return pd.DataFrame(rows)


def db_column_schema_df() -> pd.DataFrame:
    return pd.DataFrame(
        DB_COLUMN_SCHEMA,
        columns=["table", "column", "db_type", "key_role", "description"],
    )


def make_ddl() -> str:
    return f"""-- Post-load DB schema reference for TubeEottae EDA
-- Base collation: {COLLATION}
-- channel_info_table.youtube_channel_id must be indexed before FK creation.

-- Run once if the index does not already exist.
-- ALTER TABLE channel_info_table ADD INDEX idx_channel_info_youtube_channel_id (youtube_channel_id);

CREATE TABLE IF NOT EXISTS active_viewer_score_table (
    channel_id VARCHAR(64) NOT NULL,
    title VARCHAR(255),
    subscriber_count BIGINT UNSIGNED,
    avg_view_count DOUBLE,
    view_per_sub DOUBLE,
    cluster TINYINT,
    cluster_name VARCHAR(50),
    active_viewer_score DECIMAL(10,6),
    PRIMARY KEY (channel_id),
    CONSTRAINT fk_active_viewer_channel
        FOREIGN KEY (channel_id) REFERENCES channel_info_table(youtube_channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE={COLLATION};

CREATE TABLE IF NOT EXISTS sensitive_keyword_score_table (
    channel_id VARCHAR(64) NOT NULL,
    channel_title VARCHAR(255),
    sensitive_score DECIMAL(10,6),
    n_sensitive_videos INT UNSIGNED,
    sensitive_video_ratio DECIMAL(10,6),
    cat_politics INT UNSIGNED,
    cat_hate INT UNSIGNED,
    cat_aggro INT UNSIGNED,
    cat_adult_illegal INT UNSIGNED,
    PRIMARY KEY (channel_id),
    CONSTRAINT fk_sensitive_keyword_channel
        FOREIGN KEY (channel_id) REFERENCES channel_info_table(youtube_channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE={COLLATION};

CREATE TABLE IF NOT EXISTS upload_regularity_score_table (
    channel_id VARCHAR(64) NOT NULL,
    channel_title VARCHAR(255),
    regularity_score DECIMAL(10,6),
    mean_interval_days DOUBLE,
    std_interval_days DOUBLE,
    max_gap_days DOUBLE,
    cv DOUBLE,
    outlier_ratio DECIMAL(10,6),
    gap_ratio DECIMAL(10,6),
    PRIMARY KEY (channel_id),
    CONSTRAINT fk_upload_regularity_channel
        FOREIGN KEY (channel_id) REFERENCES channel_info_table(youtube_channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE={COLLATION};

CREATE TABLE IF NOT EXISTS channel_prediction_table (
    channel_id VARCHAR(64) NOT NULL,
    title VARCHAR(255),
    churn_actual_label TINYINT,
    churn_prob_lr DECIMAL(10,6),
    churn_prob_rf DECIMAL(10,6),
    churn_prob_xgb DECIMAL(10,6),
    churn_prob DECIMAL(10,6),
    stagnation_actual_label TINYINT,
    stagnation_prob_lr DECIMAL(10,6),
    stagnation_prob_rf DECIMAL(10,6),
    stagnation_prob_xgb DECIMAL(10,6),
    stagnation_prob DECIMAL(10,6),
    volatility_actual_label TINYINT,
    volatility_prob_lr DECIMAL(10,6),
    volatility_prob_rf DECIMAL(10,6),
    volatility_prob_xgb DECIMAL(10,6),
    volatility_prob DECIMAL(10,6),
    has_churn TINYINT DEFAULT 0,
    has_stagnation TINYINT DEFAULT 0,
    has_volatility TINYINT DEFAULT 0,
    PRIMARY KEY (channel_id),
    CONSTRAINT fk_channel_prediction_channel
        FOREIGN KEY (channel_id) REFERENCES channel_info_table(youtube_channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE={COLLATION};

CREATE TABLE IF NOT EXISTS video_info_table (
    video_id VARCHAR(32) NOT NULL,
    channel_id VARCHAR(64) NOT NULL,
    channel_title VARCHAR(255),
    video_title TEXT,
    published_at DATETIME,
    duration_sec DOUBLE,
    is_shorts TINYINT,
    view_count BIGINT UNSIGNED,
    like_count BIGINT UNSIGNED,
    comment_count BIGINT UNSIGNED,
    source_file VARCHAR(255),
    channel_created_at DATETIME,
    country VARCHAR(8),
    subscriber_count BIGINT UNSIGNED,
    channel_total_views BIGINT UNSIGNED,
    total_video_count BIGINT UNSIGNED,
    PRIMARY KEY (video_id),
    INDEX idx_video_info_channel_id (channel_id),
    CONSTRAINT fk_video_info_channel
        FOREIGN KEY (channel_id) REFERENCES channel_info_table(youtube_channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE={COLLATION};
"""


def make_post_load_views_sql() -> str:
    return f"""-- Post-load EDA views
-- These views assume all existing and additional tables have been loaded.
-- Adjust category/band join keys if the physical DB uses different column names.

CREATE OR REPLACE VIEW v_channel_score_eda AS
SELECT
    ci.channel_identifier,
    ci.youtube_channel_id,
    ci.channel_name,
    av.active_viewer_score,
    av.view_per_sub,
    av.cluster_name,
    sk.sensitive_score,
    sk.n_sensitive_videos,
    sk.sensitive_video_ratio,
    ur.regularity_score,
    ur.mean_interval_days,
    ur.max_gap_days,
    cp.churn_prob,
    cp.stagnation_prob,
    cp.volatility_prob,
    cp.has_churn,
    cp.has_stagnation,
    cp.has_volatility
FROM channel_info_table ci
LEFT JOIN active_viewer_score_table av
    ON av.channel_id = ci.youtube_channel_id
LEFT JOIN sensitive_keyword_score_table sk
    ON sk.channel_id = ci.youtube_channel_id
LEFT JOIN upload_regularity_score_table ur
    ON ur.channel_id = ci.youtube_channel_id
LEFT JOIN channel_prediction_table cp
    ON cp.channel_id = ci.youtube_channel_id;

CREATE OR REPLACE VIEW v_video_activity_eda AS
SELECT
    ci.channel_identifier,
    ci.youtube_channel_id,
    vi.video_id,
    vi.video_title,
    vi.published_at,
    vi.duration_sec,
    vi.is_shorts,
    vi.view_count,
    vi.like_count,
    vi.comment_count
FROM video_info_table vi
JOIN channel_info_table ci
    ON vi.channel_id = ci.youtube_channel_id;

-- comments_table is intentionally kept independent from video_info_table
-- because the collected comment video_id may differ from video_info_table.video_id.
"""


def save_plots(
    sources: dict[str, pd.DataFrame],
    quality: pd.DataFrame,
    prediction_profile: pd.DataFrame,
    channel_prediction: pd.DataFrame,
) -> list[str]:
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans", "Arial"]
    saved = []

    source_rows = quality[["table", "expected_loaded_rows"]].rename(
        columns={"expected_loaded_rows": "rows"}
    )
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.barh(source_rows["table"], source_rows["rows"], color="#4C6A72")
    ax.set_title("전체 적재 완료 후 테이블별 예상 행 수")
    ax.set_xlabel("rows")
    for i, value in enumerate(source_rows["rows"]):
        ax.text(value, i, f" {value:,}", va="center", fontsize=9)
    fig.tight_layout()
    path = REPORT_DIR / "post_load_table_rows.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    saved.append(rel(path))

    fig, ax = plt.subplots(figsize=(10, 4.5))
    q = quality.copy()
    ax.bar(q["table"], q["fk_match_rate"], color="#6C8E5E")
    ax.set_ylim(0, 105)
    ax.set_title("channel_info_table FK 매칭률")
    ax.set_ylabel("match rate (%)")
    ax.tick_params(axis="x", rotation=25)
    for i, value in enumerate(q["fk_match_rate"]):
        ax.text(i, value, f"{value:.1f}%", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    path = REPORT_DIR / "post_load_fk_coverage.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    saved.append(rel(path))

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(
        prediction_profile["metric"],
        prediction_profile["rows"],
        color=["#557A95", "#8E7C5E", "#7A6C95", "#B95C50"],
    )
    ax.set_title("channel_prediction_table 병합 커버리지")
    ax.set_ylabel("rows")
    ax.tick_params(axis="x", rotation=20)
    for i, value in enumerate(prediction_profile["rows"]):
        ax.text(i, value, f"{value:,}", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    path = REPORT_DIR / "post_load_prediction_coverage.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    saved.append(rel(path))

    score_series = [
        ("active_viewer_score", sources["active_viewer_score"]["active_viewer_score"]),
        ("sensitive_score", sources["sensitive_keyword_score"]["sensitive_score"]),
        ("regularity_score", sources["upload_regularity_score"]["regularity_score"]),
        ("churn_prob", channel_prediction["churn_prob"]),
        ("stagnation_prob", channel_prediction["stagnation_prob"]),
        ("volatility_prob", channel_prediction["volatility_prob"]),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(12, 7))
    for ax, (name, series) in zip(axes.ravel(), score_series):
        ax.hist(series.dropna(), bins=30, color="#557A95", edgecolor="white")
        ax.set_title(name)
    fig.tight_layout()
    path = REPORT_DIR / "post_load_score_distributions.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    saved.append(rel(path))

    videos = sources["filtered_dataset_long"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    videos["is_shorts"].value_counts(dropna=False).plot(
        kind="bar", ax=axes[0], color="#8E7C5E"
    )
    axes[0].set_title("video_info_table is_shorts 분포")
    capped = videos["view_count"].clip(upper=videos["view_count"].quantile(0.99))
    capped.hist(bins=40, ax=axes[1], color="#5E6C8E")
    axes[1].set_title("video_info_table view_count 분포 (p99 cap)")
    fig.tight_layout()
    path = REPORT_DIR / "post_load_video_info_profile.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    saved.append(rel(path))

    return saved


def make_report(
    source_inv: pd.DataFrame,
    quality: pd.DataFrame,
    prediction_profile: pd.DataFrame,
    comment_summary: pd.DataFrame,
    column_profile: pd.DataFrame,
    plots: list[str],
) -> str:
    existing = pd.DataFrame(EXISTING_DB_TABLES)
    planned = pd.DataFrame(PLANNED_DB_TABLES)
    marts = pd.DataFrame(POST_LOAD_EDA_MARTS)
    decisions = pd.DataFrame(DESIGN_DECISIONS)
    schema = db_column_schema_df()

    lines = [
        "# 전체 DB 적재 완료 후 EDA 구성",
        "",
        f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 신규 테이블 기본 collation: `{COLLATION}`",
        "- 기준: 기존 적재 완료 테이블 + 추가 적재 테이블이 모두 적재된 이후의 DB",
        "",
        "## 결론",
        "",
        "- 최종 EDA는 `channel_info_table`을 허브로 두고 점수/예측/영상 테이블을 붙이는 구조가 가장 안정적입니다.",
        "- 채널 단위 핵심 EDA 뷰는 `v_channel_score_eda`입니다. 여기서 활성 시청자, 민감도, 업로드 규칙성, 3종 예측 확률을 한 번에 봅니다.",
        "- 카테고리/구독자 밴드 분석은 `v_channel_score_eda`를 `category_table`, `channel_category_table`, `band_table`과 집계하는 방식으로 구성합니다.",
        "- `video_info_table`은 영상 단위 시계열/Shorts/조회수 EDA에 사용하고, `comments_table`과는 FK를 만들지 않습니다.",
        "- `filtered_dataset_wide.csv`는 최종 DB에 별도 적재하지 않고, 적재 완료 후 EDA에서는 `channel_info_table`과 신규 점수 테이블 조합으로 대체합니다.",
        "",
        "## 최종 DB 테이블 구성",
        "",
        md_table(existing),
        "",
        "## 추가 적재 후 포함 테이블",
        "",
        md_table(planned),
        "",
        "## 적재 완료 후 EDA 뷰 구성",
        "",
        md_table(marts),
        "",
        "## 주요 설계 결정사항",
        "",
        md_table(decisions),
        "",
        "## 원본 파일 인벤토리",
        "",
        md_table(source_inv),
        "",
        "## 적재 완료 후 예상 커버리지",
        "",
        md_table(quality),
        "",
        "## channel_prediction_table 병합 프로필",
        "",
        md_table(prediction_profile),
        "",
        "## 댓글 파일 참고 요약",
        "",
        "댓글은 이미 `comments_table`에 적재된 기존 테이블로 보고, 신규 `video_info_table`과 직접 연결하지 않습니다.",
        "",
        md_table(comment_summary),
        "",
        "## DB 컬럼 스키마",
        "",
        md_table(schema),
        "",
        "## 컬럼 프로파일 요약",
        "",
        md_table(column_profile.head(80)),
        "",
        "## 생성된 그래프",
        "",
        "\n".join(f"- `{p}`" for p in plots),
        "",
        "## 생성된 SQL",
        "",
        "- `reports/eda/post_load_new_tables_schema.sql`",
        "- `reports/eda/post_load_eda_views.sql`",
        "",
    ]
    return "\n".join(lines)


def make_schema_markdown() -> str:
    return "\n".join(
        [
            "# 전체 DB 적재 완료 후 EDA 스키마",
            "",
            "기존 적재 완료 테이블과 추가 적재 테이블이 모두 적재된 이후를 기준으로 재구성한 EDA 스키마입니다.",
            "",
            "## 최종 DB 기존 테이블",
            "",
            md_table(pd.DataFrame(EXISTING_DB_TABLES)),
            "",
            "## 추가 적재 후 포함 테이블",
            "",
            md_table(pd.DataFrame(PLANNED_DB_TABLES)),
            "",
            "## 적재 완료 후 EDA 뷰",
            "",
            md_table(pd.DataFrame(POST_LOAD_EDA_MARTS)),
            "",
            "## 설계 결정사항",
            "",
            md_table(pd.DataFrame(DESIGN_DECISIONS)),
            "",
            "## 컬럼 스키마",
            "",
            md_table(db_column_schema_df()),
            "",
        ]
    )


def write_notebook() -> None:
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# 전체 DB 적재 완료 후 EDA\n",
                "\n",
                "기존 적재 완료 테이블과 추가 적재 테이블이 모두 DB에 들어간 이후를 기준으로 EDA 구성을 점검합니다.\n",
                "`make_core_tables_eda.py`를 실행하면 `reports/eda`가 post-load DB EDA 산출물로 재구성됩니다.\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from pathlib import Path\n",
                "import pandas as pd\n",
                "\n",
                "ROOT = Path.cwd().resolve()\n",
                "while not (ROOT / 'pyproject.toml').exists() and ROOT != ROOT.parent:\n",
                "    ROOT = ROOT.parent\n",
                "REPORT_DIR = ROOT / 'reports' / 'eda'\n",
                "REPORT_DIR\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import runpy\n",
                "runpy.run_path(ROOT / 'notebooks' / '02_eda' / 'make_core_tables_eda.py', run_name='__main__')\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## 산출물 확인\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": ["pd.read_csv(REPORT_DIR / 'post_load_db_tables.csv')\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": ["pd.read_csv(REPORT_DIR / 'post_load_expected_coverage.csv')\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": ["pd.read_csv(REPORT_DIR / 'post_load_eda_marts.csv')\n"],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## 직접 탐색용 로드\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "raw = ROOT / 'data' / 'raw'\n",
                "active = pd.read_csv(raw / 'active_viewer_score.csv')\n",
                "sensitive = pd.read_csv(raw / 'sensitive_keyword_score.csv')\n",
                "regularity = pd.read_csv(raw / 'upload_regularity_score.csv')\n",
                "videos = pd.read_csv(raw / 'filtered_dataset_long.csv')\n",
                "active.shape, sensitive.shape, regularity.shape, videos.shape\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "pd.read_csv(REPORT_DIR / 'post_load_column_schema.csv').head(30)\n",
            ],
        },
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)
    clean_report_dir()

    sources = load_sources()
    channel_prediction = build_channel_prediction(sources)
    channel_info_ids = set(sources["channel_info_source"]["youtube_channel_id"].dropna().astype(str))
    channel_prediction_loadable = channel_prediction[
        channel_prediction["channel_id"].astype(str).isin(channel_info_ids)
    ].copy()
    source_inv = source_inventory()
    quality = db_load_quality_checks(sources, channel_prediction)
    prediction_profile = channel_prediction_merge_profile(channel_prediction, channel_info_ids)
    comments = comment_file_summary()
    columns = column_profile_for_planned_tables(sources, channel_prediction)

    plots = save_plots(sources, quality, prediction_profile, channel_prediction)

    post_load_tables = pd.concat(
        [
            pd.DataFrame(EXISTING_DB_TABLES).assign(group="existing_loaded"),
            pd.DataFrame(PLANNED_DB_TABLES)
            .rename(columns={"primary_key": "key", "description": "description"})
            .assign(status="loaded_after_ingest", group="additional_loaded")[
                ["table", "status", "key", "description", "group"]
            ],
        ],
        ignore_index=True,
    )
    post_load_tables.to_csv(
        REPORT_DIR / "post_load_db_tables.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(EXISTING_DB_TABLES).to_csv(
        REPORT_DIR / "post_load_existing_tables.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(PLANNED_DB_TABLES).to_csv(
        REPORT_DIR / "post_load_additional_tables.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(POST_LOAD_EDA_MARTS).to_csv(
        REPORT_DIR / "post_load_eda_marts.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(DESIGN_DECISIONS).to_csv(
        REPORT_DIR / "post_load_design_decisions.csv", index=False, encoding="utf-8-sig"
    )
    db_column_schema_df().to_csv(
        REPORT_DIR / "post_load_column_schema.csv", index=False, encoding="utf-8-sig"
    )
    source_inv.to_csv(REPORT_DIR / "post_load_source_inventory.csv", index=False, encoding="utf-8-sig")
    quality.to_csv(REPORT_DIR / "post_load_expected_coverage.csv", index=False, encoding="utf-8-sig")
    prediction_profile.to_csv(
        REPORT_DIR / "post_load_prediction_coverage.csv",
        index=False,
        encoding="utf-8-sig",
    )
    comments.to_csv(REPORT_DIR / "comment_file_summary.csv", index=False, encoding="utf-8-sig")
    columns.to_csv(REPORT_DIR / "post_load_column_profile.csv", index=False, encoding="utf-8-sig")
    channel_prediction_loadable.head(200).to_csv(
        REPORT_DIR / "channel_prediction_table_preview.csv",
        index=False,
        encoding="utf-8-sig",
    )

    report = make_report(source_inv, quality, prediction_profile, comments, columns, plots)
    (REPORT_DIR / "post_load_eda_report.md").write_text(report, encoding="utf-8")
    (REPORT_DIR / "post_load_db_schema.md").write_text(make_schema_markdown(), encoding="utf-8")
    (REPORT_DIR / "post_load_new_tables_schema.sql").write_text(make_ddl(), encoding="utf-8")
    (REPORT_DIR / "post_load_eda_views.sql").write_text(make_post_load_views_sql(), encoding="utf-8")
    DOCS_SCHEMA_PATH.write_text(make_schema_markdown(), encoding="utf-8")
    write_notebook()

    print("Generated post-load DB EDA artifacts:")
    for path in sorted(REPORT_DIR.iterdir()):
        if path.is_file():
            print(f"- {rel(path)}")
    print(f"- {rel(NOTEBOOK_PATH)}")
    print(f"- {rel(DOCS_SCHEMA_PATH)}")


if __name__ == "__main__":
    main()
