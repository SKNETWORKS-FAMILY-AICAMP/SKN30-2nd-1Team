import csv
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

from src.fetcher import fetch_comments
from src.parser import parse_info_json, write_csv

_HERE = Path(__file__).parent
VIDEOS_CSV_DIR = _HERE / "data/videos/csv"
RAW_DIR = Path("data/parsed-raw")
OUTPUT_DIR = Path("data/parsed-csv")

MAX_VIDEOS_PER_CHANNEL = 10
COMMENT_FETCH_LIMIT = "60,60,0"  # youtube extractor: total,root,replies_per_thread
MAX_VIEWER_COMMENTS = 50


def _fetch_video_ids_from_youtube(channel_id: str) -> list[str]:
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist",
        "--match-filter", "!is_live & !was_live",
        "--print", "%(id)s\t%(upload_date)s",
        "--playlist-end", str(MAX_VIDEOS_PER_CHANNEL * 2),
        "--no-warnings",
        f"https://www.youtube.com/channel/{channel_id}/videos",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    videos = []
    for line in result.stdout.strip().splitlines():
        parts = line.strip().split("\t")
        if len(parts) == 2:
            videos.append((parts[1], parts[0]))  # (upload_date, video_id)
    videos.sort(key=lambda x: x[0], reverse=True)
    return [vid for _, vid in videos[:MAX_VIDEOS_PER_CHANNEL]]


def load_videos_for_channel(channel_id: str) -> list[str]:
    videos = []
    for csv_file in sorted(VIDEOS_CSV_DIR.glob("*.csv")):
        with open(csv_file, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row["channel_id"] == channel_id:
                    videos.append((row["published_at"], row["video_id"]))

    if videos:
        videos.sort(key=lambda x: x[0], reverse=True)
        return [vid for _, vid in videos[:MAX_VIDEOS_PER_CHANNEL]]

    print(f"  (no CSV for {channel_id}, fetching from YouTube...)", flush=True)
    return _fetch_video_ids_from_youtube(channel_id)


def run_batch(
    input_tsv: Path,
    raw_dir: Path,
    output_dir: Path,
    no_save_json: bool,
    dry_run: bool = False,
    remote_components: bool = False,
) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    failed: list[dict] = []
    failed_channels: list[dict] = []
    total_processed = 0
    skipped = 0
    no_comments = 0

    with open(input_tsv, encoding="utf-8", newline="") as f:
        first = next(csv.reader(f, delimiter="\t"), None)
    if not first:
        print("No rows in input TSV.")
        return

    has_header = first[0] == "channel_number"
    if has_header:
        col_count = len(first)
    else:
        col_count = len(first)

    if col_count >= 4:
        fieldnames = ["channel_number", "channel_id", "video_number", "video_id"]
    else:
        fieldnames = ["channel_number", "channel_id"]

    with open(input_tsv, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(
            f, delimiter="\t",
            fieldnames=None if has_header else fieldnames,
        )
        rows = list(reader)

    if not rows:
        print("No rows in input TSV.")
        return

    is_retry = "video_id" in rows[0]

    for row in rows:
        channel_number = row["channel_number"]
        channel_id = row["channel_id"]

        if is_retry:
            videos = [(int(row["video_number"]), row["video_id"])]
        else:
            try:
                video_ids = load_videos_for_channel(channel_id)
                videos = list(enumerate(video_ids, start=1))
            except Exception as e:
                print(f"[ch:{channel_number}] SKIP (video list fetch failed: {e})")
                failed_channels.append({
                    "channel_number": channel_number,
                    "channel_id": channel_id,
                    "reason": "video_list_fetch_failed",
                    "error_message": str(e),
                })
                continue

        total = len(videos)
        for video_number, video_id in videos:
            total_processed += 1
            stem = f"{channel_number}_{video_number}_{channel_id}_{video_id}"
            print(f"[ch:{channel_number}] video {video_number}/{total} ({video_id}) ... ", end="", flush=True)

            if dry_run:
                skipped += 1
                print("SKIP (dry-run)")
                continue

            try:
                json_path = fetch_comments(
                    video_id,
                    raw_dir,
                    output_stem=stem,
                    remote_components=remote_components,
                    comment_limit=COMMENT_FETCH_LIMIT,
                )
                parsed_rows = parse_info_json(
                    json_path,
                    max_comments=MAX_VIEWER_COMMENTS,
                    exclude_uploader=True,
                    root_only=True,
                )
                write_csv(parsed_rows, output_dir / f"{stem}.csv")
                if no_save_json:
                    json_path.unlink()
                if len(parsed_rows) == 0:
                    no_comments += 1
                    print("OK (0 comments — disabled or empty)")
                else:
                    print(f"OK ({len(parsed_rows)} comments)")
            except Exception as e:
                print(f"FAIL ({e})")
                failed.append({
                    "channel_number": channel_number,
                    "channel_id": channel_id,
                    "video_number": video_number,
                    "video_id": video_id,
                })

    print(f"\n{'='*50}")
    print(f"Total:   {total_processed}")
    if dry_run:
        print(f"Skipped: {skipped}")
    else:
        print(f"Success: {total_processed - len(failed)}")
        print(f"  (No comments: {no_comments})")
    print(f"Failed:  {len(failed)}")
    if failed_channels:
        print(f"Failed channels (video list): {len(failed_channels)}")

    if failed:
        failed_path = Path(f"failed_{timestamp}.tsv")
        with open(failed_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["channel_number", "channel_id", "video_number", "video_id"],
                delimiter="\t",
            )
            writer.writeheader()
            writer.writerows(failed)
        print(f"Failed videos → {failed_path}")

    if failed_channels:
        failed_ch_path = Path(f"failed_channels_{timestamp}.tsv")
        with open(failed_ch_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["channel_number", "channel_id", "reason", "error_message"],
                delimiter="\t",
            )
            writer.writeheader()
            writer.writerows(failed_channels)
        print(f"Failed channels → {failed_ch_path}")


def main():
    parser = argparse.ArgumentParser(description="Batch YouTube comment parser")
    parser.add_argument("input_tsv", type=Path, help="TSV file (channel_number, channel_id) or retry TSV")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DIR,
        help=f"Directory to save .info.json files (default: {RAW_DIR})",
    )
    parser.add_argument(
        "--no-save-json",
        action="store_true",
        help="Delete .info.json files after parsing",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Directory to save parsed CSV files (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without fetching or writing files",
    )
    parser.add_argument(
        "--remote-components",
        action="store_true",
        help="Allow yt-dlp to load remote JS components such as ejs:github",
    )
    args = parser.parse_args()

    if not args.input_tsv.is_file():
        parser.error(f"'{args.input_tsv}' is not a file")

    if args.dry_run:
        print("[DRY RUN] No files will be fetched or written.\n")
    run_batch(
        args.input_tsv,
        args.raw_dir,
        args.output_dir,
        args.no_save_json,
        args.dry_run,
        args.remote_components,
    )


if __name__ == "__main__":
    main()
