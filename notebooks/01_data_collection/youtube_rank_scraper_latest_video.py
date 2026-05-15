"""
youtube-rank.com 크롤러
===============================================================

실행 전 설치:
    python -m pip install requests beautifulsoup4 pandas

선택 설치:
    python -m pip install lxml

실행 방법:
    python youtube_rank_scraper_latest_video.py                      # 기본값: 3페이지 테스트
    python youtube_rank_scraper_latest_video.py --pages 10           # 10페이지
    python youtube_rank_scraper_latest_video.py --pages 0            # 전체 수집
    python youtube_rank_scraper_latest_video.py --delay 1.5          # 요청 딜레이 조정
    python youtube_rank_scraper_latest_video.py --output my_data.csv # 저장 파일명 변경

주의:
    상세 페이지의 영상 목록에서 최신 업로드일을 추출해 is_churned를 계산합니다.
    영상 목록이 없거나 날짜를 찾을 수 없으면 latest_video_date와 is_churned는 비워둡니다.
"""

import argparse
import re
import time
from datetime import date, datetime
from urllib.parse import parse_qs, urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


BASE_URL = "https://youtube-rank.com/board/bbs/board.php"
SITE_ORIGIN = "https://youtube-rank.com"
BOARD_BASE = "https://youtube-rank.com/board/bbs/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://youtube-rank.com/",
}

CHURN_THRESHOLD_DAYS = 180
REQUEST_TIMEOUT = 15


def make_soup(html: str) -> BeautifulSoup:
    """lxml이 없을 수 있으므로 기본 파서로 파싱합니다."""
    return BeautifulSoup(html, "html.parser")


def parse_korean_number(text: str) -> int | None:
    """
    한글 단위 숫자를 정수로 변환합니다.

    예)
        '1억3000만'     -> 130000000
        '1327억5207만'  -> 132752070000
        '9980만'        -> 99800000
        '3,833'         -> 3833
        '646개'         -> 646
    """
    if text is None:
        return None

    text = str(text).strip().replace(",", "").replace(" ", "")
    text = re.sub(r"(명|회|개|건|위|단)$", "", text)

    if not text:
        return None

    if re.fullmatch(r"\d+", text):
        return int(text)

    result = 0.0

    eok_match = re.search(r"(\d+(?:\.\d+)?)억", text)
    man_match = re.search(r"(\d+(?:\.\d+)?)만", text)

    if eok_match:
        result += float(eok_match.group(1)) * 100_000_000
    if man_match:
        result += float(man_match.group(1)) * 10_000

    return int(result) if result > 0 else None


def days_since(date_str: str) -> int | None:
    """'YYYY-MM-DD HH:MM:SS' 또는 'YYYY-MM-DD'를 오늘 기준 경과 일수로 변환합니다."""
    if not date_str:
        return None

    try:
        dt = datetime.strptime(date_str.strip()[:10], "%Y-%m-%d").date()
        return (date.today() - dt).days
    except ValueError:
        return None


def is_churned(days: int | None) -> int | None:
    """경과 일수를 기준으로 이탈 여부를 반환합니다. 1=이탈 추정, 0=활동 추정, None=알 수 없음."""
    if days is None:
        return None
    return 1 if days >= CHURN_THRESHOLD_DAYS else 0


def normalize_site_url(href: str) -> str:
    """youtube-rank 내부 href를 절대 URL로 변환합니다."""
    if not href:
        return ""
    return urljoin(BOARD_BASE, href)


def request_soup(session: requests.Session, url: str, params: dict | None = None) -> BeautifulSoup:
    """GET 요청 후 BeautifulSoup 객체를 반환합니다."""
    res = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    res.raise_for_status()
    return make_soup(res.text)


def get_total_pages(session: requests.Session) -> int:
    """
    페이지네이션 링크에서 실제 마지막 페이지 번호를 추정합니다.

    주의:
      youtube-rank의 `전체 n건` 텍스트는 실제 목록 페이지 수와 맞지 않을 수 있어
      사용하지 않습니다.
    """
    params = {
        "bo_table": "youtube",
        "sst": "subscriber_cnt",
        "sod": "asc",
        "sop": "and",
        "page": 1,
    }
    soup = request_soup(session, BASE_URL, params=params)

    nums = []
    for a in soup.select("a[href*='page=']"):
        href = a.get("href", "")
        m = re.search(r"(?:[?&]|&)page=(\d+)", href)
        if m:
            nums.append(int(m.group(1)))

    return max(nums) if nums else 1


def parse_list_page(soup: BeautifulSoup) -> list[dict]:
    """목록 페이지에서 채널 기본 정보를 추출합니다."""
    channels = []

    for row in soup.select("tr"):
        tds = row.select("td")

        # 화면 기준 컬럼:
        # 0 순위 / 1 이미지 / 2 제목 / 3 구독자순 / 4 View순 / 5 Video순 / 6 조회수
        if len(tds) < 6:
            continue

        try:
            title_td = tds[2]

            a_tag = title_td.select_one("a[href*='wr_id=']") or title_td.select_one("a[href]")
            if not a_tag:
                continue

            detail_url = normalize_site_url(a_tag.get("href", ""))

            title_text = title_td.get_text(" ", strip=True)
            cat_match = re.search(r"\[([^\]]+)\]", title_text)
            category = cat_match.group(1).strip() if cat_match else ""

            channel_name = a_tag.get_text(" ", strip=True)
            channel_name = re.sub(r"\[[^\]]+\]", "", channel_name).strip()
            channel_name = re.sub(r"\s+", " ", channel_name)

            if not channel_name or len(channel_name) > 80:
                lines = [x.strip() for x in title_td.get_text("\n", strip=True).split("\n") if x.strip()]
                lines = [x for x in lines if not re.fullmatch(r"\[[^\]]+\]", x)]
                channel_name = lines[0] if lines else ""

            sub_raw = tds[3].get_text(" ", strip=True)
            view_raw = tds[4].get_text(" ", strip=True)
            vid_raw = tds[5].get_text(" ", strip=True)

            subscriber_count = parse_korean_number(sub_raw)
            if not channel_name or subscriber_count is None:
                continue

            channels.append(
                {
                    "channel_name": channel_name,
                    "category": category,
                    "subscriber_raw": sub_raw,
                    "subscriber_count": subscriber_count,
                    "total_views_raw": view_raw,
                    "total_views": parse_korean_number(view_raw),
                    "video_count_raw": vid_raw,
                    "video_count": parse_korean_number(vid_raw),
                    # 내부 상세 페이지 요청용으로만 사용하고 최종 CSV에는 저장하지 않습니다.
                    "_detail_url": detail_url,
                }
            )

        except Exception as e:
            print(f"  [목록 파싱 오류] {e}")
            continue

    return channels


def is_youtube_url(url: str) -> bool:
    if not url:
        return False
    host = urlparse(url).netloc.lower()
    return "youtube.com" in host or "youtu.be" in host


def extract_youtube_channel_id(url: str) -> str | None:
    """
    유튜브 URL에서 식별자를 추출합니다.

    우선순위:
      1) /channel/UC... -> UC... 만 반환
      2) /@handle      -> @handle 반환
      3) /c/name       -> c/name 반환
      4) /user/name    -> user/name 반환
    """
    if not url:
        return None

    patterns = [
        r"youtube\.com/channel/(UC[\w-]+)",
        r"youtube\.com/(@[\w.-]+)",
        r"youtube\.com/(c/[\w.-]+)",
        r"youtube\.com/(user/[\w.-]+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)

    return None


def resolve_youtube_url(session: requests.Session, link_php_url: str) -> tuple[str | None, str | None]:
    """
    youtube-rank의 link.php 중간 링크를 실제 유튜브 URL로 해석합니다.

    반환:
      (youtube_channel_url, youtube_channel_id)

    예:
      https://www.youtube.com/channel/UC13XC53dxI4gDTyIezj_NAA
      -> ('https://www.youtube.com/channel/UC13XC53dxI4gDTyIezj_NAA', 'UC13XC53dxI4gDTyIezj_NAA')
    """
    if not link_php_url:
        return None, None

    link_php_url = normalize_site_url(link_php_url)

    # 1) 가장 가벼운 방식: redirect를 따라가지 않고 Location만 확인
    try:
        res = session.get(link_php_url, allow_redirects=False, timeout=REQUEST_TIMEOUT)
        location = res.headers.get("Location") or res.headers.get("location")
        if location:
            final_url = urljoin(link_php_url, location)
            if is_youtube_url(final_url):
                return final_url, extract_youtube_channel_id(final_url)
    except Exception:
        pass

    # 2) fallback: 실제 redirect를 따라간 뒤 최종 URL 확인
    try:
        res = session.get(link_php_url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        final_url = res.url
        if is_youtube_url(final_url):
            return final_url, extract_youtube_channel_id(final_url)
    except Exception:
        pass

    return None, None


def find_youtube_link_candidates(soup: BeautifulSoup) -> list[str]:
    """상세 페이지에서 유튜브 이동 후보 링크를 수집합니다."""
    candidates = []

    # 1) 가장 정확한 기준: 유튜브 아이콘이 들어 있는 a 태그
    icon_links = soup.select("a:has(.sns-p-you)")
    for a in icon_links:
        href = a.get("href", "")
        if href:
            candidates.append(normalize_site_url(href))

    # 2) fallback: link.php 형태 전체를 후보로 넣음
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "link.php" in href:
            abs_url = normalize_site_url(href)
            if abs_url not in candidates:
                candidates.append(abs_url)

    # 3) 혹시 상세 페이지에 유튜브 URL이 직접 노출되는 경우
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if is_youtube_url(href):
            if href not in candidates:
                candidates.append(href)

    return candidates


def extract_channel_id_from_detail(soup: BeautifulSoup) -> str | None:
    """상세 페이지 내부 링크의 channel_id 파라미터에서 UC 채널 ID를 우선 추출합니다."""
    for a in soup.select("a[href*='channel_id=']"):
        href = a.get("href", "")
        query = urlparse(href).query
        channel_id = parse_qs(query).get("channel_id", [None])[0]
        if channel_id:
            return channel_id
    return None


def parse_latest_video_date(soup: BeautifulSoup) -> str | None:
    """상세 페이지의 영상 목록(tr.play_li) 안에서만 최신 업로드일을 추출합니다."""
    video_dates = []

    for row in soup.select("tr.play_li"):
        for h2 in row.select("td.subject h2"):
            txt = h2.get_text(" ", strip=True)
            m = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", txt)
            if m:
                video_dates.append(m.group(0))

    return max(video_dates) if video_dates else None


def parse_detail_page(session: requests.Session, soup: BeautifulSoup) -> dict:
    """상세 페이지에서 생성일, 최신 영상 업로드일, 유튜브 채널 ID/URL을 추출합니다."""
    info = {
        "created_date": None,
        "latest_video_date": None,
        "days_since_latest_video": None,
        "is_churned": None,
        "youtube_channel_url": None,
        "youtube_channel_id": None,
    }

    text = soup.get_text("\n", strip=True)

    created_m = re.search(
        r"생성날짜\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)",
        text,
    )
    if created_m:
        info["created_date"] = created_m.group(1).strip()

    # 실제 활동성 판단용: 상세 페이지의 영상 목록(tr.play_li) 내부 날짜만 사용
    latest_video_date = parse_latest_video_date(soup)
    if latest_video_date:
        info["latest_video_date"] = latest_video_date
        info["days_since_latest_video"] = days_since(latest_video_date)
        info["is_churned"] = is_churned(info["days_since_latest_video"])

    # 1순위: 상세 페이지 내부의 정보 수정 요청 링크에 포함된 channel_id 파라미터
    direct_channel_id = extract_channel_id_from_detail(soup)
    if direct_channel_id:
        info["youtube_channel_id"] = direct_channel_id
        info["youtube_channel_url"] = f"https://www.youtube.com/channel/{direct_channel_id}"
        return info

    # 2순위 fallback: 유튜브 버튼(link.php) 리다이렉션 또는 직접 노출 URL
    for candidate in find_youtube_link_candidates(soup):
        if is_youtube_url(candidate):
            yt_url = candidate
            ch_id = extract_youtube_channel_id(yt_url)
        else:
            yt_url, ch_id = resolve_youtube_url(session, candidate)

        if yt_url:
            info["youtube_channel_url"] = yt_url
            info["youtube_channel_id"] = ch_id
            break

    return info


def crawl(max_pages: int = 3, delay: float = 1.0, output: str = "youtube_channels.csv") -> pd.DataFrame:
    session = requests.Session()
    session.headers.update(HEADERS)

    if max_pages == 0:
        print("전체 페이지 수 확인 중...")
        total_pages = get_total_pages(session)
        print(f"전체 페이지: {total_pages}페이지")
        max_pages = total_pages
    else:
        print(f"테스트 모드: {max_pages}페이지만 수집")

    all_channels = []
    empty_streak = 0
    empty_streak_limit = 3

    for page in range(1, max_pages + 1):
        print(f"[목록] {page}/{max_pages} 페이지 수집 중...", end=" ")
        params = {
            "bo_table": "youtube",
            "sst": "subscriber_cnt",
            "sod": "asc",
            "sop": "and",
            "page": page,
        }

        try:
            soup = request_soup(session, BASE_URL, params=params)
            rows = parse_list_page(soup)

            if rows:
                all_channels.extend(rows)
                empty_streak = 0
                print(f"{len(rows)}개 채널 수집")
            else:
                empty_streak += 1
                print(f"0개 채널 수집 | 빈 페이지 연속 {empty_streak}/{empty_streak_limit}")

                if empty_streak >= empty_streak_limit:
                    print(f"연속 {empty_streak_limit}페이지에서 채널이 없어 목록 수집을 종료합니다.")
                    break

        except Exception as e:
            empty_streak += 1
            print(f"오류: {e} | 실패 연속 {empty_streak}/{empty_streak_limit}")

            if empty_streak >= empty_streak_limit:
                print(f"연속 {empty_streak_limit}페이지 요청/파싱 실패로 목록 수집을 종료합니다.")
                break

        time.sleep(delay)

    print(f"\n목록 수집 완료: 총 {len(all_channels)}개 채널")

    print("\n상세 페이지 수집 시작...")
    for i, ch in enumerate(all_channels, start=1):
        print(f"  [{i}/{len(all_channels)}] {ch['channel_name'][:30]}", end=" ")

        try:
            soup = request_soup(session, ch["_detail_url"])
            detail = parse_detail_page(session, soup)
            ch.update(detail)
            print(
                f"→ 최신영상: {ch.get('latest_video_date') or 'N/A'} | "
                f"경과: {ch.get('days_since_latest_video') if ch.get('days_since_latest_video') is not None else 'N/A'}일 | "
                f"이탈: {ch.get('is_churned') if ch.get('is_churned') is not None else 'N/A'} | "
                f"YT ID: {ch.get('youtube_channel_id') or 'N/A'}"
            )
        except Exception as e:
            print(f"오류: {e}")

        time.sleep(delay)

    df = pd.DataFrame(all_channels)

    # 내부 작업용 컬럼 제거
    if "_detail_url" in df.columns:
        df = df.drop(columns=["_detail_url"])

    col_order = [
        "channel_name",
        "category",
        "subscriber_raw",
        "subscriber_count",
        "total_views_raw",
        "total_views",
        "video_count_raw",
        "video_count",
        "created_date",
        "latest_video_date",
        "days_since_latest_video",
        "is_churned",
        "youtube_channel_url",
        "youtube_channel_id",
    ]

    existing_cols = [c for c in col_order if c in df.columns]
    df = df[existing_cols] if existing_cols else df

    df.to_csv(output, index=False, encoding="utf-8-sig")

    churn_count = df["is_churned"].sum() if "is_churned" in df.columns else "N/A"
    yt_id_count = df["youtube_channel_id"].notna().sum() if "youtube_channel_id" in df.columns else "N/A"

    print(f"\n저장 완료: {output}")
    print(f"총 {len(df)}개 채널 | 이탈 추정 채널: {churn_count}개 | 유튜브 ID 수집: {yt_id_count}개")
    print("\n=== 컬럼 설명 ===")
    print("subscriber_raw       : 원본 한글 표기")
    print("subscriber_count     : 변환된 정수")
    print("total_views          : 변환된 총 조회수")
    print("video_count          : 변환된 영상 수")
    print("latest_video_date       : 상세 페이지 영상 목록 기준 최신 업로드일")
    print("days_since_latest_video : 최신 영상 업로드일로부터 경과 일수")
    print(f"is_churned           : 이탈 추정 여부 (1=이탈 추정, 0=활동 추정) — 기준: {CHURN_THRESHOLD_DAYS}일")
    print("youtube_channel_url  : link.php가 아닌 실제 유튜브 URL")
    print("youtube_channel_id   : /channel/UC...면 UC...만, 그 외 @handle/c/user 값")

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="youtube-rank.com 크롤러")
    parser.add_argument("--pages", type=int, default=3, help="수집할 페이지 수 (0=전체)")
    parser.add_argument("--delay", type=float, default=1.0, help="요청 간 딜레이 초")
    parser.add_argument("--output", type=str, default="youtube_channels.csv", help="저장 파일명")
    args = parser.parse_args()

    crawl(max_pages=args.pages, delay=args.delay, output=args.output)
