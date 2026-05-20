# YouTube 채널 데이터 필터링 작업 보고서

## 개요

개인 크리에이터 채널 데이터를 확보하기 위해 원본 수집 데이터에서 기업·공공기관·방송사 채널을 제거하는 작업을 수행하였습니다.

---

## 파일 구성

| 파일명 | 설명 |
|---|---|
| `youtube_channels_cleaned.csv` | 원본 수집 데이터 (변경 없음) |
| `youtube_channels_cleaned.tsv` | 정제 완료된 전체 채널 데이터 |
| `youtube_channels_filtered.tsv` | 기존 필터링된 채널 데이터 (구독자 기준 선별) |
| `youtube_channels_residue.tsv` | **최종 결과물** — cleaned에서 filtered 제외 후 추가 정제한 채널 데이터 |

---

## Step 1. CSV → TSV 변환

**대상 파일:** `youtube_channels_filtered.csv`, `youtube_channels_cleaned.csv`

일부 필드(예: `"2,040개"`)에 쉼표가 포함되어 `cut -d ','` 방식의 분리가 불가능하였습니다.  
Python `csv` 모듈로 따옴표 처리 후 탭 구분자(TSV)로 변환하였습니다.

---

## Step 2. cleaned 데이터 정제

### 2-1. 중복 제거

`youtube_channel_id` 기준으로 중복 행을 제거하였습니다.

| 구분 | 행 수 |
|---|---|
| 정제 전 | 8,191 |
| 중복 제거 후 | 8,180 |
| **제거된 행** | **11** |

### 2-2. 영상 수 기준 필터링

영상 수가 50개 미만인 채널을 제외하였습니다. (50개 이상 포함)

| 구분 | 행 수 |
|---|---|
| 중복 제거 후 | 8,180 |
| 필터링 후 | 7,218 |
| **제거된 행** | **962** |

### 2-3. channel_identifier 부여

`youtube_channels_filtered.tsv`에 이미 존재하는 채널은 기존 `channel_identifier`를 그대로 사용하고,  
나머지 채널에는 `CH07244`부터 순번으로 신규 부여하였습니다.

| 구분 | 수 |
|---|---|
| filtered에서 가져온 identifier | 3,352 |
| 신규 부여 (CH07244~CH11109) | 3,866 |

---

## Step 3. residue 파일 생성

`youtube_channels_cleaned.tsv`에서 `youtube_channels_filtered.tsv`에 포함된 채널을 제외하여  
`youtube_channels_residue.tsv`를 생성하였습니다.

| 구분 | 행 수 |
|---|---|
| cleaned | 7,218 |
| filtered (제외) | 3,352 |
| **residue 초기** | **3,866** |

---

## Step 4. residue 채널 추가 정제

개인 크리에이터 채널만 남기기 위해 기업·방송사·공공기관 채널을 단계적으로 제거하였습니다.

### 4-1. 카테고리 전체 제거

| 카테고리 | 제거 수 | 사유 |
|---|---|---|
| 회사/오피셜 | 174 | 브랜드·기업 공식 채널 |
| 뉴스/정치/사회 | 372 | 정치인·언론사·공공기관 채널 |
| **소계** | **546** | |

### 4-2. TV/방송 카테고리 세부 정제

TV/방송 카테고리는 개인 크리에이터가 혼재하므로 채널명 키워드 분석을 통해 단계적으로 제거하였습니다.

| 단계 | 제거 대상 | 제거 수 |
|---|---|---|
| 1차 | 기업/미디어 키워드 채널 (Korea, Media, Studio, Entertainment 등) | 25 |
| 2차 | 방송국 계열 채널 (KBS, MBC, SBS, JTBC, EBS, tvN 등) | 75 |
| 3차 | 방송 프로그램 채널 (아는형님, 놀면뭐하니, 그것이알고싶다 등) | 13 |
| 4차 | 기업/에이전시 채널 (TVING, TVCHOSUN, OBS, SK텔레콤, CJ ENM 등) | 7 |
| 5차 | 방송국 계열 잔류 (춘천엠비씨뮤직, M2) + 드라마/미디어 (clipservice, DRAMA Voyage, TV-People) + sNack! | 6 |
| **TV/방송 소계** | | **126** |

> **유지한 채널:** 개인 크리에이터 42개, 팬/덕질 채널 8개, 클립/숏츠 큐레이션 6개, 개인 추정 37개 등

### 4-3. 정제 결과 요약

| 구분 | 행 수 |
|---|---|
| residue 초기 | 3,866 |
| TV/방송 정제 제거 | 126 |
| 카테고리 전체 제거 | 546 |
| **최종 잔여** | **3,194** |

---

## 최종 결과: youtube_channels_residue.tsv

**총 3,194개 채널** — 개인 크리에이터 중심으로 정제된 데이터

| 카테고리 | 채널 수 |
|---|---|
| 미분류 | 764 |
| 키즈/어린이 | 446 |
| 게임 | 335 |
| 취미/라이프 | 257 |
| 음악/댄스/가수 | 256 |
| 음식/요리/레시피 | 161 |
| BJ/인물/연예인 | 157 |
| 패션/미용 | 123 |
| TV/방송 | 119 |
| 교육/강의 | 111 |
| 스포츠/운동 | 87 |
| 애완/반려동물 | 82 |
| 자동차 | 80 |
| 국내/해외/여행 | 75 |
| 영화/만화/애니 | 67 |
| IT/기술/컴퓨터 | 35 |
| 주식/경제/부동산 | 24 |
| 해외 | 15 |
| **합계** | **3,194** |

---

## 컬럼 설명

| 컬럼명 | 설명 |
|---|---|
| `channel_identifier` | 내부 고유 ID (CH + 5자리 숫자) |
| `channel_name` | 채널명 |
| `category` | 채널 분류 카테고리 |
| `subscriber_raw` | 구독자 수 원본 텍스트 |
| `subscriber_count` | 구독자 수 (정수) |
| `total_views_raw` | 총 조회수 원본 텍스트 |
| `total_views` | 총 조회수 (정수) |
| `video_count_raw` | 영상 수 원본 텍스트 |
| `video_count` | 영상 수 (정수) |
| `created_date` | 채널 개설일 |
| `latest_video_date` | 최근 영상 업로드일 |
| `days_since_latest_video` | 최근 영상으로부터 경과 일수 |
| `is_churned` | 이탈 여부 (1.0 = 이탈, 0.0 = 활성) |
| `youtube_channel_url` | 채널 URL |
| `youtube_channel_id` | YouTube 채널 고유 ID |
