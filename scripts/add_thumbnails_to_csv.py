"""data/raw/channels/json/*.json에서 thumbnail URL을 추출해 all_channels.csv 마지막 컬럼에 추가."""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
JSON_DIR = ROOT / "data" / "raw" / "channels" / "json"
CSV_PATH = ROOT / "data" / "raw" / "channels" / "csv" / "all_channels.csv"


def build_thumbnail_map() -> dict[str, str]:
    thumbs: dict[str, str] = {}
    for jf in sorted(JSON_DIR.glob("*.json")):
        try:
            items = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  skip {jf.name}: {e}", file=sys.stderr)
            continue
        for item in items:
            cid = item.get("id", "")
            url = (
                item.get("snippet", {})
                .get("thumbnails", {})
                .get("default", {})
                .get("url", "")
            )
            if cid:
                thumbs[cid] = url
    return thumbs


def main() -> None:
    print(f"JSON 파일 로드: {JSON_DIR}")
    thumbs = build_thumbnail_map()
    print(f"  → {len(thumbs):,}개 채널 썸네일 수집")

    df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
    before_cols = list(df.columns)

    if "thumbnail_url" in df.columns:
        df = df.drop(columns=["thumbnail_url"])

    df["thumbnail_url"] = df["channel_id"].map(thumbs).fillna("")

    matched = (df["thumbnail_url"] != "").sum()
    print(f"  → CSV {len(df):,}행 중 {matched:,}행 썸네일 매핑 완료")

    df.to_csv(CSV_PATH, index=False)
    print(f"저장 완료: {CSV_PATH}")
    print(f"컬럼: {before_cols} → {list(df.columns)}")


if __name__ == "__main__":
    main()
