# data/

프로젝트에서 사용하는 모든 데이터를 저장합니다.
5명이 quota 를 분할 수집한 결과를 통합해야 하므로 `data/` 는 **git 으로 팀과 공유**합니다.
용량이 매우 큰 파일이 생기면 그때 개별로 `.gitignore` 에 추가하세요.

## 하위 폴더

### raw/
원시 데이터. 수집 후 절대 수정하지 않습니다.

- `raw/youtube_channels.csv` — youtube-rank.com 크롤링 마스터 테이블
  - 컬럼: `channel_name, category, subscriber_count, total_views, video_count, created_date, latest_video_date, days_since_latest_video, is_churned, youtube_channel_url, youtube_channel_id`
  - 역할: API 수집의 시드(`youtube_channel_id`) + 이탈 라벨(`is_churned`) 제공
- `raw/channels/` — YouTube Data API v3 채널별 상세 (`channels.list`)
  - `json/` 원시 응답, `csv/` MUST 필드 추출본
- `raw/videos/` — YouTube Data API v3 영상별 상세 (`playlistItems.list` + `videos.list`)
  - `json/` 채널 단위 원시 응답, `csv/` MUST 필드 추출본
  - 내용: 채널별 최근 50개 영상의 views, likes, comments, duration, published_at

### processed/
전처리 및 피처 엔지니어링 완료 데이터.

- `processed/features/` — 피처 엔지니어링 완료 CSV (`features_YYYYMMDD.csv`)
- `processed/splits/` — train / val / test 분리 결과
  - `train.csv`, `val.csv`, `test.csv`

## 주의사항

- `raw/` 데이터는 수정 금지. 전처리 결과는 반드시 `processed/` 에 저장
- API 수집 시 팀원별 담당 채널 범위를 `raw/youtube_channels.csv` 의 행 인덱스로 분할
