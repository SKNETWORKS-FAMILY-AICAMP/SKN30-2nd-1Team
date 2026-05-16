"""
04_channel_info.ipynb 배치 자동화 스크립트
=========================================
youtube_channels_cleaned.csv 의 0~1999 행을 50개씩 끊어
channels.list API 로 수집하고 JSON + MUST CSV 를 저장한다.

실행:
    python notebooks/01_data_collection/run_channel_batch.py
    python notebooks/01_data_collection/run_channel_batch.py --start 0 --end 1999 --step 50
    python notebooks/01_data_collection/run_channel_batch.py --start 900 --end 1999  # 이어서
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

PARTS = 'snippet,contentDetails,statistics,topicDetails,brandingSettings,status'
QUOTA_REASONS = {
    'quotaExceeded',
    'rateLimitExceeded',
    'dailyLimitExceeded',
    'userRateLimitExceeded',
}

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / 'data' / 'raw' / 'youtube_channels_cleaned.csv'
JSON_DIR = ROOT / 'data' / 'raw' / 'channels' / 'json'
CSV_DIR = ROOT / 'data' / 'raw' / 'channels' / 'csv'


def fetch_batch(youtube, channel_ids):
    resp = youtube.channels().list(
        part=PARTS,
        id=','.join(channel_ids),
        maxResults=50,
    ).execute()
    return resp.get('items', [])


def extract_must(items):
    rows = []
    for item in items:
        s = item.get('snippet', {})
        cd = item.get('contentDetails', {}).get('relatedPlaylists', {})
        st = item.get('statistics', {})
        rows.append({
            'channel_id': item['id'],
            'title': s.get('title'),
            'published_at': s.get('publishedAt'),
            'country': s.get('country'),
            'uploads_playlist': cd.get('uploads'),
            'subscriber_count': st.get('subscriberCount'),
            'view_count': st.get('viewCount'),
            'video_count': st.get('videoCount'),
        })
    return pd.DataFrame(rows)


def save_batch(items, start, end):
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    json_path = JSON_DIR / f'channels_raw_{start}_{end}.json'
    csv_path = CSV_DIR / f'channels_must_{start}_{end}.csv'
    json_path.write_text(
        json.dumps(items, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    extract_must(items).to_csv(csv_path, index=False, encoding='utf-8-sig')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--start', type=int, default=0)
    p.add_argument('--end', type=int, default=1999, help='inclusive')
    p.add_argument('--step', type=int, default=50)
    p.add_argument('--sleep', type=float, default=0.0,
                   help='배치 간 대기 (초). 기본 0')
    args = p.parse_args()

    load_dotenv(ROOT / '.env')
    api_key = os.getenv('YOUTUBE_API_KEY')
    assert api_key, '.env 의 YOUTUBE_API_KEY 가 필요합니다'
    youtube = build('youtube', 'v3', developerKey=api_key)

    df_all = pd.read_csv(CSV_PATH)
    total = len(df_all)
    end_clamped = min(args.end, total - 1)

    print(f'전체 채널: {total:,} / 처리 범위: {args.start} ~ {end_clamped} '
          f'(step={args.step})', flush=True)

    for batch_start in range(args.start, end_clamped + 1, args.step):
        batch_end = min(batch_start + args.step - 1, end_clamped)
        ids = df_all['youtube_channel_id'].iloc[batch_start:batch_end + 1].tolist()
        print(f'[{batch_start:>5}..{batch_end:<5}] {len(ids)}개 요청', flush=True)
        try:
            items = fetch_batch(youtube, ids)
        except HttpError as e:
            reason = (
                e.error_details[0]['reason']
                if e.error_details else f'HTTP {e.resp.status}'
            )
            print(f'  ✗ API 에러: {reason} — 중단')
            print(f'▶ 다음 실행: --start {batch_start} --end {args.end}')
            sys.exit(1 if reason in QUOTA_REASONS else 2)
        save_batch(items, batch_start, batch_end)
        print(f'  ✓ 저장: channels_raw_{batch_start}_{batch_end}.json '
              f'(응답 {len(items)}개)', flush=True)
        if args.sleep:
            time.sleep(args.sleep)

    print(f'\n✓ 완료: {args.start} ~ {end_clamped}')


if __name__ == '__main__':
    main()
