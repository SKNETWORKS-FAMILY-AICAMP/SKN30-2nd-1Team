# notebooks/02_modeling — 현재 Feature 정리 및 진행 상황

## 1. 전체 파이프라인 한눈에 보기

```
[01_data_collection]                  [02_modeling — 6 노트북]                   [risk_calculation.ipynb]
youtube_channels.csv      ──▶  ┌─ churn_probability_model        ──▶ churn_prob              ─┐
videos/channels/comments  ──▶  ├─ stagnation_probability_model   ──▶ stagnation_prob         ─┤
dataset_wide.csv          ──▶  ├─ view_volatility_model          ──▶ volatility_prob         ─┼─▶ risk_df (8 columns)
dataset_long.csv          ──▶  ├─ upload_regularity_score        ──▶ regularity_score        ─┤    → 최종 위험도 ABCDF
filtered_dataset_*        ──▶  ├─ sensitive_keyword_score        ──▶ sensitive_score         ─┤
                               └─ active_viewer_score            ──▶ active_viewer_score     ─┘
```

위험도 가중치 (`risk_calculation.ipynb` 첫 셀에 명시):

```
최종 위험도 (ABCDF)
├── 평판 위험도 33%    : 민감 키워드 매칭도
├── 트래픽 위험도 33%  : 이탈 확률 + 정체 확률 + 조회수 변동성 + 업로드 주기 불확실성
└── 팬덤 위험도 33%    : 활성 시청자 비율
```

---

## 2. 노트북별 Feature / 산출물 정리

### 2-1. `churn_probability_model.ipynb` — 이탈 확률
- **출력 컬럼**: `churn_prob` (0~1)
- **출력 파일**: `data/raw/churn_probability_output.csv`
- **입력 데이터**: `dataset_wide.csv` (채널 단위) + `dataset_long.csv` (영상 시계열)
- **라벨 정의**: `days_since_last_upload >= 180일` → `is_churned = 1`
- **사용 피처 (22개 가량)**:
  - 채널 규모: `subscriber_count`, `view_count`, `total_video_count`, `channel_age_days`
  - 활동성: `collected_video_count`, `avg_upload_interval_days`, `std_upload_interval_days`, `max_gap_days`, `hiatus_count_30d`, `upload_freq_change_rate`
  - 성과: `avg_view_count`, `std_view_count`, `avg_like_count`, `avg_comment_count`, `avg_engagement_rate`
  - Shorts: `shorts_ratio`, `avg_shorts_view`, `avg_normal_view`
  - long 파생: `upload_slope`, `recent_3m_upload_count`, `recent_view_ratio`, `days_between_last2`
- **제외 피처**: `days_since_last_upload` (데이터 리크), `channel_id` / `title` / `source_file` (ID·텍스트), `published_at` (→ `channel_age_days`로 변환), `country` (희소 범주)
- **모델**: LogisticRegression + RandomForest + XGBoost 앙상블 평균 (`prob_lr`, `prob_rf`, `prob_xgb` → `churn_prob`)

### 2-2. `stagnation_probability_model.ipynb` — 정체 확률
- **출력 컬럼**: `stagnation_prob`
- **출력 파일**: `data/raw/stagnation_probability_output.csv`
- **입력 데이터**: `filtered_dataset_long.csv` (최신 영상 1개 제외 — 조회수 미성숙)
- **라벨 정의**: `log_slope < -0.005` **AND** `change_rate_half < -0.1` → `is_stagnant = 1`
- **사용 피처 (8개)**: `log_slope`, `r_squared`, `change_rate_half`, `recent10_vs_all`, `view_cv`, `pct_below_median`, `momentum_3`, `trend_accel`
- **모델**: LR + RF + XGB 앙상블

### 2-3. `view_volatility_model.ipynb` — 조회수 변동성
- **출력 컬럼**: `volatility_prob`
- **출력 파일**: `data/raw/view_volatility_output.csv`
- **입력 데이터**: `filtered_dataset_long.csv` (최신 1개 제외)
- **라벨 정의**: `log_view_std > 중앙값` **AND** `mad_to_median > 중앙값` → `is_volatile = 1`
- **사용 피처 (8개)**: `view_cv`, `log_view_std`, `mad_to_median`, `iqr_to_median`, `range_to_median`, `outlier_ratio`, `spike_ratio`, `pct_change_std`
- **모델**: LR + RF + XGB 앙상블

### 2-4. `upload_regularity_score.ipynb` — 업로드 규칙성 (룰 기반)
- **출력 컬럼**: `regularity_score` (0~1, **높을수록 안정적**)
- **출력 파일**: `data/raw/upload_regularity_score.csv`
- **입력 데이터**: `filtered_dataset_long.csv`
- **사용 피처**: `mean_interval_days`, `std_interval_days`, `max_gap_days`, `cv`, `outlier_ratio`, `gap_ratio`
- **수식**: `CV 안정성(50%) + 이상치 안정성(30%) + 최대공백 패널티(20%)`![alt text](image.png)
- **ML 미사용** — 규칙 기반 점수
- **위험도 합산 시 주의**: 다른 점수와 방향이 반대(높을수록 좋음). 트래픽 위험도에 더할 때 `(1 - regularity_score)`로 뒤집어야 함.

### 2-5. `sensitive_keyword_score.ipynb` — 민감 키워드 매칭 (룰 기반)
- **출력 컬럼**: `sensitive_score`, `n_sensitive_videos`, `sensitive_video_ratio`, `cat_politics`, `cat_hate`, `cat_aggro`, `cat_adult_illegal`
- **출력 파일**: `data/raw/sensitive_keyword_score.csv`
- **입력 데이터**: `filtered_dataset_long.csv` (영상 제목 사용)
- **사용 피처**: 62개 민감 키워드 사전 — 정치/사회(3점), 혐오/차별(3점), 자극/어그로(1~3점), 성인·도박·불법(3점), 오탐 감점(-1점)
- **정규화**: `raw_score / (영상수 × 3)`, 0~1 클립
- **ML 미사용** — 키워드 매칭 기반

### 2-6. `active_viewer_score.ipynb` — 활성 시청자 (KMeans 군집)
- **출력 컬럼**: `active_viewer_score`, `cluster`, `cluster_name`, `avg_view_count`, `view_per_sub`
- **출력 파일**: `data/raw/active_viewer_score.csv`
- **입력 데이터**: `filtered_dataset_wide.csv`
- **사용 피처**: `view_per_sub`(조회수/구독자), `like_per_view`, `comment_per_view` — 로그 스케일 + StandardScaler
- **모델**: K-Means (K=4) — 군집 4개: `슈퍼팬(0.85)` / `일반팬(0.60)` / `소극적팬(0.35)` / `유령팬(0.15)`
- **점수화**: 군집 기준점수 + log_vps 보정(±0.1) + 참여율 보정(±0.05)
- **위험도 합산 시 주의**: 높을수록 건강 → 팬덤 위험도에는 `(1 - active_viewer_score)`로 뒤집어야 함.

### 2-7. `risk_calculation.ipynb` — 통합 (현재 작업 중)
- 위 6개 CSV를 `channel_id` 기준으로 outer join → `risk_df` 생성
- 최종 컬럼 8개: `channel_id`, `channel_title`, `sensitive_score`, `churn_prob`, `stagnation_prob`, `volatility_prob`, `regularity_score`, `active_viewer_score`
- 현재 상태: **데이터 병합 단계까지만 진행**, ABCDF 등급화·가중 합산은 아직 미구현
- 행 수: 3,336 채널 (sensitive_keyword 기준 필터링 후)

---

## 3. 지금까지 알아야 할 핵심 포인트

### 3-1. 데이터 분기 구조
- **wide**: 채널 1행 단위 (집계 피처) — `dataset_wide.csv`, `filtered_dataset_wide.csv`
- **long**: 영상 1행 단위 (시계열) — `dataset_long.csv`, `filtered_dataset_long.csv`
- 시계열 기반 모델들(정체/변동성/규칙성)은 모두 **최신 1개 영상 제외**한 `filtered_dataset_long.csv` 사용 (조회수 미성숙 보정)
- `sensitive_keyword_score.csv`의 `channel_id` 집합을 기준 마스터로 사용 (3,336개)

### 3-2. 피처 그룹 (feature_description.md 기준)
- **그룹 0** 채널 기본정보: `subscriber_count`, `view_count`, `total_video_count`, `channel_age_days` 등
- **그룹 A** 활동성: 업로드 빈도/규칙성/공백 관련
- **그룹 B** 성과: 조회·좋아요·댓글·engagement
- **그룹 C** Shorts: 비율 + 평균 조회수

### 3-3. 데이터 리크·이상값 주의
- `days_since_last_upload`는 이탈 라벨 생성에 사용 → 학습 피처에서 **반드시 제외**
- `upload_freq_change_rate`: 분모 0 가능 → `clip(-5, 5)`
- `avg_engagement_rate`: 조회수 0 근처에서 폭주 → `clip(0, 1)`

### 3-4. 점수 방향성 통일 (위험도 합산 시 필수)
| 컬럼 | 방향 | 위험도로 변환 |
|---|---|---|
| `churn_prob` | 높을수록 위험 | 그대로 |
| `stagnation_prob` | 높을수록 위험 | 그대로 |
| `volatility_prob` | 높을수록 위험 | 그대로 |
| `sensitive_score` | 높을수록 위험 | 그대로 |
| `regularity_score` | **높을수록 안전** | `1 - score` |
| `active_viewer_score` | **높을수록 안전** | `1 - score` |

### 3-5. 다음에 해야 할 일 (risk_calculation 미완성 부분)
1. `regularity_score`, `active_viewer_score` 방향 뒤집기
2. 3개 카테고리(평판/트래픽/팬덤) 가중 합산 → 최종 위험도 산출
3. ABCDF 5단계 등급화 (분포 기반 컷오프 또는 KMeans)
4. `risk_ranking.csv` 저장 형식 결정 (이미 `data/raw/risk_ranking.csv` 존재 — 확인 필요)

---

## Critical Files (참고)
- [feature_description.md](../feature_description.md) — 그룹 0/A/B/C 피처 설계 문서
- [notebooks/02_modeling/risk_calculation.ipynb](../notebooks/02_modeling/risk_calculation.ipynb) — 통합 노트북 (미완성)
- [notebooks/02_modeling/churn_probability_model.ipynb](../notebooks/02_modeling/churn_probability_model.ipynb)
- [notebooks/02_modeling/stagnation_probability_model.ipynb](../notebooks/02_modeling/stagnation_probability_model.ipynb)
- [notebooks/02_modeling/view_volatility_model.ipynb](../notebooks/02_modeling/view_volatility_model.ipynb)
- [notebooks/02_modeling/upload_regularity_score.ipynb](../notebooks/02_modeling/upload_regularity_score.ipynb)
- [notebooks/02_modeling/sensitive_keyword_score.ipynb](../notebooks/02_modeling/sensitive_keyword_score.ipynb)
- [notebooks/02_modeling/active_viewer_score.ipynb](../notebooks/02_modeling/active_viewer_score.ipynb)
