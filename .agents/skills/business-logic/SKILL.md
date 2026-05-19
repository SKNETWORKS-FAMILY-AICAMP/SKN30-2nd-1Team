---
name: business-logic
description: 튜브어때 서비스의 비즈니스 로직 계층 — 이탈 위험도 예측 모델, 추천 알고리즘, SHAP 기반 설명, 댓글 감성 분석 파이프라인을 책임진다. 데이터 스키마 변경이나 UI 렌더링은 다루지 않는다.
---

# Business Logic Skill (튜브어때)

## Objective

YouTube 채널의 **이탈 위험도 예측**과 **광고주 추천**을 수행하는 비즈니스 로직 계층을 설계·구현·유지보수한다.
입력은 DBA 계층이 제공한 정제된 CSV (`data/processed/*.csv`)이며, 출력은 Designer 계층이 소비하는 **예측 결과 객체/CSV** (`data/predictions/*.csv`)이다.

비즈니스 로직 계층의 핵심은 다음 세 가지 의사결정을 데이터로부터 도출하는 것이다:

1. 이 채널은 향후 90일 내 이탈할 위험이 얼마나 높은가? (위험도 점수 + A/B/C 등급)
2. 광고 목적(장기 계약 / 단기 캠페인 / 위험 채널 탐지)에 맞는 채널은 무엇인가?
3. 그 판단의 근거(SHAP Top-3)는 무엇인가?

## Scope

### 포함 (In Scope)

- **Feature Engineering 로직** ([docs/튜브어때_PRD.md](../../../docs/튜브어때_PRD.md) §10)
  - 업로드 패턴, 조회수/성장, 참여율, 댓글 감성 feature 계산식 구현
  - 결측치/이상치 처리 규칙 정의
- **라벨링 로직** (PRD §12-1)
  - 이탈 정의(90일 무업로드) 적용
  - 시즌제 채널·단기 휴재 채널 예외 처리
- **모델 학습·튜닝·평가** (PRD §12)
  - Logistic Regression / RandomForest / XGBoost / LightGBM 학습 파이프라인
  - KoBERT 기반 댓글 감성 분류기 학습/추론
  - 평가 지표: Recall(최우선) / Precision / F1 / ROC-AUC / PR-AUC
  - 클래스 불균형 처리: `class_weight`, SMOTE(학습 한정), Threshold Tuning
- **추천 알고리즘** (PRD §6-2)
  - 장기 계약 / 단기 캠페인 / 위험 탐지 추천 기준 구현
- **SHAP 해석** (PRD §6-4)
  - 각 채널 예측의 위험 원인 Top-3 추출
- **모델 산출물 관리**
  - 학습된 모델을 [saved_models/](../../../saved_models/)에 버전 태그와 함께 저장
  - 예측 결과를 `data/predictions/predictions_YYYYMMDD.csv` 스키마(PRD §14-2)에 맞춰 기록

### 제외 (Out of Scope — 다른 계층에 위임)

- **데이터 수집/스키마 정의** → DBA 계층 ([dba/SKILL.md](../dba/SKILL.md))
- **CSV 컬럼 추가/제거/타입 변경** → DBA 계층과 합의 후 진행
- **화면 렌더링·차트 스타일·UX 플로우** → Designer 계층 ([designer/SKILL.md](../designer/SKILL.md))
- **사용자 입력 검증 UI** → Designer 계층 (단, 비즈니스 규칙 자체는 본 계층이 정의)

## Key Responsibilities

1. **재현 가능한 학습 파이프라인 제공**
   - `src/` 하위에 학습/추론 모듈을 두고, 동일한 입력 CSV → 동일한 모델 산출물이 보장되어야 한다.
   - 랜덤 시드, 데이터 분할 방식, 하이퍼파라미터를 [configs/](../../../configs/)에 명시한다.

2. **이탈 정의의 일관성 유지**
   - "90일 무업로드 = 이탈(1)"이라는 PRD §12-1 정의를 모든 학습/평가/추론 코드에서 단일 함수로 적용한다.
   - 시즌제 채널 예외는 카테고리 기준으로 분리한다.

3. **Recall 우선 평가**
   - 모델 선정 시 **Recall ≥ 80% (KPI)** 를 만족하지 못하면 채택하지 않는다.
   - Threshold는 검증 세트의 Recall 곡선을 기준으로 튜닝한다.

4. **설명 가능성 보장**
   - 모든 예측은 SHAP Top-3 위험 요인을 함께 산출해야 한다 (Designer가 렌더링).

5. **추론 성능 KPI 충족**
   - 채널당 분석 처리 시간 **5초 이내** (PRD §22).
   - 무거운 전처리는 사전 배치로 위임하고, 추론 시점에는 feature lookup만 수행한다.

6. **예측 결과 스키마 준수**
   - `predictions_YYYYMMDD.csv` 컬럼(`channel_id`, `predicted_at`, `risk_score`, `risk_grade`, `top_risk_factors`, `model_version`)을 반드시 지킨다.
   - 스키마 변경이 필요하면 **반드시 DBA 계층과 합의 후** PRD를 갱신한다.

## Constraints & Guidelines

### 계층 경계 (Boundary Rules)

- **데이터 스키마 변경 금지**: `channels.csv` / `videos.csv` / `comments.csv` 컬럼을 임의로 추가·변경하지 않는다. 필요하면 DBA에 변경 요청.
- **UI 호출 금지**: Streamlit, Plotly 컴포넌트를 직접 호출하지 않는다. 결과는 **DataFrame / dict / dataclass** 등 순수 데이터 구조로만 반환한다.
- **사이드 이펙트 최소화**: 모델 함수는 가능한 한 순수 함수로 작성하고, 파일 IO는 학습/저장 진입점(엔트리포인트)에서만 수행한다.

### 데이터 사용 규칙

- MVP 단계에서는 **실시간 YouTube API 호출 금지** (PRD §6-1). 항상 `data/processed/`의 스냅샷만 사용한다.
- CSV에 없는 채널 요청은 **`ChannelNotFoundError`** 같은 명시적 예외로 전파하고, 임의의 fallback 데이터를 생성하지 않는다.
- 테스트 세트에는 절대 SMOTE/오버샘플링을 적용하지 않는다.

### 윤리·정책 (PRD §20)

- 비공개 정보(이메일, 비공개 댓글 등)는 학습 feature로 사용하지 않는다.
- "위험 채널" 라벨이 외부에 노출될 때는 통계적 추정치임을 명시할 수 있도록, 출력 객체에 `disclaimer` 또는 `model_version` 필드를 함께 제공한다.

### 코드 위치

- 학습 파이프라인: [src/](../../../src/) 하위 모듈 (예: `src/modeling/`, `src/features/`)
- 모델 산출물: [saved_models/](../../../saved_models/)
- 실험 노트북: [notebooks/](../../../notebooks/) — 실험 전용, 프로덕션 추론 경로에 포함시키지 않는다.
- 설정값(시드, 하이퍼파라미터, threshold): [configs/](../../../configs/)

### 변경 시 체크리스트

- [ ] PRD §10·§12에 정의된 feature/모델 정의와 일치하는가?
- [ ] Recall 80% / F1 0.7 / ROC-AUC 0.85 KPI를 충족하는가?
- [ ] 예측 결과가 `predictions_YYYYMMDD.csv` 스키마를 따르는가?
- [ ] DBA·Designer 계층의 인터페이스(입력 CSV 스키마, 출력 결과 객체)를 깨뜨리지 않는가?
- [ ] 시즌제 채널 예외가 누락되지 않았는가?
