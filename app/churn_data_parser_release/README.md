# churn-data-parser

YouTube 채널 ID 하나를 받아 채널 메타데이터, 최근 영상 메타데이터, 일부 댓글을 JSON으로 수집하는 단건 파서입니다.

## Output Scope

- 채널 정보
- 채널 `/videos` 탭 기준 최근 영상 최대 50개
- 수집된 영상 중 앞 10개 영상의 댓글
- 댓글은 top 정렬 기준 root comment만 포함
- 업로더 댓글은 제외
- 댓글 수집 대상이 아닌 영상은 `comments: []`로 출력

라이브 또는 예정 영상은 메타데이터 수집 과정에서 제외될 수 있습니다.

## Requirements

- Python 3.11 이상
- `uv`
- 댓글 수집 시 PATH에서 실행 가능한 Deno

`--no-comments` 옵션을 사용하면 Deno 없이 영상 메타데이터만 수집할 수 있습니다.

## Setup

```bash
uv sync
```

## Usage

입력값은 현재 YouTube 채널 ID 형식만 지원합니다.

```bash
uv run python main.py <channel_id>
```

예시:

```bash
uv run python main.py UC0kp1x32b-Y4cvP5r3vW_hw
```

JSON 파일로 저장:

```bash
uv run python main.py UC0kp1x32b-Y4cvP5r3vW_hw --output result.json
```

댓글 없이 메타데이터만 수집:

```bash
uv run python main.py UC0kp1x32b-Y4cvP5r3vW_hw --no-comments
```

## Output Shape

최상위 JSON은 채널 정보와 영상 목록을 포함합니다.

```json
{
  "channel_id": "UC...",
  "channel_title": "channel title",
  "subscriber_count": 0,
  "description": "channel description",
  "collected_at": "2026-05-21T00:00:00Z",
  "videos": [
    {
      "video_number": "V001",
      "video_id": "video id",
      "video_title": "video title",
      "published_at": "2026-05-21",
      "timestamp": 0,
      "duration_sec": 0,
      "is_shorts": 0,
      "view_count": 0,
      "like_count": 0,
      "comment_count": 0,
      "comments": []
    }
  ]
}
```

각 댓글 객체는 `id`, `text`, `author_id`, `like_count`, `timestamp`, `is_pinned`, `is_favorited` 필드를 포함합니다.

## Notes

- YouTube 추출 결과는 채널 상태, 영상 공개 상태, yt-dlp 동작에 따라 달라질 수 있습니다.
- 댓글 수집을 켠 실행은 Deno가 없으면 시작 단계에서 실패합니다.
