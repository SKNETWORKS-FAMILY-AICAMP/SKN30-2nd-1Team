---
name: dba
description: 튜브어때 서비스의 콘텐츠/데이터 모델 계층 — YouTube API 수집, CSV 스키마 정의, 전처리, 데이터 품질을 책임진다. 모델링 로직이나 UI 렌더링은 다루지 않는다.
---

# DBA Skill (튜브어때 — Data & Content Model)

## Objective

YouTube 채널·영상·댓글 데이터를 **수집·정제·저장**하여, Business Logic 계층이 일관되게 소비할 수 있는 **신뢰 가능한 데이터 자산**을 제공한다.
MVP에서는 DB를 사용하지 않고 **CSV 파일** 기반(`data/`)으로 콘텐츠 모델을 운영한다 (PRD §11, §14).

데이터 계층의 핵심 책임은 다음 세 가지다:

1. YouTube Data API v3로부터 채널/영상/댓글을 안정적으로 수집한다.
2. 수집 데이터를 [docs/튜브어때_PRD.md](../../../docs/튜브어때_PRD.md) §14-2의 CSV 스키마로 정규화한다.
3. 데이터 일자(스냅샷 기준일), 누락, 중복, 쿼터 실패를 추적·관리한다.

## Scope

### 포함 (In Scope)

- **YouTube Data API v3 수집** (PRD §9-1)
  - `channels` / `videos` / `search` / `commentThreads` endpoint 호출
  - 다중 API 키 로테이션, 일일 쿼터 추적
- **수집 결과 저장** (PRD §14-1)
  - `data/raw/{channels,videos,comments}/` 에 원본 응답 보관
  - 실패 채널은 `failed_channels_*.csv`로 격리
- **전처리·정규화** (PRD §14-2)
  - `channels.csv`, `videos.csv`, `comments.csv` 스키마 강제
  - 타입 변환, 결측 처리, 중복 제거, 시간대 통일(UTC 또는 KST 일관성)
- **데이터 품질·메타데이터 관리**
  - `last_collected_at` 기록
  - 스냅샷 기준일 명시 (예: 2026-05-17)
  - 채널 ID/URL 정규화 (사용자 입력 `@handle` ↔ `UCxxxx` 매핑)
- **데이터 버전 관리**
  - 대용량 파일은 `.gitignore`로 제외하되, 스키마 정의·샘플은 추적
  - 데이터 산출일 기준 디렉터리/파일명 규칙 유지

### 제외 (Out of Scope — 다른 계층에 위임)

- **Feature Engineering 계산식** (`upload_interval_30d`, `engagement_rate` 등) → Business Logic 계층 ([business-logic/SKILL.md](../business-logic/SKILL.md))
- **댓글 감성 점수 산정 로직(KoBERT)** → Business Logic 계층
  - 단, `comments.csv`의 `sentiment_score` / `sentiment_label` 컬럼 **자리**(스키마)는 본 계층이 정의
- **이탈 라벨링(90일 룰)** → Business Logic 계층
- **차트, 대시보드, 입력 UI** → Designer 계층 ([designer/SKILL.md](../designer/SKILL.md))

## Key Responsibilities

1. **CSV 스키마의 단일 진실 공급원(Single Source of Truth) 유지**
   - PRD §14-2의 컬럼·타입을 강제하는 **스키마 검증 유틸**을 제공한다 (예: `pandera`, 수동 assert).
   - 스키마 변경은 Business Logic·Designer 계층과 합의 후, PRD 갱신과 함께 수행한다.

2. **재현 가능한 수집 파이프라인 제공**
   - 동일한 채널 리스트 입력 → 동일한 출력 CSV가 보장되어야 한다 (단, 시간 의존 필드 제외).
   - 수집 스크립트 진입점을 명확히 한다 (예: `src/data_collection/...`).

3. **API 쿼터·실패 추적** (PRD §9-3, §17)
   - 일일 10,000 units / 키 한도를 추적하고, 다중 키 로테이션을 자동화한다.
   - 실패 채널은 `data/raw/failed_channels_YYYYMMDD.csv`에 사유와 함께 적재해 재시도 가능하게 한다.
   - 비공개 댓글 채널은 `comments.csv`에서 누락된 채로 두고, **임의 더미를 생성하지 않는다**.

4. **스냅샷 기준일 보장**
   - 모든 정제 데이터셋은 `last_collected_at` 또는 산출 파일명(`predictions_YYYYMMDD.csv`)으로 기준일을 추적 가능해야 한다.
   - MVP는 **2026-05-17 스냅샷** 단일 기준 (PRD §6-1, §19).

5. **채널 식별자 정규화**
   - 사용자가 URL(`https://www.youtube.com/@channelname`)을 입력해도 내부적으로 `UCxxxx` 채널 ID로 매핑되도록 lookup 테이블을 유지한다.
   - 매핑되지 않는 입력은 명시적으로 "분석 불가" 신호를 Business Logic 계층에 전달한다.

6. **개인정보·정책 준수** (PRD §20)
   - 공개 API 응답만 수집한다. 비공개 정보, 추정된 이메일/전화번호 등은 저장하지 않는다.
   - 데이터가 외부 공유될 수 있다면 채널/사용자 식별자 익명화를 검토한다.

## Constraints & Guidelines

### 계층 경계 (Boundary Rules)

- **비즈니스 로직 침범 금지**: `engagement_rate`, `view_growth_rate` 같은 **파생 feature는 본 계층에서 계산하지 않는다**. CSV에는 raw 값(`view_count`, `like_count`, `comment_count`, `published_at`)까지만 저장한다.
  - 단, 본 계층의 "전처리" 범위(타입 변환, 결측 마스킹, 중복 제거)는 허용된다.
- **모델 학습·추론 코드 작성 금지**: 학습 파이프라인은 Business Logic 계층의 책임이다.
- **UI 호출·렌더링 금지**: Streamlit/Plotly를 import하지 않는다.

### 데이터 정책

- **MVP는 1회성 배치 수집** (PRD §9-4). 정기 크롤링은 향후 확장 (PRD §21).
- 원본은 `data/raw/`에 그대로 보존하고, `data/processed/`는 재생성 가능한 파생 산출물로만 다룬다.
- 대용량 raw 파일은 `.gitignore` 처리하되, 스키마·샘플(상위 N행)은 추적해도 좋다.
- **데이터 손상 방지**: `data/processed/*.csv`를 덮어쓸 때는 임시 파일에 쓰고 atomic rename으로 교체.

### 스키마 변경 절차

1. 변경 필요성을 Business Logic / Designer 계층과 사전 합의
2. PRD §14-2 갱신
3. 스키마 검증 유틸 갱신
4. 다운스트림(모델·UI)이 깨지지 않는지 확인 후 머지

### 코드 위치

- 수집 스크립트: [src/](../../../src/) 하위 (예: `src/data_collection/`)
- 원본 데이터: [data/raw/](../../../data/raw/)
- 정제 데이터: [data/processed/](../../../data/processed/)
- 예측 결과 저장 위치: [data/predictions/](../../../data/predictions/) (쓰기 주체는 Business Logic이지만 디렉터리·파일명 규칙은 본 계층이 정의)
- API 키·쿼터 설정: [configs/](../../../configs/) 또는 환경변수(`.env`)

### 변경 시 체크리스트

- [ ] PRD §14-2 스키마와 CSV 컬럼·타입이 일치하는가?
- [ ] `last_collected_at` 또는 스냅샷 기준일이 누락되지 않았는가?
- [ ] 실패 채널이 별도 파일로 격리되었는가?
- [ ] 비공개/민감 정보가 저장되지 않는가?
- [ ] Business Logic 계층의 입력 가정(컬럼명, 타입, NaN 정책)을 깨뜨리지 않는가?
