import json
import csv
from datetime import datetime, timezone
from pathlib import Path


def _to_mysql_dt(unix_ts: int | float | None) -> str | None:
    if unix_ts is None:
        return None
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def parse_info_json(
    file_path: Path,
    max_comments: int | None = None,
    exclude_uploader: bool = False,
    root_only: bool = False,
) -> list[dict]:
    with open(file_path, encoding="utf-8-sig") as f:
        data = json.load(f)

    video_id = data.get("id", "")
    video_published_at = _to_mysql_dt(data.get("timestamp"))
    comments_raw = data.get("comments", [])

    # Deduplicate by comment id, keeping first occurrence (preserves YouTube's sort order)
    seen_ids: set[str] = set()
    deduped = []
    for c in comments_raw:
        cid = c.get("id")
        if cid and cid not in seen_ids:
            seen_ids.add(cid)
            deduped.append(c)

    # Collect uploader comment IDs to derive parent_is_uploader
    uploader_comment_ids = {c["id"] for c in deduped if c.get("author_is_uploader")}

    if root_only:
        deduped = [c for c in deduped if c.get("parent", "root") == "root"]

    if exclude_uploader:
        deduped = [c for c in deduped if not c.get("author_is_uploader")]

    if max_comments is not None:
        deduped = deduped[:max_comments]

    rows = []
    for idx, c in enumerate(deduped):
        parent = c.get("parent", "root")
        rows.append({
            "video_id": video_id,
            "video_published_at": video_published_at,
            "comment_index": idx,
            "id": c.get("id", ""),
            "parent": parent,
            "is_reply": parent != "root",
            "parent_is_uploader": parent in uploader_comment_ids,
            "text": c.get("text", ""),
            "author_id": c.get("author_id", ""),
            "author_is_uploader": c.get("author_is_uploader", False),
            "author_is_verified": c.get("author_is_verified", False),
            "like_count": c.get("like_count", 0),
            "timestamp": _to_mysql_dt(c.get("timestamp")),
            "is_favorited": c.get("is_favorited", False),
            "is_pinned": c.get("is_pinned", False),
        })

    return rows


FIELDNAMES = [
    "video_id", "video_published_at", "comment_index", "id", "parent",
    "is_reply", "parent_is_uploader", "text", "author_id",
    "author_is_uploader", "author_is_verified", "like_count",
    "timestamp", "is_favorited", "is_pinned",
]


def write_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def parse_directory(input_dir: Path, output_path: Path) -> int:
    json_files = sorted(input_dir.glob("*.info.json"))
    if not json_files:
        print(f"No .info.json files found in {input_dir}")
        return 0

    all_rows: list[dict] = []
    for f in json_files:
        rows = parse_info_json(f)
        all_rows.extend(rows)
        print(f"  {f.name}: {len(rows)} comments")

    write_csv(all_rows, output_path)
    return len(all_rows)
