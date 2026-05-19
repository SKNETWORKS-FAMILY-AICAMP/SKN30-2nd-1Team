# AGENTS.md

> 튜브어때 (TubeEottae) 프로젝트의 **단일 풀스택 코딩 에이전트** 운영 규약.
> 에이전트는 하나의 작업 흐름으로 데이터·모델·UI 계층을 모두 다룰 수 있으나,
> **작업 시작 전 [.agents/skills/](.agents/skills/)를 동적으로 탐색**하고
> 관련 SKILL.md를 읽어 **각 계층의 제약을 지켜야** 한다.

---

## 0. 운영 모델 한 줄 요약

> **하나의 에이전트, 세 개의 계층, N개의 스킬.**
> 작업이 들어오면 → 어느 계층(들)인지 식별 → 해당 스킬 문서를 로드 → 계층 경계를 지키며 실행 → 침범 시 중단·합의.

---

## 1. Domain Discovery (도메인 식별)

작업을 시작하기 **전에** 사용자의 요청이 어떤 계층에 속하는지 식별한다.
계층은 [docs/튜브어때_PRD.md](docs/튜브어때_PRD.md)에 정의된 다음 세 영역과 매핑된다:

| 도메인 시그널 | 매핑되는 계층 / 스킬 |
|---|---|
| YouTube API, CSV 스키마, `data/raw/`, `data/processed/`, 수집·쿼터·정제 | **dba** → [.agents/skills/dba/SKILL.md](.agents/skills/dba/SKILL.md) |
| feature 계산, 모델 학습·튜닝·평가, SHAP, 추천 로직, threshold, KoBERT | **business-logic** → [.agents/skills/business-logic/SKILL.md](.agents/skills/business-logic/SKILL.md) |
| Streamlit 화면, Plotly 차트, 사용자 입력 UX, 게이지·카드·면책 표기 | **designer** → [.agents/skills/designer/SKILL.md](.agents/skills/designer/SKILL.md) |

### 식별 절차

1. **[.agents/skills/](.agents/skills/)를 동적으로 나열**한다 (`ls .agents/skills/`).
   - 신규 스킬이 추가되었을 수 있으므로 **하드코딩된 목록을 가정하지 않는다**.
2. 사용자 요청의 키워드·파일 경로·언급된 산출물을 위 표와 매칭한다.
3. 매칭이 **2개 이상**이면 멀티 레이어 작업이다 → §4 절차로 진입.
4. 매칭이 **모호하면** 사용자에게 명확히 확인한다 (예: "이 변경은 추론 로직 변경인가요, UI 표시 형식 변경인가요?").

> ⚠️ 도메인 식별 단계에서 PRD를 통째로 다시 읽을 필요는 없다. SKILL.md가 PRD 섹션을 인용한다.

---

## 2. Context Loading (컨텍스트 로딩)

도메인이 식별되면 **즉시 해당 스킬 문서를 읽는다**. 추측으로 진행하지 않는다.

### 로딩 순서

1. **관련 SKILL.md 전체를 읽는다** (Objective / Scope / Key Responsibilities / Constraints & Guidelines 모두).
2. SKILL.md가 가리키는 **PRD 섹션**을 필요한 만큼만 발췌해 읽는다 (전체 PRD 통독 금지 — 토큰 낭비).
3. SKILL.md의 **코드 위치 섹션**에 명시된 디렉터리(`src/`, `app/`, `data/`, `configs/`, `saved_models/` 등)를 확인하고 기존 패턴을 따른다.
4. 멀티 레이어 작업이면 관련된 모든 스킬 문서를 한 번에 로드한다.

### 다시 로드해야 하는 경우

- 작업 도중 다른 계층 파일을 수정해야 한다는 사실을 알게 된 경우 → 해당 계층 SKILL.md를 추가로 로드.
- 사용자가 "다른 부분도 같이 바꿔줘"라고 요청한 경우 → 추가 계층의 SKILL.md 로드.
- SKILL.md가 갱신된 흔적이 있는 경우 (이전 작업과 다른 규칙이 보일 때) → 재로딩.

---

## 3. Execution Constraints (실행 제약)

스킬 문서를 로드한 뒤 작업을 수행할 때, **모든 작업은 다음 공통 제약 위에서** 진행된다.

### 3-1. 계층 경계 (Boundary Rules) — 절대 침범 금지

| 계층 | 금지 행위 |
|---|---|
| **dba** | feature 계산식 작성, 모델 호출, Streamlit/Plotly import |
| **business-logic** | CSV 컬럼 추가·삭제·타입 변경, YouTube API 직접 호출, Streamlit/Plotly import |
| **designer** | 모델 학습/SHAP 계산, threshold·등급 컷오프 결정, CSV 스키마 변경, YouTube API 호출 |

> 경계를 침범하지 않고는 작업이 불가능해 보이면 → **작업을 중단하고 §4 절차**로 전환한다.

### 3-2. 데이터 정책

- MVP는 **2026-05-17 스냅샷 기반** ([docs/튜브어때_PRD.md](docs/튜브어때_PRD.md) §6-1, §19). 실시간 YouTube API 호출 금지.
- 채널이 `data/processed/`에 없으면 **임의 fallback 데이터를 만들지 말고 명시적 예외/안내**로 전파.
- 학습 데이터에만 SMOTE 적용, **테스트 세트에는 절대 미적용**.

### 3-3. KPI 게이트

다음 지표는 작업 완료 판단의 게이트다:

- 이탈 Recall ≥ 80%, F1 ≥ 0.7, ROC-AUC ≥ 0.85
- 채널당 분석 처리 시간 ≤ 5초
- 모델 변경 시 KPI 미달이면 **머지 금지**, 사용자에게 알린다.

### 3-4. 산출물 스키마

- `data/processed/*.csv`: PRD §14-2 스키마 고정 (변경 시 §4 절차 필수)
- `data/predictions/predictions_YYYYMMDD.csv`: 컬럼 = `channel_id, predicted_at, risk_score, risk_grade, top_risk_factors, model_version`
- 모델 산출물: [saved_models/](saved_models/)에 **버전 태그와 함께** 저장

### 3-5. 윤리·정책 (PRD §20)

- 공개 API 데이터만 사용. 비공개 정보 저장 금지.
- "위험 채널" 결과는 **참고용 추정치**임이 산출물/화면에 드러나야 한다.

### 3-6. 일반 코딩 제약

- 기존 함수·유틸을 먼저 탐색해 재사용한다. 추측으로 새 모듈을 만들지 않는다.
- 가설적 미래 요구에 대비한 추상화·옵션 플래그 추가 금지.
- 디버깅용 주석, 변경 이력 주석, "X를 위해 추가됨" 같은 컨텍스트성 주석 금지 (PR 본문에 기재).

---

## 4. 여러 계층 수정 시 — 각 스킬 규칙 동시 준수

작업이 둘 이상의 계층을 건드릴 때 (예: "댓글 감성 컬럼 추가하고 화면에도 노출해줘"), 다음 절차를 따른다.

### 4-1. 영향 범위 선언

작업을 시작하기 전에 사용자(또는 자신)에게 다음을 명시한다:

```
영향 계층: [dba, business-logic, designer]
변경 파일 (예상):
  - data/processed/comments.csv (dba)         ← 스키마 컬럼 추가
  - src/features/sentiment.py (business-logic) ← 새 컬럼 소비
  - app/pages/analysis.py (designer)           ← 새 지표 카드 추가
```

### 4-2. 각 계층의 SKILL.md를 모두 로드

세 SKILL.md의 **Constraints & Guidelines > 변경 시 체크리스트**를 각각 통과시켜야 한다.

### 4-3. 변경 순서 (Top-down)

데이터 → 로직 → UI 순으로 변경한다. 그 반대로 가면 하위 계층이 깨진 상태로 UI가 머지될 수 있다.

1. **dba**: CSV 스키마 변경 + PRD §14-2 갱신 + 스키마 검증 유틸 업데이트
2. **business-logic**: 새 컬럼을 소비하는 feature/모델 코드 작성, KPI 재측정
3. **designer**: 새 결과를 화면에 표시, 면책 문구·기준일 표시 유지

### 4-4. 경계 침범 회피 패턴

| 흔한 유혹 | 올바른 처리 |
|---|---|
| UI에서 CSV를 정렬·집계해 보여주고 싶다 | 사전 집계 컬럼을 **dba/business-logic**에 추가 요청 |
| 모델 코드에서 채널을 추가 수집하고 싶다 | 수집은 **dba**에 위임, business-logic은 입력 CSV만 사용 |
| dba 단에서 `engagement_rate`를 미리 계산해 두면 편하다 | 금지. **business-logic의 feature**다. raw 컬럼까지만 저장 |
| 화면에서 SHAP를 다시 계산해 더 예쁘게 그리고 싶다 | 금지. business-logic이 산출한 결과를 **표시만** |

### 4-5. 합의 절차 (스키마·KPI·등급 컷오프 변경)

다음은 단일 계층에서 결정할 수 없고, **세 계층 합의 + PRD 갱신**이 필요한 변경이다:

- `data/processed/*.csv` 컬럼·타입 변경
- `predictions_YYYYMMDD.csv` 스키마 변경
- 이탈 정의(90일 룰) 변경
- A/B/C 등급 컷오프 변경
- KPI 임계값 변경

이런 변경은 작업 시작 전 사용자에게 **명시적으로 확인**한다.

---

## 5. 작업 시작 체크리스트

매 작업의 첫 메시지에서 다음을 빠르게 점검한다 (출력은 한두 줄로 압축):

- [ ] [.agents/skills/](.agents/skills/) 디렉터리에서 관련 스킬을 찾았는가?
- [ ] 해당 SKILL.md(들)을 읽었는가?
- [ ] 변경 영향 계층을 식별했는가? (단일/멀티)
- [ ] 멀티 레이어면 변경 순서를 dba → business-logic → designer로 잡았는가?
- [ ] 스키마/KPI/등급 컷오프를 건드리는가? → 사전 합의 필요

---

## 6. 참고 문서

- 제품 스펙: [docs/튜브어때_PRD.md](docs/튜브어때_PRD.md)
- 스킬 정의:
  - [.agents/skills/dba/SKILL.md](.agents/skills/dba/SKILL.md)
  - [.agents/skills/business-logic/SKILL.md](.agents/skills/business-logic/SKILL.md)
  - [.agents/skills/designer/SKILL.md](.agents/skills/designer/SKILL.md)
- 코드 위치: [src/](src/) (수집·모델), [app/](app/) (Streamlit), [data/](data/) (CSV), [configs/](configs/), [saved_models/](saved_models/)
