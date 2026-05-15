# 데이터 스키마

`data/raw/` 에 저장되는 세 종류의 CSV 에 대한 컬럼 정의서.
출처가 youtube-rank 크롤링 / YouTube Data API v3 로 나뉘므로 각 컬럼이 어디서 왔는지를 함께 명시한다.

| 파일 | 출처 | 단위 | 행 수 (현재) |
|---|---|---|---|
| [`data/raw/youtube_channels.csv`](../data/raw/youtube_channels.csv) | youtube-rank.com 크롤링 | 채널 1개 | 176 |
| [`data/raw/channels/csv/channels_must_0_49.csv`](../data/raw/channels/csv/channels_must_0_49.csv) | YouTube Data API v3 `channels.list` | 채널 1개 | 49 |
| [`data/raw/videos/csv/videos_0000-0049.csv`](../data/raw/videos/csv/videos_0000-0049.csv) | YouTube Data API v3 `playlistItems.list` + `videos.list` | 영상 1개 | 310 |

---

## 1. `data/raw/youtube_channels.csv`

- **출처**: youtube-rank.com 크롤링 (마스터 시드 테이블)
- **단위**: 1행 = 채널 1개
- **역할**: API 수집의 시드(`youtube_channel_id`) 와 **이탈 라벨**(`is_churned`) 제공

| 컬럼 | 타입 | 예시 | 출처 / 설명 |
|---|---|---|---|
| `channel_name` | str | `장정숙` | 크롤링 — 채널명 |
| `category` | str | `뉴스/정치/사회`, `미분류` | 크롤링 — youtube-rank 분류 |
| `subscriber_raw` | str / int | `53` | 크롤링 원본 표시값 |
| `subscriber_count` | int | `53` | 정수 변환값 |
| `total_views_raw` | str | `4174만` | 크롤링 원본 (한글 단위 포함) |
| `total_views` | int | `41740000` | 정수 변환값 |
| `video_count_raw` | str | `3개` | 크롤링 원본 표기 |
| `video_count` | int | `3` | 정수 변환값 |
| `created_date` | datetime (KST 추정) | `2016-06-08 15:54:31` | 크롤링 — 채널 개설일 |
| `latest_video_date` | datetime (KST 추정, nullable) | `2019-12-11 14:58:53` | 크롤링 — 최근 영상일 (없으면 공란) |
| `days_since_latest_video` | float (nullable) | `2346.0` | 크롤링 시점 기준 최근 영상 이후 경과일 |
| `is_churned` | float `0` / `1` (nullable) | `1.0` | **타겟 변수** — 이탈 여부 (NaN 은 라벨 없음) |
| `youtube_channel_url` | str | `https://www.youtube.com/channel/UCo3Yj54VtkEvQX9cLHKklzw` | 크롤링 — 채널 URL |
| `youtube_channel_id` | str | `UCo3Yj54VtkEvQX9cLHKklzw` | **PK** — API 수집의 시드 |

---

## 2. `data/raw/channels/csv/channels_must_0_49.csv`

- **출처**: YouTube Data API v3 — `channels.list` (parts: `snippet`, `statistics`, `contentDetails`)
- **단위**: 1행 = 채널 1개
- **분할 규칙**: 파일명 `channels_must_<start>_<end>.csv` — 마스터의 행 인덱스 구간 (예: `0_49` = 0~49행)
- **원본 JSON**: [`data/raw/channels/json/`](../data/raw/channels/json/) 에 동일 배치의 전체 응답 보존

| 컬럼 | 타입 | 예시 | 출처 / 설명 |
|---|---|---|---|
| `channel_id` | str | `UCo_gG722HnnJ7O-AOt2xtRA` | **PK / FK** → `youtube_channels.youtube_channel_id` |
| `title` | str | `Soyeon Yang` | `snippet.title` (API 시점 채널명) |
| `published_at` | ISO 8601 datetime (UTC) | `2013-06-09T23:18:55Z` | `snippet.publishedAt` — 채널 개설일시 |
| `country` | str (nullable) | `KR` (대부분 공란) | `snippet.country` |
| `uploads_playlist` | str | `UUo_gG722HnnJ7O-AOt2xtRA` | `contentDetails.relatedPlaylists.uploads` — 영상 수집용 플레이리스트 ID (`UU…`) |
| `subscriber_count` | int | `2` | `statistics.subscriberCount` (API 시점) |
| `view_count` | int | `1464` | `statistics.viewCount` |
| `video_count` | int | `29` | `statistics.videoCount` |

---

## 3. `data/raw/videos/csv/videos_0000-0049.csv`

- **출처**: YouTube Data API v3 — `playlistItems.list` (업로드 목록) + `videos.list` (영상별 통계)
- **단위**: 1행 = 영상 1개 (채널당 최근 최대 50개)
- **분할 규칙**: 파일명 `videos_<start>-<end>.csv` — 마스터의 행 인덱스 구간 (예: `0000-0049` = 0~49행 채널의 영상)
- **원본 JSON**: [`data/raw/videos/json/`](../data/raw/videos/json/) 에 채널별 파일 보존 (`<idx>_<channel_id>.json`)

| 컬럼 | 타입 | 예시 | 출처 / 설명 |
|---|---|---|---|
| `idx` | int | `0` | 마스터(`youtube_channels.csv`) 행 인덱스 — 배치 분할/추적용 |
| `channel_id` | str | `UCo3Yj54VtkEvQX9cLHKklzw` | **FK** → `channels.channel_id` |
| `channel_title` | str | `장정숙` | 조인 편의용 중복 컬럼 |
| `video_id` | str | `eM25H_bOkJ4` | **PK** |
| `video_title` | str | `171024 [장정숙 의원] 2017 국정감사…` | `snippet.title` |
| `published_at` | ISO 8601 datetime (UTC) | `2018-05-28T02:16:23Z` | `snippet.publishedAt` — 업로드 시각 |
| `duration_sec` | float | `66.0` | `contentDetails.duration` (ISO 8601) → 초 변환 |
| `is_shorts` | bool | `False` | duration 기반 휴리스틱 (≤ 60s 판정 — 노트북 정의 확인 권장) |
| `view_count` | int | `75` | `statistics.viewCount` |
| `like_count` | int | `0` | `statistics.likeCount` |
| `comment_count` | float | `0.0` | `statistics.commentCount` — 댓글 비활성 채널에서 NaN 가능 |

---

## 조인 관계

```
youtube_channels.csv          channels_must_*.csv         videos_*.csv
─────────────────────         ──────────────────         ──────────────
youtube_channel_id  (1) ──── (1)  channel_id
                                  channel_id        (1) ── (N)  channel_id
                                  uploads_playlist            video_id (PK)
is_churned  ← 라벨
```

- 마스터(`youtube_channels.csv`) 의 `youtube_channel_id` 가 두 API 테이블의 `channel_id` 와 1:1 / 1:N 으로 연결된다.
- 학습 데이터를 만들 때는 영상/채널 → 마스터 순서로 조인해 `is_churned` 라벨을 붙인다.

## 주의사항

- **시점 차이**: 크롤링 시점(`youtube_channels.csv`) 과 API 호출 시점(`channels_must_*`, `videos_*`) 이 다르므로 `subscriber_count`, `view_count` 등이 일치하지 않을 수 있다. 학습/피처 엔지니어링에는 **API 값을 정답으로** 사용한다.
- **타임존**: API 의 `published_at` 은 UTC(`Z`), 마스터의 `created_date` / `latest_video_date` 는 KST 로 추정. 기간 계산 전 통일 필요.
- **결측**: 활동 이력이 없는 채널은 `latest_video_date`, `days_since_latest_video`, `is_churned` 가 NaN. 라벨 NaN 행은 학습에서 제외해야 한다.
- **`*_raw` 컬럼**: 분석/모델링에는 정수형 컬럼(`subscriber_count`, `total_views`, `video_count`) 만 사용. `_raw` 는 검증용.
- **수정 금지**: `data/raw/` 는 원본 보존. 가공은 [`data/processed/`](../data/processed/) 에서.
