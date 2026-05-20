# 전체 DB 적재 완료 후 EDA 스키마

기존 적재 완료 테이블과 추가 적재 테이블이 모두 적재된 이후를 기준으로 재구성한 EDA 스키마입니다.

## 최종 DB 기존 테이블

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

## 적재 완료 후 EDA 뷰

| eda_view | grain | base_tables | purpose |
| --- | --- | --- | --- |
| v_channel_score_eda | 채널 1개 | channel_info_table + active_viewer_score_table + sensitive_keyword_score_table + upload_regularity_score_table + channel_prediction_table | 채널별 활성 시청자, 민감 키워드, 업로드 규칙성, 3종 예측 확률을 한 번에 보는 핵심 EDA 뷰 |
| v_category_score_eda | 카테고리 x 채널 | category_table + channel_category_table + v_channel_score_eda | 카테고리별 위험/활성/민감도 분포 비교 |
| v_band_score_eda | 구독자 밴드 x 채널 | band_table + channel_info_table + v_channel_score_eda | 구독자 규모 구간별 위험/예측 점수 분포 비교 |
| v_video_activity_eda | 영상 1개 | video_info_table + channel_info_table | 영상 업로드 시계열, Shorts 비율, 조회/좋아요/댓글 분포 분석 |
| v_comment_community_eda | 댓글 1개 | comments_table | 댓글 수, 작성 시점, 좋아요, 작성자/대댓글 구조 분석. video_info_table과는 FK 연결하지 않음 |
| v_prediction_model_eda | 채널 1개 | channel_prediction_table + channel_info_table | churn/stagnation/volatility 예측 확률 간 상관, 결측, 모델 커버리지 분석 |

## 설계 결정사항

| decision | detail |
| --- | --- |
| FK 기준 | CSV의 channel_id는 유튜브 난수값이며 channel_info_table.youtube_channel_id에 연결한다. |
| filtered_dataset_wide 스킵 | 채널 단위 wide 피처는 channel_info_table과 역할이 중복되어 별도 테이블로 적재하지 않는다. |
| 댓글-영상 미연결 | video_info_table과 comments_table은 video_id가 다를 수 있어 FK를 만들지 않는다. |
| 예측 결과 통합 | churn, volatility, stagnation 결과는 channel_prediction_table 하나로 합친다. |
| EDA 기준 시점 | 아래 산출물은 기존 테이블과 추가 적재 테이블이 모두 적재 완료된 이후의 DB를 기준으로 구성한다. |
| 인코딩/정렬 | 신규 테이블은 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 기준으로 생성한다. |

## 컬럼 스키마

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
