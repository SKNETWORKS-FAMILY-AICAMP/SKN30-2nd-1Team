# 전체 DB 적재 완료 후 EDA 구성

- 생성 시각: 2026-05-20 21:40:34
- 신규 테이블 기본 collation: `utf8mb4_unicode_ci`
- 기준: 기존 적재 완료 테이블 + 추가 적재 테이블이 모두 적재된 이후의 DB

## 결론

- 최종 EDA는 `channel_info_table`을 허브로 두고 점수/예측/영상 테이블을 붙이는 구조가 가장 안정적입니다.
- 채널 단위 핵심 EDA 뷰는 `v_channel_score_eda`입니다. 여기서 활성 시청자, 민감도, 업로드 규칙성, 3종 예측 확률을 한 번에 봅니다.
- 카테고리/구독자 밴드 분석은 `v_channel_score_eda`를 `category_table`, `channel_category_table`, `band_table`과 집계하는 방식으로 구성합니다.
- `video_info_table`은 영상 단위 시계열/Shorts/조회수 EDA에 사용하고, `comments_table`과는 FK를 만들지 않습니다.
- `filtered_dataset_wide.csv`는 최종 DB에 별도 적재하지 않고, 적재 완료 후 EDA에서는 `channel_info_table`과 신규 점수 테이블 조합으로 대체합니다.

## 최종 DB 테이블 구성

| table | status | key | description |
| --- | --- | --- | --- |
| channel_info_table | loaded | PK: channel_identifier | 채널 기본 정보. 추가 적재 테이블은 youtube_channel_id를 FK 기준으로 사용 |
| category_table | loaded | category key | 카테고리 정보 |
| channel_category_table | loaded | channel-category bridge | 채널-카테고리 중간 테이블 |
| band_table | loaded | band key | 구독자 범위 구간 정보 |
| comments_table | loaded | comment key | 댓글 데이터. video_info_table과 video_id가 다를 수 있어 연결하지 않음 |

## 추가 적재 후 포함 테이블

| table | source | load_strategy | primary_key | foreign_key | description |
| --- | --- | --- | --- | --- | --- |
| active_viewer_score_table | data/raw/active_viewer_score.csv | channel_id 기준 1:1 적재 | channel_id | channel_id -> channel_info_table.youtube_channel_id | 활성 시청자 점수 |
| sensitive_keyword_score_table | data/raw/sensitive_keyword_score.csv | channel_id 기준 1:1 적재 | channel_id | channel_id -> channel_info_table.youtube_channel_id | 민감 키워드/위험도 점수 |
| upload_regularity_score_table | data/raw/upload_regularity_score.csv | channel_id 기준 1:1 적재 | channel_id | channel_id -> channel_info_table.youtube_channel_id | 업로드 규칙성 점수 |
| channel_prediction_table | churn_probability_output.csv + view_volatility_output.csv + stagnation_probability_output.csv | 3개 예측 결과를 channel_id 기준 outer merge 후 channel_info_table FK 가능 행만 적재 | channel_id | channel_id -> channel_info_table.youtube_channel_id | 모델 예측 결과 통합 테이블 |
| video_info_table | data/raw/filtered_dataset_long.csv | video_id 기준 영상 단위 적재 | video_id | channel_id -> channel_info_table.youtube_channel_id | 영상 단위 원본 데이터 |

## 적재 완료 후 EDA 뷰 구성

| eda_view | grain | base_tables | purpose |
| --- | --- | --- | --- |
| v_channel_score_eda | 채널 1개 | channel_info_table + active_viewer_score_table + sensitive_keyword_score_table + upload_regularity_score_table + channel_prediction_table | 채널별 활성 시청자, 민감 키워드, 업로드 규칙성, 3종 예측 확률을 한 번에 보는 핵심 EDA 뷰 |
| v_category_score_eda | 카테고리 x 채널 | category_table + channel_category_table + v_channel_score_eda | 카테고리별 위험/활성/민감도 분포 비교 |
| v_band_score_eda | 구독자 밴드 x 채널 | band_table + channel_info_table + v_channel_score_eda | 구독자 규모 구간별 위험/예측 점수 분포 비교 |
| v_video_activity_eda | 영상 1개 | video_info_table + channel_info_table | 영상 업로드 시계열, Shorts 비율, 조회/좋아요/댓글 분포 분석 |
| v_comment_community_eda | 댓글 1개 | comments_table | 댓글 수, 작성 시점, 좋아요, 작성자/대댓글 구조 분석. video_info_table과는 FK 연결하지 않음 |
| v_prediction_model_eda | 채널 1개 | channel_prediction_table + channel_info_table | churn/stagnation/volatility 예측 확률 간 상관, 결측, 모델 커버리지 분석 |

## 주요 설계 결정사항

| decision | detail |
| --- | --- |
| FK 기준 | CSV의 channel_id는 유튜브 난수값이며 channel_info_table.youtube_channel_id에 연결한다. |
| filtered_dataset_wide 스킵 | 채널 단위 wide 피처는 channel_info_table과 역할이 중복되어 별도 테이블로 적재하지 않는다. |
| 댓글-영상 미연결 | video_info_table과 comments_table은 video_id가 다를 수 있어 FK를 만들지 않는다. |
| 예측 결과 통합 | churn, volatility, stagnation 결과는 channel_prediction_table 하나로 합친다. |
| EDA 기준 시점 | 아래 산출물은 기존 테이블과 추가 적재 테이블이 모두 적재 완료된 이후의 DB를 기준으로 구성한다. |
| 인코딩/정렬 | 신규 테이블은 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 기준으로 생성한다. |

## 원본 파일 인벤토리

| source_name | path | exists | rows | cols | size_mb | key_column | description |
| --- | --- | --- | --- | --- | --- | --- | --- |
| channel_info_source | data/raw/youtube_channels_filtered.csv | True | 3352 | 15 | 0.715 | youtube_channel_id | 기존 DB channel_info_table 기준 소스 |
| active_viewer_score | data/raw/active_viewer_score.csv | True | 3336 | 8 | 0.354 | channel_id | 활성 시청자 점수 |
| sensitive_keyword_score | data/raw/sensitive_keyword_score.csv | True | 3336 | 9 | 0.203 | channel_id | 민감 키워드/위험도 점수 |
| upload_regularity_score | data/raw/upload_regularity_score.csv | True | 3333 | 9 | 0.26 | channel_id | 업로드 규칙성 점수 |
| churn_probability_output | data/raw/churn_probability_output.csv | True | 8083 | 7 | 0.517 | channel_id | 이탈 확률 모델 결과 |
| stagnation_probability_output | data/raw/stagnation_probability_output.csv | True | 3333 | 7 | 0.215 | channel_id | 정체 확률 모델 결과 |
| view_volatility_output | data/raw/view_volatility_output.csv | True | 3333 | 7 | 0.213 | channel_id | 조회수 변동성 모델 결과 |
| filtered_dataset_long | data/raw/filtered_dataset_long.csv | True | 166449 | 18 | 45.162 | video_id | 영상 단위 원본 데이터 |
| filtered_dataset_wide | data/raw/filtered_dataset_wide.csv | True | 3336 | 22 | 0.681 | channel_id | channel_info_table과 중복되어 적재 스킵 |

## 적재 완료 후 예상 커버리지

| table | source | source_rows | expected_loaded_rows | load_policy | key | null_key_rows | duplicate_key_rows | unique_keys | fk_matched_rows | fk_unmatched_rows | fk_match_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| active_viewer_score_table | data/raw/active_viewer_score.csv | 3336 | 3336 | load_all | channel_id | 0 | 0 | 3336 | 3336 | 0 | 100.0 |
| sensitive_keyword_score_table | data/raw/sensitive_keyword_score.csv | 3336 | 3336 | load_all | channel_id | 0 | 0 | 3336 | 3336 | 0 | 100.0 |
| upload_regularity_score_table | data/raw/upload_regularity_score.csv | 3333 | 3333 | load_all | channel_id | 0 | 0 | 3333 | 3333 | 0 | 100.0 |
| video_info_table | data/raw/filtered_dataset_long.csv | 166449 | 166449 | load_all | video_id | 0 | 0 | 166449 | 166449 | 0 | 100.0 |
| channel_prediction_table | 3 prediction CSV outer merge | 8083 | 3336 | filter_fk_matched_only | channel_id | 0 | 0 | 8083 | 3336 | 4747 | 41.272 |

## channel_prediction_table 병합 프로필

| metric | rows | pct_of_prediction_table |
| --- | --- | --- |
| outer merged prediction rows | 8083 | 100.0 |
| FK-compatible prediction rows | 3336 | 41.272 |
| churn only/coverage | 8083 | 100.0 |
| stagnation coverage | 3333 | 41.235 |
| volatility coverage | 3333 | 41.235 |
| all three predictions present | 3333 | 41.235 |

## 댓글 파일 참고 요약

댓글은 이미 `comments_table`에 적재된 기존 테이블로 보고, 신규 `video_info_table`과 직접 연결하지 않습니다.

| band | files | non_empty_files | comment_rows |
| --- | --- | --- | --- |
| band_A | 540 | 515 | 16615 |
| band_B | 560 | 536 | 19861 |
| band_C | 590 | 579 | 21437 |
| band_D | 591 | 531 | 22024 |

## DB 컬럼 스키마

| table | column | db_type | key_role | description |
| --- | --- | --- | --- | --- |
| active_viewer_score_table | channel_id | VARCHAR(64) | PK, FK | source channel_id |
| active_viewer_score_table | title | VARCHAR(255) |  | 채널명 |
| active_viewer_score_table | subscriber_count | BIGINT UNSIGNED |  | 구독자 수 |
| active_viewer_score_table | avg_view_count | DOUBLE |  | 평균 조회수 |
| active_viewer_score_table | view_per_sub | DOUBLE |  | 구독자 대비 조회수 |
| active_viewer_score_table | cluster | TINYINT |  | KMeans cluster |
| active_viewer_score_table | cluster_name | VARCHAR(50) |  | 클러스터명 |
| active_viewer_score_table | active_viewer_score | DECIMAL(10,6) |  | 활성 시청자 점수 |
| sensitive_keyword_score_table | channel_id | VARCHAR(64) | PK, FK | source channel_id |
| sensitive_keyword_score_table | channel_title | VARCHAR(255) |  | 채널명 |
| sensitive_keyword_score_table | sensitive_score | DECIMAL(10,6) |  | 민감 키워드 점수 |
| sensitive_keyword_score_table | n_sensitive_videos | INT UNSIGNED |  | 민감 영상 수 |
| sensitive_keyword_score_table | sensitive_video_ratio | DECIMAL(10,6) |  | 민감 영상 비율 |
| sensitive_keyword_score_table | cat_politics | INT UNSIGNED |  | 정치 카테고리 매칭 수 |
| sensitive_keyword_score_table | cat_hate | INT UNSIGNED |  | 혐오 카테고리 매칭 수 |
| sensitive_keyword_score_table | cat_aggro | INT UNSIGNED |  | 어그로 카테고리 매칭 수 |
| sensitive_keyword_score_table | cat_adult_illegal | INT UNSIGNED |  | 성인/불법 카테고리 매칭 수 |
| upload_regularity_score_table | channel_id | VARCHAR(64) | PK, FK | source channel_id |
| upload_regularity_score_table | channel_title | VARCHAR(255) |  | 채널명 |
| upload_regularity_score_table | regularity_score | DECIMAL(10,6) |  | 업로드 규칙성 점수 |
| upload_regularity_score_table | mean_interval_days | DOUBLE |  | 평균 업로드 간격 |
| upload_regularity_score_table | std_interval_days | DOUBLE |  | 업로드 간격 표준편차 |
| upload_regularity_score_table | max_gap_days | DOUBLE |  | 최대 업로드 공백 |
| upload_regularity_score_table | cv | DOUBLE |  | 변동계수 |
| upload_regularity_score_table | outlier_ratio | DECIMAL(10,6) |  | 이상 간격 비율 |
| upload_regularity_score_table | gap_ratio | DECIMAL(10,6) |  | 공백 비율 |
| channel_prediction_table | channel_id | VARCHAR(64) | PK, FK | source channel_id |
| channel_prediction_table | title | VARCHAR(255) |  | 대표 채널명 |
| channel_prediction_table | churn_actual_label | TINYINT |  | 이탈 모델 라벨 |
| channel_prediction_table | churn_prob_lr | DECIMAL(10,6) |  | LR 이탈 확률 |
| channel_prediction_table | churn_prob_rf | DECIMAL(10,6) |  | RF 이탈 확률 |
| channel_prediction_table | churn_prob_xgb | DECIMAL(10,6) |  | XGB 이탈 확률 |
| channel_prediction_table | churn_prob | DECIMAL(10,6) |  | 앙상블 이탈 확률 |
| channel_prediction_table | stagnation_actual_label | TINYINT |  | 정체 모델 라벨 |
| channel_prediction_table | stagnation_prob_lr | DECIMAL(10,6) |  | LR 정체 확률 |
| channel_prediction_table | stagnation_prob_rf | DECIMAL(10,6) |  | RF 정체 확률 |
| channel_prediction_table | stagnation_prob_xgb | DECIMAL(10,6) |  | XGB 정체 확률 |
| channel_prediction_table | stagnation_prob | DECIMAL(10,6) |  | 앙상블 정체 확률 |
| channel_prediction_table | volatility_actual_label | TINYINT |  | 변동성 모델 라벨 |
| channel_prediction_table | volatility_prob_lr | DECIMAL(10,6) |  | LR 변동성 확률 |
| channel_prediction_table | volatility_prob_rf | DECIMAL(10,6) |  | RF 변동성 확률 |
| channel_prediction_table | volatility_prob_xgb | DECIMAL(10,6) |  | XGB 변동성 확률 |
| channel_prediction_table | volatility_prob | DECIMAL(10,6) |  | 앙상블 변동성 확률 |
| channel_prediction_table | has_churn | TINYINT |  | churn 결과 존재 여부 |
| channel_prediction_table | has_stagnation | TINYINT |  | stagnation 결과 존재 여부 |
| channel_prediction_table | has_volatility | TINYINT |  | volatility 결과 존재 여부 |
| video_info_table | video_id | VARCHAR(32) | PK | 영상 ID |
| video_info_table | channel_id | VARCHAR(64) | FK | channel_info_table.youtube_channel_id |
| video_info_table | channel_title | VARCHAR(255) |  | 영상 수집 시점 채널명 |
| video_info_table | video_title | TEXT |  | 영상 제목 |
| video_info_table | published_at | DATETIME |  | 영상 업로드 시각 |
| video_info_table | duration_sec | DOUBLE |  | 영상 길이 초 |
| video_info_table | is_shorts | TINYINT |  | Shorts 여부 |
| video_info_table | view_count | BIGINT UNSIGNED |  | 조회수 |
| video_info_table | like_count | BIGINT UNSIGNED |  | 좋아요 수 |
| video_info_table | comment_count | BIGINT UNSIGNED |  | 댓글 수 |
| video_info_table | source_file | VARCHAR(255) |  | 원천 파일 |
| video_info_table | channel_created_at | DATETIME |  | 채널 생성 시각 |
| video_info_table | country | VARCHAR(8) |  | 국가 코드 |
| video_info_table | subscriber_count | BIGINT UNSIGNED |  | 채널 구독자 수 |
| video_info_table | channel_total_views | BIGINT UNSIGNED |  | 채널 누적 조회수 |
| video_info_table | total_video_count | BIGINT UNSIGNED |  | 채널 전체 영상 수 |

## 컬럼 프로파일 요약

| table | column | source_dtype | non_null | null_pct | n_unique | sample | min | median | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| active_viewer_score_table | channel_id | object | 3336 | 0.0 | 3336 | UCy2bCk5KnIfjmWYFHMZcd5w |  |  |  |
| active_viewer_score_table | title | object | 3336 | 0.0 | 3336 | RosaliaVEVO |  |  |  |
| active_viewer_score_table | subscriber_count | int64 | 3336 | 0.0 | 775 | 137000 | 98900.0 | 283000.0 | 1490000.0 |
| active_viewer_score_table | avg_view_count | float64 | 3336 | 0.0 | 3335 | 30169503.76 | 0.0 | 74629.64 | 30169503.76 |
| active_viewer_score_table | view_per_sub | float64 | 3336 | 0.0 | 3335 | 220.2153559124072 | 0.0 | 0.2462 | 220.215356 |
| active_viewer_score_table | cluster | int64 | 3336 | 0.0 | 4 | 1 | 0.0 | 0.0 | 3.0 |
| active_viewer_score_table | cluster_name | object | 3336 | 0.0 | 4 | 슈퍼팬 (최고 활성) |  |  |  |
| active_viewer_score_table | active_viewer_score | float64 | 3251 | 2.548 | 653 | 0.9518 | 0.1653 | 0.6065 | 0.9518 |
| sensitive_keyword_score_table | channel_id | object | 3336 | 0.0 | 3336 | UCdf4di4k4fU5lio8ZXQx6mQ |  |  |  |
| sensitive_keyword_score_table | channel_title | object | 3336 | 0.0 | 3336 | 루스명품 |  |  |  |
| sensitive_keyword_score_table | sensitive_score | float64 | 3336 | 0.0 | 62 | 0.7733 | 0.0 | 0.0133 | 0.7733 |
| sensitive_keyword_score_table | n_sensitive_videos | int64 | 3336 | 0.0 | 29 | 37 | 0.0 | 1.0 | 47.0 |
| sensitive_keyword_score_table | sensitive_video_ratio | float64 | 3336 | 0.0 | 35 | 0.74 | 0.0 | 0.02 | 0.94 |
| sensitive_keyword_score_table | cat_politics | int64 | 3336 | 0.0 | 19 | 0 | 0.0 | 0.0 | 46.0 |
| sensitive_keyword_score_table | cat_hate | int64 | 3336 | 0.0 | 5 | 0 | 0.0 | 0.0 | 4.0 |
| sensitive_keyword_score_table | cat_aggro | int64 | 3336 | 0.0 | 28 | 2 | 0.0 | 1.0 | 52.0 |
| sensitive_keyword_score_table | cat_adult_illegal | int64 | 3336 | 0.0 | 6 | 37 | 0.0 | 0.0 | 37.0 |
| upload_regularity_score_table | channel_id | object | 3333 | 0.0 | 3333 | UCMYu489PAK30L1eYR4eQJmA |  |  |  |
| upload_regularity_score_table | channel_title | object | 3333 | 0.0 | 3333 | 킥튜브 |  |  |  |
| upload_regularity_score_table | regularity_score | float64 | 3333 | 0.0 | 2240 | 1.0 | 0.3577 | 0.6385 | 1.0 |
| upload_regularity_score_table | mean_interval_days | float64 | 3333 | 0.0 | 443 | 0.0 | 0.0 | 3.6 | 108.0 |
| upload_regularity_score_table | std_interval_days | float64 | 3333 | 0.0 | 705 | 0.0 | 0.0 | 3.7 | 461.2 |
| upload_regularity_score_table | max_gap_days | float64 | 3333 | 0.0 | 545 | 0.0 | 0.0 | 18.0 | 3231.0 |
| upload_regularity_score_table | cv | float64 | 3333 | 0.0 | 1902 | 0.0 | 0.0 | 1.166 | 6.836 |
| upload_regularity_score_table | outlier_ratio | float64 | 3333 | 0.0 | 30 | 0.0 | 0.0 | 0.0612 | 0.3469 |
| upload_regularity_score_table | gap_ratio | float64 | 3333 | 0.0 | 1410 | 0.0 | 0.0 | 5.24 | 48.36 |
| channel_prediction_table | channel_id | object | 8083 | 0.0 | 8083 | UC--8ua5dEkuY26fgWkpkz3Q |  |  |  |
| channel_prediction_table | title | object | 8083 | 0.0 | 8074 | 하늘석양 |  |  |  |
| channel_prediction_table | churn_actual_label | int64 | 8083 | 0.0 | 2 | 0 | 0.0 | 0.0 | 1.0 |
| channel_prediction_table | churn_prob_lr | float64 | 8083 | 0.0 | 914 | 0.0 | 0.0 | 0.199 | 0.998 |
| channel_prediction_table | churn_prob_rf | float64 | 8083 | 0.0 | 702 | 0.066 | 0.007 | 0.124 | 0.975 |
| channel_prediction_table | churn_prob_xgb | float64 | 8083 | 0.0 | 2 | 0.0 | 0.0 | 0.0 | 1.0 |
| channel_prediction_table | churn_prob | float64 | 8083 | 0.0 | 677 | 0.022 | 0.002 | 0.11 | 0.987 |
| channel_prediction_table | stagnation_actual_label | float64 | 3333 | 58.765 | 2 | 1.0 | 0.0 | 1.0 | 1.0 |
| channel_prediction_table | stagnation_prob_lr | float64 | 3333 | 58.765 | 870 | 0.871 | 0.0 | 0.507 | 1.0 |
| channel_prediction_table | stagnation_prob_rf | float64 | 3333 | 58.765 | 423 | 0.975 | 0.0 | 0.821 | 0.988 |
| channel_prediction_table | stagnation_prob_xgb | float64 | 3333 | 58.765 | 19 | 1.0 | 0.0 | 1.0 | 1.0 |
| channel_prediction_table | stagnation_prob | float64 | 3333 | 58.765 | 596 | 0.948 | 0.0 | 0.708 | 0.996 |
| channel_prediction_table | volatility_actual_label | float64 | 3333 | 58.765 | 2 | 0.0 | 0.0 | 0.0 | 1.0 |
| channel_prediction_table | volatility_prob_lr | float64 | 3333 | 58.765 | 745 | 0.065 | 0.0 | 0.209 | 1.0 |
| channel_prediction_table | volatility_prob_rf | float64 | 3333 | 58.765 | 372 | 0.024 | 0.0 | 0.086 | 0.991 |
| channel_prediction_table | volatility_prob_xgb | float64 | 3333 | 58.765 | 23 | 0.0 | 0.0 | 0.0 | 1.0 |
| channel_prediction_table | volatility_prob | float64 | 3333 | 58.765 | 514 | 0.03 | 0.0 | 0.106 | 0.997 |
| channel_prediction_table | has_churn | int64 | 8083 | 0.0 | 1 | 1 | 1.0 | 1.0 | 1.0 |
| channel_prediction_table | has_stagnation | int64 | 8083 | 0.0 | 2 | 1 | 0.0 | 0.0 | 1.0 |
| channel_prediction_table | has_volatility | int64 | 8083 | 0.0 | 2 | 1 | 0.0 | 0.0 | 1.0 |
| video_info_table | video_id | object | 166449 | 0.0 | 166449 | yOTYf7a8XBY |  |  |  |
| video_info_table | channel_id | object | 166449 | 0.0 | 3336 | UC0kp1x32b-Y4cvP5r3vW_hw |  |  |  |
| video_info_table | channel_title | object | 166449 | 0.0 | 3336 | Sereno Official |  |  |  |
| video_info_table | video_title | object | 166448 | 0.001 | 164520 | Sereno - 목설화 (目雪話) |  |  |  |
| video_info_table | published_at | object | 166445 | 0.002 | 155849 | 2017-09-21 11:07:10+00:00 |  |  |  |
| video_info_table | duration_sec | float64 | 166144 | 0.183 | 8425 | 195.0 | 2.0 | 215.0 | 83514.0 |
| video_info_table | is_shorts | bool | 166449 | 0.0 | 2 | False | 0.0 | 0.0 | 1.0 |
| video_info_table | view_count | float64 | 166445 | 0.002 | 100541 | 314804.0 | 0.0 | 33989.0 | 707336604.0 |
| video_info_table | like_count | float64 | 161243 | 3.128 | 16383 | 2497.0 | 0.0 | 566.0 | 2262875.0 |
| video_info_table | comment_count | float64 | 163718 | 1.641 | 3239 | 84.0 | 0.0 | 38.0 | 325451.0 |
| video_info_table | source_file | object | 166445 | 0.002 | 80 | videos_3250-3299.csv |  |  |  |
| video_info_table | channel_created_at | object | 166449 | 0.0 | 3336 | 2015-11-02T10:38:22Z |  |  |  |
| video_info_table | country | object | 150816 | 9.392 | 14 | KR |  |  |  |
| video_info_table | subscriber_count | float64 | 166449 | 0.0 | 775 | 100000.0 | 98900.0 | 284000.0 | 1490000.0 |
| video_info_table | channel_total_views | float64 | 166449 | 0.0 | 3335 | 46972796.0 | 0.0 | 116931949.0 | 5648210224.0 |
| video_info_table | total_video_count | float64 | 166449 | 0.0 | 1736 | 78.0 | 0.0 | 606.0 | 25899.0 |

## 생성된 그래프

- `reports/eda/post_load_table_rows.png`
- `reports/eda/post_load_fk_coverage.png`
- `reports/eda/post_load_prediction_coverage.png`
- `reports/eda/post_load_score_distributions.png`
- `reports/eda/post_load_video_info_profile.png`

## 생성된 SQL

- `reports/eda/post_load_new_tables_schema.sql`
- `reports/eda/post_load_eda_views.sql`
