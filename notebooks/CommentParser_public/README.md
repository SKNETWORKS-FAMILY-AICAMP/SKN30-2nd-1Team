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

**일반 배치** — 채널 단위로 수집:

```tsv
channel_number	channel_id
8002	UCsJ6RuBiTVWRX156FVbeaGg
8012	UC1B6SalAoiJD7eHfMUA9QrA
```

| 컬럼 | 설명 |
|------|------|
| `channel_number` | 프로젝트 내부 채널 식별 번호 (임의 지정) |
| `channel_id` | YouTube 채널 ID (`UC...` 형식) |

- 채널당 `published_at` 기준 최신 20개 영상을 자동으로 수집
- 영상 목록은 `data/videos/csv/` 디렉토리의 CSV 파일에서 조회

**retry 배치** — 실패한 영상 재시도:

```tsv
channel_number	channel_id	video_number	video_id
8002	UCsJ6RuBiTVWRX156FVbeaGg	3	iV1IOGlFHiw
```

| 컬럼 | 설명 |
|------|------|
| `channel_number` | 채널 식별 번호 |
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

실패한 영상 목록은 `failed_YYYYMMDD_HHMMSS.tsv`로 자동 저장됩니다.

## 수집 정책 (Batch)

| 항목 | 내용 |
|------|------|
| 채널당 영상 수 | 최신순 상위 20개 |
| 댓글 정렬 | YouTube 인기순 |
| 수집량 | 영상당 최대 120개 수집 후 100개 출력 |
| 크리에이터 댓글 | 제외 |
| 대댓글 | 제외 |

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
