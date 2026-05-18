import argparse
from pathlib import Path
from src.fetcher import fetch_comments
from src.parser import parse_info_json, write_csv

OUTPUT_DIR = Path("data/parsed-csv")


def main():
    parser = argparse.ArgumentParser(description="YouTube comment parser using yt-dlp")
    parser.add_argument("video_id", help="YouTube video ID (e.g. FDUsLDBgjFs)")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/parsed-raw"),
        help="Directory to save .info.json files (default: data/parsed-raw)",
    )
    parser.add_argument(
        "--no-save-json",
        action="store_true",
        help="Delete .info.json file after parsing",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV filename (default: {video_id}.csv)",
    )
    parser.add_argument(
        "--remote-components",
        action="store_true",
        help="Allow yt-dlp to load remote JS components such as ejs:github",
    )
    args = parser.parse_args()

    print(f"Fetching: {args.video_id}")
    json_path = fetch_comments(
        args.video_id,
        args.raw_dir,
        remote_components=args.remote_components,
    )

    base_name = json_path.name[: -len(".info.json")]  # {channel_id}_{video_id}
    output_path = OUTPUT_DIR / (args.output or f"{base_name}.csv")

    print(f"Parsing: {json_path.name}")
    rows = parse_info_json(json_path)

    write_csv(rows, output_path)

    if args.no_save_json:
        json_path.unlink()
        print(f"Deleted: {json_path.name}")

    print(f"Done: {len(rows)} comments → {output_path}")


if __name__ == "__main__":
    main()
