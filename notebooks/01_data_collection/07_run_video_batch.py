"""
05_video_info.ipynb 배치 자동화 스크립트
=========================================
data/raw/channels/csv/channels_must_{start}_{end}.csv 의 채널들에 대해
playlistItems.list + videos.list 를 호출하여
영상 정보 JSON + MUST CSV 를 저장한다.

실행:
    python notebooks/01_data_collection/run_video_batch.py
    python notebooks/01_data_collection/run_video_batch.py --start 0 --end 1999 --step 50
    python notebooks/01_data_collection/run_video_batch.py --start 900 --end 1999  # 이어서
"""
import argparse
import json
import os
import re
import socket
import ssl
import sys
import time
from pathlib import Path

import httplib2
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

TRANSIENT_EXC = (
    OSError,
    socket.error,
    socket.timeout,
    ssl.SSLError,
    httplib2.HttpLib2Error,
    TimeoutError,
    ConnectionError,
)
MAX_RETRIES = 5

VIDEO_PARTS = (
    'snippet,contentDetails,statistics,status,'
    'topicDetails,recordingDetails,localizations'
)
QUOTA_REASONS = {
    'quotaExceeded',
    'rateLimitExceeded',
    'dailyLimitExceeded',
    'userRateLimitExceeded',
}
MAX_VIDEOS_PER_CHANNEL = 50
REQUEST_DELAY_SEC = 0.5

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / 'data' / 'raw' / 'youtube_channels_cleaned.csv'
CHANNELS_CSV_DIR = ROOT / 'data' / 'raw' / 'channels' / 'csv'
OUT_DIR = ROOT / 'data' / 'raw' / 'videos'
JSON_DIR = OUT_DIR / 'json'
CSV_DIR = OUT_DIR / 'csv'


def err_reason(e: HttpError) -> str:
    try:
        return e.error_details[0]['reason']
    except Exception:
        return f'HTTP {e.resp.status}'


def is_quota_error(e: HttpError) -> bool:
    return err_reason(e) in QUOTA_REASONS


def execute_with_retry(request, label=''):
    """일시적 네트워크/소켓 오류는 지수 백오프로 재시도. HttpError 는 그대로 전파."""
    for attempt in range(MAX_RETRIES):
        try:
            return request.execute()
        except HttpError:
            raise
        except TRANSIENT_EXC as e:
            wait = min(30, 2 ** attempt)
            print(f'      ⚠ transient {label} ({type(e).__name__}: {e}) — '
                  f'{wait}s 후 재시도 ({attempt + 1}/{MAX_RETRIES})',
                  flush=True)
            time.sleep(wait)
    return request.execute()  # 마지막 시도, 예외 전파


def get_playlist_videos(youtube, playlist_id, max_results=50):
    items = []
    next_page = None
    while len(items) < max_results:
        kwargs = dict(
            part='snippet,contentDetails,status',
            playlistId=playlist_id,
            maxResults=min(50, max_results - len(items)),
        )
        if next_page:
            kwargs['pageToken'] = next_page
        resp = execute_with_retry(youtube.playlistItems().list(**kwargs),
                                  label='playlistItems')
        items.extend(resp.get('items', []))
        next_page = resp.get('nextPageToken')
        if not next_page:
            break
        time.sleep(REQUEST_DELAY_SEC)
    return items


def get_video_details(youtube, video_ids):
    all_items = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        resp = execute_with_retry(
            youtube.videos().list(part=VIDEO_PARTS, id=','.join(batch)),
            label='videos.list',
        )
        all_items.extend(resp.get('items', []))
        time.sleep(REQUEST_DELAY_SEC)
    return all_items


def parse_duration_sec(iso_duration):
    if not iso_duration:
        return None
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not m:
        return None
    h, mn, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mn * 60 + s


def build_combined_df(df_ch, playlist_data, video_data, idx_map):
    """notebook Cell 30 의 MUST 통합 CSV 와 동일한 구조"""
    playlist_rows = []
    for cid, items in playlist_data.items():
        for it in items:
            s = it.get('snippet', {})
            cd = it.get('contentDetails', {})
            playlist_rows.append({
                'idx': idx_map.get(cid),
                'channel_id': cid,
                'video_id': cd.get('videoId'),
                'video_title': s.get('title'),
                'published_at': s.get('publishedAt'),
            })
    df_pl = pd.DataFrame(
        playlist_rows,
        columns=['idx', 'channel_id', 'video_id', 'video_title', 'published_at'],
    )

    content_rows = []
    stats_rows = []
    for cid, videos in video_data.items():
        for v in videos:
            cd = v.get('contentDetails', {})
            dur = parse_duration_sec(cd.get('duration'))
            content_rows.append({
                'video_id': v['id'],
                'duration_sec': dur,
                'is_shorts': (dur is not None and dur <= 60),
            })
            st = v.get('statistics', {})
            stats_rows.append({
                'video_id': v['id'],
                'view_count': st.get('viewCount'),
                'like_count': st.get('likeCount'),
                'comment_count': st.get('commentCount'),
            })
    df_content = pd.DataFrame(
        content_rows,
        columns=['video_id', 'duration_sec', 'is_shorts'],
    )
    df_stats = pd.DataFrame(
        stats_rows,
        columns=['video_id', 'view_count', 'like_count', 'comment_count'],
    )
    for col in ['view_count', 'like_count', 'comment_count']:
        df_stats[col] = pd.to_numeric(df_stats[col], errors='coerce')

    df_combined = (
        df_pl
        .merge(
            df_ch[['channel_id', 'title']].rename(columns={'title': 'channel_title'}),
            on='channel_id', how='left',
        )
        .merge(df_content, on='video_id', how='left')
        .merge(df_stats, on='video_id', how='left')
    )

    return df_combined[[
        'idx',
        'channel_id', 'channel_title',
        'video_id', 'video_title',
        'published_at', 'duration_sec', 'is_shorts',
        'view_count', 'like_count', 'comment_count',
    ]].sort_values(['idx', 'published_at']).reset_index(drop=True)


def process_batch(youtube, df_all, batch_start, batch_end):
    """단일 배치 처리. 반환: (status, last_done_idx)
    status: 'ok' | 'quota' | 'no_channels'
    """
    must_path = CHANNELS_CSV_DIR / f'channels_must_{batch_start}_{batch_end}.csv'
    if not must_path.exists():
        print(f'  ✗ 채널 CSV 없음: {must_path.name} — 스킵', flush=True)
        return 'no_channels', None

    df_must = pd.read_csv(must_path)

    df_slice = df_all.iloc[batch_start:batch_end + 1][['idx', 'youtube_channel_id']].copy()
    df_slice = df_slice.rename(columns={'youtube_channel_id': 'channel_id'})
    df_ch = (
        df_slice
        .merge(df_must, on='channel_id', how='left')
        .sort_values('idx')
        .reset_index(drop=True)
    )

    playlist_data = {}
    video_data = {}
    idx_map = {}
    last_done_idx = None
    quota_hit = False

    for _, row in df_ch.iterrows():
        cid = row['channel_id']
        idx = int(row['idx'])
        title = row.get('title', cid)
        playlist_id = row.get('uploads_playlist')
        idx_map[cid] = idx

        if not playlist_id or pd.isna(playlist_id):
            print(f'    [{idx:>4}] SKIP {title} — uploads_playlist 없음', flush=True)
            last_done_idx = idx
            continue

        try:
            items = get_playlist_videos(youtube, playlist_id, MAX_VIDEOS_PER_CHANNEL)
            playlist_data[cid] = items
        except HttpError as e:
            reason = err_reason(e)
            if is_quota_error(e):
                print(f'    [{idx:>4}] ✗ QUOTA (playlistItems) — {reason}', flush=True)
                quota_hit = True
                break
            print(f'    [{idx:>4}] ✗ playlistItems {reason}', flush=True)
            last_done_idx = idx
            time.sleep(REQUEST_DELAY_SEC)
            continue

        video_ids = [
            it['contentDetails']['videoId']
            for it in items
            if it.get('contentDetails', {}).get('videoId')
        ]
        if video_ids:
            try:
                video_data[cid] = get_video_details(youtube, video_ids)
            except HttpError as e:
                reason = err_reason(e)
                if is_quota_error(e):
                    print(f'    [{idx:>4}] ✗ QUOTA (videos.list) — {reason}', flush=True)
                    playlist_data.pop(cid, None)
                    quota_hit = True
                    break
                print(f'    [{idx:>4}] ✗ videos.list {reason}', flush=True)

        json_path = JSON_DIR / f'{idx:04d}_{cid}.json'
        payload = {
            'idx': idx,
            'channel_id': cid,
            'channel_title': title,
            'playlist_items': playlist_data.get(cid, []),
            'video_details': video_data.get(cid, []),
        }
        json_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )
        last_done_idx = idx
        time.sleep(REQUEST_DELAY_SEC)

    if last_done_idx is None:
        return ('quota' if quota_hit else 'ok'), None

    df_combined = build_combined_df(df_ch, playlist_data, video_data, idx_map)
    range_end = last_done_idx
    suffix = '_partial' if quota_hit else ''
    out_csv = CSV_DIR / f'videos_{batch_start:04d}-{range_end:04d}{suffix}.csv'
    df_combined.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(
        f'    ✓ {out_csv.name}  영상 {len(df_combined)}행 / '
        f'채널 {df_combined["idx"].nunique()}/{len(df_ch)}',
        flush=True,
    )
    return ('quota' if quota_hit else 'ok'), last_done_idx


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--start', type=int, default=0)
    p.add_argument('--end', type=int, default=1999, help='inclusive')
    p.add_argument('--step', type=int, default=50)
    p.add_argument('--sleep', type=float, default=0.0,
                   help='배치 간 대기 (초). 기본 0')
    p.add_argument('--skip-existing', action='store_true', default=True,
                   help='이미 저장된 배치 CSV 가 있으면 스킵 (기본 on)')
    p.add_argument('--no-skip-existing', dest='skip_existing',
                   action='store_false')
    args = p.parse_args()

    load_dotenv(ROOT / '.env')
    api_key = os.getenv('YOUTUBE_API_KEY')
    assert api_key, '.env 의 YOUTUBE_API_KEY 가 필요합니다'
    youtube = build('youtube', 'v3', developerKey=api_key)

    JSON_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    df_all = pd.read_csv(CSV_PATH).reset_index().rename(columns={'index': 'idx'})
    total = len(df_all)
    end_clamped = min(args.end, total - 1)

    print(
        f'전체 채널: {total:,} / 처리 범위: {args.start} ~ {end_clamped} '
        f'(step={args.step}, skip_existing={args.skip_existing})',
        flush=True,
    )

    for batch_start in range(args.start, end_clamped + 1, args.step):
        batch_end = min(batch_start + args.step - 1, end_clamped)
        existing = CSV_DIR / f'videos_{batch_start:04d}-{batch_end:04d}.csv'
        if args.skip_existing and existing.exists():
            print(f'[{batch_start:>4}..{batch_end:<4}] ⏭  이미 있음: {existing.name}',
                  flush=True)
            continue

        print(f'[{batch_start:>4}..{batch_end:<4}] 처리 시작', flush=True)
        status, last_done = process_batch(youtube, df_all, batch_start, batch_end)

        if status == 'quota':
            resume = (last_done + 1) if last_done is not None else batch_start
            print(f'\n⚠ API quota 소진 — 다음 실행:', flush=True)
            print(f'  python notebooks/01_data_collection/run_video_batch.py '
                  f'--start {resume} --end {args.end}',
                  flush=True)
            sys.exit(1)

        if args.sleep:
            time.sleep(args.sleep)

    print(f'\n✓ 완료: {args.start} ~ {end_clamped}', flush=True)


if __name__ == '__main__':
    main()
