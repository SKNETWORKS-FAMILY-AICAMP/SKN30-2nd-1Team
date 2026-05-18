# CommentParser

YouTube comment collection and parsing pipeline using `yt-dlp`.

## Requirements

- Python 3.12+
- `uv`

Deno is bundled as a Python package dependency and installed automatically via `uv sync`. No separate Deno installation is needed.

## Setup

```bash
uv sync
```

## Single Video

```bash
uv run python main.py VIDEO_ID
```

Useful options:

```bash
uv run python main.py VIDEO_ID --no-save-json        # raw JSON 삭제
uv run python main.py VIDEO_ID --output custom.csv   # 출력 파일명 지정
uv run python main.py VIDEO_ID --raw-dir /tmp/raw    # raw JSON 저장 경로 지정
uv run python main.py VIDEO_ID --remote-components   # yt-dlp 원격 JS 컴포넌트 허용
```

## Batch

### 입력 TSV 형식

> 공식 입력은 `channel_number`, `channel_id` 2개 컬럼입니다.
> 헤더 포함/미포함 둘 다 지원합니다.
> 컬럼 구성이 다른 파일(예: 채널 목록 원본 `sampled_channels.tsv`)은 직접 입력으로 사용하지 말고, 아래 형식의 실행용 TSV로 전처리해서 사용합니다.

**일반 배치** — 채널 단위로 수집:

헤더 포함:

```tsv
channel_number	channel_id
CH07150	UCKNdfTZCJuOQfWN5Pe5UAAQ
CH07226	UCAaLhok91QDrweyuDRsmjqQ
```

헤더 없음:

```tsv
CH07150	UCKNdfTZCJuOQfWN5Pe5UAAQ
CH07226	UCAaLhok91QDrweyuDRsmjqQ
```

| 컬럼 | 설명 |
|------|------|
| `channel_number` | 프로젝트 내부 채널 식별자 (임의 지정, 문자열) |
| `channel_id` | YouTube 채널 ID (`UC...` 형식) |

- 채널당 최신 10개 영상을 자동으로 수집
- 영상 목록은 `data/videos/csv/`에서 먼저 조회하고, 없으면 YouTube에서 직접 가져옴 (라이브/라이브 VOD 제외)
- 영상 목록 조회 실패 시 해당 채널은 `failed_channels_YYYYMMDD_HHMMSS.tsv`에 기록하고 다음 채널로 진행

**retry 배치** — 실패한 영상 재시도:

```tsv
channel_number	channel_id	video_number	video_id
CH07150	UCKNdfTZCJuOQfWN5Pe5UAAQ	3	iV1IOGlFHiw
```

| 컬럼 | 설명 |
|------|------|
| `channel_number` | 채널 식별자 |
| `channel_id` | YouTube 채널 ID |
| `video_number` | 채널 내 영상 순번 |
| `video_id` | YouTube 영상 ID |

- `video_id` 컬럼이 있으면 자동으로 retry 모드로 동작
- 실패 시 생성되는 `failed_YYYYMMDD_HHMMSS.tsv`를 그대로 입력으로 사용 가능

### 실행

```bash
uv run python batch.py INPUT.tsv --dry-run       # 실제 수집 없이 영상 목록 확인
uv run python batch.py INPUT.tsv                 # 수집 실행
uv run python batch.py INPUT.tsv --no-save-json  # raw JSON 삭제 (CSV만 보존)
uv run python batch.py INPUT.tsv --output-dir /path/to/csv  # 출력 경로 지정
```

### 실패 처리 및 재시도

배치 실행 후 실패가 있으면 두 종류의 파일이 생성됩니다.

| 파일 | 발생 조건 | 내용 |
|------|-----------|------|
| `failed_YYYYMMDD_HHMMSS.tsv` | 영상 댓글 수집/파싱 실패 | `channel_number`, `channel_id`, `video_number`, `video_id` |
| `failed_channels_YYYYMMDD_HHMMSS.tsv` | 채널 영상 목록 조회 실패 | `channel_number`, `channel_id`, `reason`, `error_message` |

**두 파일 모두 그대로 batch.py 입력으로 사용할 수 있습니다:**

```bash
uv run python batch.py failed_20260518_010000.tsv          # 영상 재시도
uv run python batch.py failed_channels_20260518_010000.tsv # 채널 재시도
```

## 수집 정책 (Batch)

| 항목 | 내용 |
|------|------|
| 채널당 영상 수 | 최신순 상위 10개 (라이브/라이브 VOD 제외) |
| 댓글 정렬 | YouTube 인기순 |
| 수집량 | 영상당 최대 60개 수집 후 50개 출력 |
| 크리에이터 댓글 | 제외 |
| 대댓글 | 제외 |

## 출력 경로

배치 실행 시 raw JSON 및 CSV 출력 경로는 **스크립트를 실행하는 위치(working directory) 기준**으로 생성됩니다.

| 파일 | 기본 경로 |
|------|----------|
| raw JSON (중간 파일) | `./data/parsed-raw/` |
| output CSV | `./data/parsed-csv/` |
| 실패 TSV | `./failed_YYYYMMDD_HHMMSS.tsv` |

`--output-dir`, `--raw-dir` 옵션으로 경로를 직접 지정할 수 있습니다.

## Output CSV Columns

| Column | Description |
|--------|-------------|
| `video_id` | YouTube video ID (join key) |
| `video_published_at` | Video upload datetime (UTC, `YYYY-MM-DD HH:MM:SS`) |
| `comment_index` | Comment order as returned by YouTube (0-based, reflects popularity ranking) |
| `id` | Comment unique ID |
| `parent` | `"root"` if top-level comment; parent comment's `id` if this is a reply |
| `is_reply` | `True` if this is a reply to another comment |
| `parent_is_uploader` | `True` if the parent comment was written by the video uploader |
| `text` | Comment body |
| `author_id` | Commenter's channel ID (join key) |
| `author_is_uploader` | `True` if the commenter is the video uploader |
| `author_is_verified` | `True` if the commenter's channel is verified |
| `like_count` | Number of likes on the comment |
| `timestamp` | Comment post datetime (UTC, `YYYY-MM-DD HH:MM:SS`) |
| `is_favorited` | `True` if the uploader hearted this comment |
| `is_pinned` | `True` if this is a pinned comment |
