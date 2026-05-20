# 유튜브 댓글 감성분석 → 마케팅 KPI 패널 (이탈 모델 보조지표)

## Context

본 프로젝트의 댓글 데이터는 다음과 같이 **층화 샘플링**되어 있다.

- 구독자 밴드(A/B/C/D) × {이탈 / 유지} 으로 층화
- 각 층 안에서 채널 랜덤 샘플링
- 채널당 최근 10개 영상 × 영상당 인기 댓글 50개 (≈ 채널당 500개)

이 표본 구조는 **시계열 추세나 채널 단위 이탈 직접 예측엔 부적합**하지만, 채널 간
비교가 가능한 균일 표본이며, 인기 댓글은 시청자 다수가 공감한 "대표 반응"으로
해석할 수 있다.

따라서 본 작업의 목표는 댓글 감성을 **마케팅·소비자 분석에서 쓰는 표준
방법론**으로 정량화하여, **이탈 확률 모델 결과의 보조지표**(해석·검증용
KPI 패널)로 제공하는 것이다. `risk_calculation.ipynb`에 가중치로 강제
합류시키지 않는다.

## 산출물

| 항목 | 경로 |
|---|---|
| 신규 노트북 | [notebooks/02_modeling/comment_sentiment_panel.ipynb](notebooks/02_modeling/comment_sentiment_panel.ipynb) |
| 채널 단위 KPI 패널 | [data/raw/comment_sentiment_panel.csv](data/raw/comment_sentiment_panel.csv) |
| 의존성 추가 | [pyproject.toml](pyproject.toml) |

`risk_calculation.ipynb`는 수정하지 않는다.

---

## 1. 감성 분석 모델

### 1.1 선택 모델

**`cardiffnlp/twitter-xlm-roberta-base-sentiment`**

| 항목 | 내용 |
|---|---|
| 베이스 아키텍처 | XLM-RoBERTa base (Transformer encoder, ~270M parameters) |
| 학습 코퍼스 | 8개 언어 (영/한/일/중/스/프/포/이) 트위터 약 198M 트윗으로 사전학습 → 198K 라벨 트윗으로 fine-tuning |
| 출력 | 3-class: `positive` / `neutral` / `negative` + confidence(softmax) |
| 입력 길이 | 최대 512 token (실사용 max_length=256) |
| 라이선스 | MIT |
| 배포 | HuggingFace Hub (`transformers` 라이브러리로 로드) |
| 추론 비용 | 로컬 추론, 외부 API 호출 0건, 비용 0원 |
| 모델 크기 | 약 1.1 GB (float32) |

### 1.2 모델 작동 방식 (간단 설명)

1. **Tokenizer**: SentencePiece 기반 다국어 토크나이저가 한국어/영어/이모지 demojize 텍스트를 subword 단위로 분해
2. **Encoder**: XLM-RoBERTa가 12-layer Transformer로 문맥 표현 생성
3. **Classification head**: `[CLS]` 표현에 linear layer를 얹어 3-class softmax 출력

### 1.3 왜 이 모델인가 (선택 근거)

본 데이터의 댓글 특성과 매칭해 다음 5개 축으로 비교 검토했다.

#### 근거 1: 댓글에 다국어가 섞여 있다

- 본 데이터 댓글에는 한국어, 영어, 일본어, 중국어가 혼재 (특히 K-pop·게임·여행
  채널). 한국어 전용 모델(KoBERT, KR-FinBert 등)은 외국어 댓글을 OOV 또는
  비정상 토큰으로 처리하여 신뢰도 하락.
- XLM-R 계열은 100개 언어로 사전학습되어 다국어를 같은 임베딩 공간에 매핑.

#### 근거 2: 댓글은 SNS체 짧은 문장이다

- 평균 길이가 짧고, 비격식·구어·신조어가 많음. 뉴스·리뷰·금융 텍스트로
  학습된 감성 모델(KR-FinBert 등)은 도메인 미스매치로 정확도 저하.
- 본 모델은 트위터 텍스트로 학습 — SNS 도메인에 직접 적합.

#### 근거 3: 이모지가 감성의 핵심 신호다

- 유튜브 댓글의 감성은 이모지(🔥, 😭, ❤️, 🤣)에 강하게 의존.
- 전처리에서 `emoji.demojize`로 `:fire:`, `:loudly_crying_face:` 같은 토큰으로
  변환하면 모델이 그 의미를 학습된 표현으로 다룸. 트위터 학습 코퍼스에
  유사 패턴이 풍부.

#### 근거 4: 3-class 출력이 KPI 계산에 직결된다

- 본 작업의 KPI(NSS, Sentiment Mix, Polarization, Like-weighted NSS)는 모두
  positive / neutral / negative 분포에서 직접 도출.
- 연속 점수만 내는 모델(예: 단일 sentiment scalar)은 신뢰구간/분포 해석이 어려움.
- 5-class 모델은 KPI 계산 시 다시 묶어야 해서 정보 손실.

#### 근거 5: 라이선스·재현성·비용

- MIT 라이선스, HuggingFace 공개 → 팀 재현 가능
- 로컬 추론 → API 비용 0, rate limit 없음, 인터넷 끊겨도 재추론 가능
- HuggingFace 다운로드 수 수백만 단위, **`tweetnlp` 라이브러리의 디폴트 다국어 감성 모델** — 실무 표준

### 1.4 검토했지만 채택 안 한 대안

| 모델 | 장점 | 채택 안 한 이유 |
|---|---|---|
| `monologg/kobert` 등 한국어 전용 | 한국어 정확도 ↑ | 외국어/이모지 댓글 손실. 본 표본의 다국어 비중을 무시할 수 없음 |
| `snunlp/KR-FinBert-SC` | 한국어 감성 fine-tuned | 금융 도메인 — 댓글 SNS체와 미스매치 |
| `xlm-roberta-large` 기반 7-class 감성 | 정밀 등급 | 모델 크기 2배+, 추론 시간 2~3배. ROI 낮음 |
| OpenAI/Anthropic API | 정확도 ↑ 가능성 | 비용 + rate limit + 외부 의존. 수만 댓글 단위에서 부담 |
| VADER + 영-한 번역 | 빠름, 무료 | 번역 손실, 한국어 정확도 매우 낮음. 데모용에만 적합 |

### 1.5 모델의 한계 인지

- 정치·풍자·반어법은 SNS 모델도 자주 틀린다 → **Lexicon 보조 사전과 병행**
- 짧은 ㅋㅋ/ㅎㅎ만 있는 댓글은 종종 neutral로 잡힌다 → 보조 feature(`laugh_count`)로 보강
- confidence가 낮은 (예: 0.4~0.5) 예측은 noise일 수 있어, 정렬에는 평균을 쓰고 단일 댓글 해석은 피한다

---

## 2. 분석 방법론 (마케팅·소비자 분석 표준)

### 2.1 적용 방법론 매트릭스

| # | 방법론 | 출처/표준 | 본 데이터 적용 |
|---|---|---|---|
| 1 | **Net Sentiment Score (NSS)** | Brand Health Tracking 표준 | `(P - N) / (P + N + Neu)`, [-1,+1] |
| 2 | **Sentiment Mix** | VoC 리포트 기본 | P/Neu/N 3비율 |
| 3 | **Engagement-weighted Sentiment** | Social Listening 도구 표준 (Brandwatch/Sprinklr 류) | `like_count` 가중 NSS |
| 4 | **Loyalty / Affection Lexicon Score** | Brand Attachment 측정 (Park & MacInnis) | 충성·애정 표현 사전 매칭 비율 |
| 5 | **Churn-Warning Lexicon Score** | VoC 이탈 시그널 분석 | 이탈·불만 표현 사전 매칭 비율 |
| 6 | **Sentiment Polarization** | 팬덤 양극화 측정 | `4·P·N` (P=N=0.5일 때 1) |
| 7 | **Engagement Quality** | 댓글 몰입 보조 | 평균 길이, 이모지/웃음/물음표 비율 |

3·4·5번이 단순 감성 분포만으로 보지 못하는 부분을 보강하는 **마케팅 차별 지표**.

### 2.2 Loyalty Lexicon 초안 (사용자 보강 대상)

> 가중치는 sensitive_keyword_score.ipynb의 3·2·1점 체계를 차용.

```python
LOYALTY_LEXICON = {
    "충성_고": {  # weight 3 — 명시적 팬덤·관계 표현
        "keywords": ["사랑해요", "사랑합니다", "최고예요", "최고입니다", "응원합니다",
                     "응원해요", "구독했어요", "구독하고 갑니다", "알림설정",
                     "구독자 1호", "팬이에요", "팬입니다", "덕질"],
        "weight": 3,
    },
    "충성_중": {  # weight 2 — 재방문·재시청 의향
        "keywords": ["다시 봐도", "또 봐요", "또 보러", "n회차", "정주행",
                     "기다렸어요", "기다렸습니다", "다음 영상", "다음편 빨리"],
        "weight": 2,
    },
    "충성_저": {  # weight 1 — 가벼운 긍정·친밀도
        "keywords": ["좋아요", "잘봤어요", "잘 봤습니다", "감사합니다", "재밌어요",
                     "재밌네요", "굿", "최고", "역시"],
        "weight": 1,
    },
}
```

### 2.3 Churn-Warning Lexicon 초안 (사용자 보강 대상)

```python
CHURN_WARNING_LEXICON = {
    "이탈_고": {  # weight 3 — 명시적 이탈 선언
        "keywords": ["구독 취소", "구취", "언구독", "이제 안 봐요", "이제 안 봅니다",
                     "탈덕", "정 떨어졌", "실망했어요", "실망입니다"],
        "weight": 3,
    },
    "이탈_중": {  # weight 2 — 채널 변화에 대한 불만
        "keywords": ["예전이 좋았", "옛날이 좋았", "재미없어졌", "재미가 없어",
                     "변했어요", "변했네요", "초심", "왜 이래", "퀄리티 떨어"],
        "weight": 2,
    },
    "이탈_저": {  # weight 1 — 업로드 공백·근황 불안 (질문이지만 이탈 신호일 수 있음)
        "keywords": ["언제 올라와", "왜 안 올려", "근황", "어디 갔어", "잠수",
                     "활동 안 하시", "휴재"],
        "weight": 1,
    },
}
```

**계산식**:

```
loyalty_score(channel) = Σ(매칭된 댓글 가중치) / (n_comments × 3)   # 0~1 클립
churn_warning_score(channel) = 같은 방식 × CHURN_WARNING_LEXICON
```

사전 자체는 사용자가 본 데이터에 맞춰 수정·확장하기 쉽도록 노트북 상단에 노출.

---

## 3. 데이터 흐름

```
data/raw/comments/band_{A,B,C,D}/{CHxxx}_{idx}_{UC...}_{vid}.csv  (2,281개)
        │  CSV walk + 파일명에서 channel_id(UC...) 추출
        ▼
[댓글 단위 DataFrame] (channel_id, video_id, text, like_count, ...)
        │  preprocess_comment()
        ▼
comment_clean
        │  XLM-R sentiment batch inference (MPS > CUDA > CPU)
        ▼
sentiment_label, sentiment_score
        │  Lexicon 매칭 (loyalty, churn_warning)
        │  보조 feature (emoji_count, laugh_count, cry_count, question_flag, comment_len)
        ▼
[댓글 단위 결과] (메모리)
        │  영상 단위 집계 (channel_id, video_id)
        ▼
[영상 단위 결과] (메모리)
        │  채널 단위 집계 (channel_id)
        ▼
data/raw/comment_sentiment_panel.csv  ← 산출물
```

---

## 4. 채널 단위 KPI 패널 (CSV 스키마)

| 컬럼 | 의미 | 범위 | 카테고리 |
|---|---|---|---|
| `channel_id` | YouTube 채널 ID (UC...) | string | Key |
| `n_videos` | 분석된 영상 수 | int | Meta |
| `n_comments` | 분석된 총 댓글 수 | int | Meta |
| `net_sentiment_score` | NSS = (P-N)/(P+N+Neu) | -1~+1 | 방법 1 |
| `pos_ratio` | 긍정 비율 | 0~1 | 방법 2 |
| `neu_ratio` | 중립 비율 | 0~1 | 방법 2 |
| `neg_ratio` | 부정 비율 | 0~1 | 방법 2 |
| `like_weighted_nss` | 좋아요 가중 NSS | -1~+1 | 방법 3 |
| `loyalty_score` | 충성 표현 매칭 점수 | 0~1 | 방법 4 |
| `churn_warning_score` | 이탈 신호 매칭 점수 | 0~1 | 방법 5 |
| `polarization_score` | 양극화 4·P·N | 0~1 | 방법 6 |
| `avg_comment_len` | 평균 댓글 길이 | float | 방법 7 |
| `emoji_ratio` | 이모지 포함 비율 | 0~1 | 방법 7 |
| `laugh_ratio` | ㅋㅋ/ㅎㅎ 비율 | 0~1 | 방법 7 |
| `cry_ratio` | ㅠㅠ/ㅜㅜ 비율 | 0~1 | 방법 7 |
| `question_ratio` | 물음표 포함 비율 | 0~1 | 방법 7 |

---

## 5. 이탈 모델과의 결합 (보조지표 활용)

`risk_calculation.ipynb`에 가중치로 합류시키지 않는다. 대신 분석 노트북 자체에 **해석 매트릭스**를 시각화로 포함.

| 이탈확률 | NSS / Loyalty / Churn-warning | 해석 |
|---|---|---|
| ↑ | `churn_warning_score` ↑ | 강한 경고 — 모델·VoC 모두 일치 |
| ↑ | `loyalty_score` ↑, NSS ↑ | **불일치** — 모델 결과 재검토 또는 콘텐츠 외 요인(업로더 본인 사유) 의심 |
| ↓ | `polarization_score` ↑ | 단기 안정이나 잠재 갈등 — 모니터링 권장 |
| ↓ | `loyalty_score` ↑ | 건강한 채널 |
| ↓ | NSS ↓ , `churn_warning_score` ↓ | 부정적이지만 강하지 않은 노이즈, 큰 의미 없음 |

---

## 6. 노트북 구성

```
0. 라이브러리 / 한글 폰트
1. Lexicon 정의 (LOYALTY_LEXICON, CHURN_WARNING_LEXICON) — 보강 쉽게 상단 노출
2. 댓글 CSV 일괄 로드
   - data/raw/comments/band_*/*.csv 글롭
   - 파일명에서 channel_id (UC로 시작) 파싱
   - 단일 DataFrame으로 concat
3. 댓글 전처리 (preprocess_comment)
4. 감성 모델 로드 (device auto-detect)
5. 댓글 단위 batch inference (max_length=256, batch_size=32, tqdm)
6. Lexicon 매칭 + 보조 feature
7. 영상 단위 집계 (sanity 확인용, 메모리)
8. 채널 단위 KPI 패널 집계
9. 분포 시각화 + 이탈모델 결과와 결합 매트릭스 시각화
10. 저장: data/raw/comment_sentiment_panel.csv
```

---

## 7. 의존성 추가

`pyproject.toml`의 `dependencies`에 추가:

```toml
"emoji>=2.0.0",
"soynlp>=0.0.493",
"tqdm>=4.66.0",
```

`[dl]` extras는 그대로 (`torch`, `transformers`, `sentencepiece` 이미 존재).

설치:
```bash
uv sync --extra dl
```

---

## 8. 검증 (Verification)

1. **Smoke test**
   - 노트북 셀 5 직전에 `df = df.head(100)` 슬라이스로 전 셀 통과
   - 에러 없이 `comment_sentiment_panel.csv`가 생성되는지 확인 후 슬라이스 제거

2. **출력 무결성**
   - `channel_id`가 모두 UC로 시작 (`.str.startswith("UC").all()`)
   - `pos_ratio + neu_ratio + neg_ratio ≈ 1.0`
   - 모든 비율 컬럼이 [0,1] 범위

3. **모델 sanity**
   - 상위 NSS 5채널의 댓글 샘플 5개씩을 눈으로 확인 — 실제 긍정인지
   - 하위 NSS 5채널 동일 확인
   - `churn_warning_score` 상위 채널의 매칭 댓글 직접 확인 — 사전이 잘못 잡는 케이스 없는지

4. **재현성**
   - 노트북 전체 재실행 시 동일 결과 (모델 결정론·정렬 안정성 확인)

5. **이탈 모델 연결**
   - `churn_probability_output.csv`와 `channel_id` 교집합 확인
   - 5장의 결합 매트릭스를 실제 산점도/히트맵으로 1장 출력
