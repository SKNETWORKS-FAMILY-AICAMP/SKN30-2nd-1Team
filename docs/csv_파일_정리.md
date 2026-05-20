# `data/raw/` CSV 파일 정리

현재 `data/raw/` 폴더에 있는 CSV 파일별 출처·생성 방법·주요 컬럼 정리.

---

## 1. 원천(raw) 채널 목록 — 외부 수집/크롤링

| 파일 | 행수 | 생성 출처 | 핵심 컬럼 |
|---|---|---|---|
| `youtube_channels.csv` | 9,427 | 외부에서 수집한 초기 채널 목록 (구독자/카테고리 등) | `channel_name`, `category`, `subscriber_count`, `total_views`, `video_count`, `created_date`, `latest_video_date`, `days_since_latest_video`, `is_churned`, `youtube_channel_id` |
| `youtube_channels_cleaned.csv` | 8,193 | `youtube_channels.csv`를 정제 (결측·잘못된 URL 제거 등) | 위와 동일 |
| `youtube_channels_filtered.csv` | 3,353 | `youtube_channels_cleaned.csv`를 분석 대상으로 필터링 (`channel_identifier` 추가) | 위 + `channel_identifier` |

---

## 2. 가공된 데이터셋 — YouTube API 수집 + 집계

| 파일 | 행수 | 생성 출처 | 핵심 컬럼 |
|---|---|---|---|
| `dataset_wide.csv` | 8,084 | `01_data_collection`에서 API로 채널·영상 수집 후 **채널 단위 집계** | 채널 정보 + 활동성(`avg_upload_interval_days`, `max_gap_days` 등) + 성과(`avg_view_count`, `avg_like_count` 등) + Shorts(`shorts_ratio`) |
| `filtered_dataset_wide.csv` | 3,337 | `dataset_wide.csv`를 `dataset_filtering.ipynb`로 분석 대상만 필터링 | wide와 동일 |
| `filtered_dataset_long.csv` | 166,450 | 영상 단위 시계열 데이터, **최신 1개 영상 제외** (조회수 미성숙) | `video_id`, `video_title`, `published_at`, `duration_sec`, `is_shorts`, `view_count`, `like_count`, `comment_count` |

> 시계열 기반 모델(정체/변동성/규칙성)은 모두 `filtered_dataset_long.csv` 사용.

---

## 3. 모델 출력 점수 — `notebooks/02_modeling` 결과

| 파일 | 행수 | 생성 노트북 | 핵심 컬럼 |
|---|---|---|---|
| `churn_probability_output.csv` | 8,084 | `churn_probability_model.ipynb` (LR+RF+XGB 앙상블) | `actual_label`, `prob_lr`, `prob_rf`, `prob_xgb`, **`churn_prob`** |
| `stagnation_probability_output.csv` | 3,334 | `stagnation_probability_model.ipynb` (LR+RF+XGB 앙상블) | `prob_lr`, `prob_rf`, `prob_xgb`, **`stagnation_prob`** |
| `view_volatility_output.csv` | 3,334 | `view_volatility_model.ipynb` (LR+RF+XGB 앙상블) | `prob_lr`, `prob_rf`, `prob_xgb`, **`volatility_prob`** |
| `upload_regularity_score.csv` | 3,334 | `upload_regularity_score.ipynb` (룰 기반) | **`regularity_score`**, `mean_interval_days`, `std_interval_days`, `max_gap_days`, `cv`, `outlier_ratio`, `gap_ratio` |
| `sensitive_keyword_score.csv` | 3,337 | `sensitive_keyword_score.ipynb` (62개 키워드 매칭) | **`sensitive_score`**, `n_sensitive_videos`, `sensitive_video_ratio`, `cat_politics`, `cat_hate`, `cat_aggro`, `cat_adult_illegal` |
| `active_viewer_score.csv` | 3,337 | `active_viewer_score.ipynb` (KMeans K=4) | `subscriber_count`, `avg_view_count`, `view_per_sub`, `cluster`, `cluster_name`(슈퍼팬/일반팬/소극적팬/유령팬), **`active_viewer_score`** |

---

## 4. 최종 통합 결과

| 파일 | 행수 | 생성 노트북 | 핵심 컬럼 |
|---|---|---|---|
| `risk_ranking.csv` | 3,337 | `risk_calculation.ipynb` — 6개 점수 채널별 outer join + 가중 합산 | `sensitive_score`, `churn_prob`, `stagnation_prob`, `volatility_prob`, `regularity_score`, `active_viewer_score`, **`traffic_risk`, `reputation_risk`, `fandom_risk`, `risk`, `rank`** |

> **참고**: `risk_ranking.csv`에 이미 `traffic_risk`/`reputation_risk`/`fandom_risk`/`risk`/`rank` 컬럼이 존재합니다 — 일부 가중합산은 이미 진행됐고, ABCDF 등급화는 아직 미구현입니다.

---

## 파이프라인 흐름

```
youtube_channels.csv          (외부 수집)
  ↓ 정제
youtube_channels_cleaned.csv
  ↓ 필터링
youtube_channels_filtered.csv
  ↓ API 영상 수집 + 집계
dataset_wide.csv  ←→  (filtered_dataset_long.csv: 영상 시계열)
  ↓ 분석 대상 필터링 (dataset_filtering.ipynb)
filtered_dataset_wide.csv
  ↓ 6개 모델/스코어 노트북
churn_prob / stagnation_prob / volatility_prob /
regularity_score / sensitive_score / active_viewer_score
  ↓ risk_calculation.ipynb로 통합
risk_ranking.csv  ← 최종 산출물
```

---

## 행수 차이 정리

- **9,427 → 8,193 → 3,353**: 외부 수집 데이터의 정제·필터링 단계
- **8,084**: API 수집 성공한 채널 (wide / churn_probability_output)
- **3,337**: 분석 대상 필터링 후 채널 수 (filtered_wide, sensitive_keyword, active_viewer, risk_ranking)
- **3,334**: 영상이 충분히 있어 시계열 분석 가능한 채널 (stagnation, volatility, regularity)
- **166,450**: filtered_dataset_long의 영상 단위 행수
