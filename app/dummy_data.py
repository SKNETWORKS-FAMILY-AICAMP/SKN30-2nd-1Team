"""디자인 시안용 하드코딩 데이터.

designer SKILL §Boundary Rules — 실제 CSV / 모델 호출 없음.
모든 숫자는 레퍼런스 이미지에 표기된 값을 그대로 옮긴 것이다.
"""

# ────────────────────────────────────────────
# 1) 대시보드 메인
# ────────────────────────────────────────────

DASHBOARD_KPI = [
    {
        "label": "총 분석 채널 수",
        "value": "8,241",
        "unit": "개",
        "delta": "최근 30일 +245",
        "tone": "neutral",
    },
    {
        "label": "활동 중인 채널",
        "value": "6,892",
        "unit": "개",
        "delta": "83.7%",
        "tone": "neutral",
    },
    {
        "label": "위험 채널 (C등급)",
        "value": "1,142",
        "unit": "개",
        "delta": "13.9%",
        "tone": "danger",
    },
    {
        "label": "평균 이탈 위험도",
        "value": "32",
        "unit": "%",
        "delta": "-5% (지난 30일 대비)",
        "tone": "positive",
    },
]

RISK_DISTRIBUTION = [
    {"label": "A등급 (안정)", "count": 4273, "ratio": 0.52, "color": "#10B981"},
    {"label": "B등급 (주의)", "count": 2548, "ratio": 0.31, "color": "#F59E0B"},
    {"label": "C등급 (위험)", "count": 1420, "ratio": 0.17, "color": "#EF4444"},
]

# 최근 30일 평균 이탈 위험도 추이 (날짜 라벨, 값 %)
RISK_TREND = [
    ("04/14", 38), ("04/16", 39), ("04/18", 40), ("04/20", 41),
    ("04/22", 39), ("04/24", 38), ("04/26", 37), ("04/28", 36),
    ("04/30", 35), ("05/02", 34), ("05/04", 34), ("05/06", 33),
    ("05/08", 33), ("05/10", 33), ("05/12", 32), ("05/14", 32),
]

TOP_RISKY_CHANNELS = [
    {"rank": 1, "name": "○○역방", "delta": "+28%"},
    {"rank": 2, "name": "게임하는 ○○", "delta": "+24%"},
    {"rank": 3, "name": "○○ 브이로그", "delta": "+19%"},
    {"rank": 4, "name": "○○ 리뷰", "delta": "+17%"},
    {"rank": 5, "name": "○○ 일상", "delta": "+15%"},
]

RISK_SIGNALS = [
    {"icon": "📈", "label": "업로드 주기 증가", "value": 48},
    {"icon": "📉", "label": "조회수 지속 하락", "value": 36},
    {"icon": "💬", "label": "댓글 감성 악화", "value": 29},
    {"icon": "👥", "label": "참여율 감소", "value": 24},
]


# ────────────────────────────────────────────
# 2) 채널 조회 + 예측
# ────────────────────────────────────────────

SAMPLE_CHANNEL = {
    "handle": "@sample_creator",
    "name": "샘플 크리에이터",
    "category": "게임",
    "subscriber_count": "1.28M",
    "total_views": "428,571,234",
    "joined_at": "2017.05.14",
    "last_upload_days": "12일 전",
    "last_upload_date": "2026.05.02",
    "uploads_30d": "1개",
    "avg_view": "125,000",
    "avg_view_delta": "-42%",
}

PREDICTION_RESULT = {
    "grade": "C",
    "risk_pct": 72,
    "summary": [
        {"label": "업로드 주기", "value": "20일", "delta": "+150%", "tone": "danger"},
        {"label": "조회수 변화", "value": "-58%", "delta": "↓ 급감", "tone": "danger"},
        {"label": "참여율", "value": "2.1%", "delta": "-0.9%p", "tone": "warning"},
        {"label": "댓글 감성 점수", "value": "-0.32", "delta": "부정 전환", "tone": "danger"},
    ],
}

TOP_REASONS = [
    {
        "title": "업로드 주기 급감",
        "desc": "최근 업로드 간격이 평균 대비 3.2배 증가했습니다.",
    },
    {
        "title": "조회수 지속 하락",
        "desc": "최근 3개월 평균 조회수가 58% 감소했습니다.",
    },
    {
        "title": "댓글 감성 악화",
        "desc": "최근 90일 부정 댓글 비율이 32%로 상승했습니다.",
    },
]


# ────────────────────────────────────────────
# 3) 위험 분석 상세
# ────────────────────────────────────────────

UPLOAD_TREND = [
    ("12월", 12), ("1월", 10), ("2월", 8), ("3월", 5), ("4월", 2), ("5월", 1)
]

VIEW_TREND = [
    ("12월", 600_000), ("1월", 540_000), ("2월", 420_000),
    ("3월", 330_000), ("4월", 270_000), ("5월", 235_000)
]

SENTIMENT_TREND = {
    "positive": [("12월", 68), ("1월", 64), ("2월", 58), ("3월", 52), ("4월", 47), ("5월", 41)],
    "negative": [("12월", 14), ("1월", 17), ("2월", 21), ("3월", 26), ("4월", 30), ("5월", 32)],
}

ENGAGEMENT_TREND = [
    ("12월", 5.0), ("1월", 4.5), ("2월", 3.8), ("3월", 3.1), ("4월", 2.5), ("5월", 2.1)
]

RISK_SIGNAL_SUMMARY = [
    {"label": "업로드 감소", "desc": "최근 3개월 업로드 83% 감소", "level": "높음", "tone": "danger"},
    {"label": "조회수 하락", "desc": "최근 3개월 58% 감소", "level": "높음", "tone": "danger"},
    {"label": "댓글 감성 약화", "desc": "부정 댓글 비율 32%", "level": "높음", "tone": "danger"},
    {"label": "참여율 감소", "desc": "최근 3개월 0.9%p 감소", "level": "중간", "tone": "warning"},
]

SHAP_FACTORS = [
    {"label": "업로드 주기 증가", "value": 0.42},
    {"label": "댓글 감성 하락", "value": 0.31},
    {"label": "조회수 감소",   "value": 0.26},
    {"label": "참여율 감소",   "value": 0.18},
    {"label": "영상 길이 감소", "value": 0.11},
]


# ────────────────────────────────────────────
# 5) 광고주 추천
# ────────────────────────────────────────────

LONG_TERM_FEATURES = [
    {"icon": "📅", "label": "꾸준한 업로드"},
    {"icon": "📊", "label": "안정적인 조회수"},
    {"icon": "💬", "label": "긍정적 댓글 감성"},
    {"icon": "👥", "label": "높은 참여율"},
]

LONG_TERM_CHANNELS = [
    {"rank": 1, "name": "똑똑한 ○○", "subs": "1.35M", "risk": "8%",  "grade": "A"},
    {"rank": 2, "name": "여행하는 ○○", "subs": "945K", "risk": "12%", "grade": "A"},
    {"rank": 3, "name": "요리왕 ○○",   "subs": "780K", "risk": "15%", "grade": "A"},
]

SHORT_TERM_FEATURES = [
    {"icon": "⚠️", "label": "최근 활동 감소"},
    {"icon": "📉", "label": "업로드 주기 불안정"},
    {"icon": "🔻", "label": "조회수 하락 추세"},
]

SHORT_TERM_CHANNELS = [
    {"rank": 1, "name": "리뷰하는 ○○",   "subs": "430K", "risk": "58%", "grade": "C"},
    {"rank": 2, "name": "○○ 브이로그",   "subs": "560K", "risk": "65%", "grade": "C"},
    {"rank": 3, "name": "게임하는 ○○",   "subs": "890K", "risk": "82%", "grade": "C"},
]


def _generate_channels(seed: int, count: int, *, good: bool) -> list[dict]:
    import random
    rng = random.Random(seed)
    prefixes_good = [
        "똑똑한", "여행하는", "요리왕", "행복한", "친절한", "꾸준한", "성실한",
        "건강한", "활기찬", "따뜻한", "재치있는", "센스있는", "차분한", "단정한",
        "부지런한", "정직한", "긍정적인", "다정한", "유쾌한", "프로",
    ]
    prefixes_bad = [
        "리뷰하는", "게임하는", "잡담하는", "심심한", "지친", "막막한",
        "엉뚱한", "변덕스런", "들썩이는", "흔들리는", "헤매는", "허둥대는",
        "오락가락", "정처없는", "조급한", "산만한",
    ]
    suffixes = [
        "○○", "○○ 채널", "○○ TV", "○○ 일상", "○○ 라이프", "○○ 스튜디오",
        "○○ 다이어리", "○○ 클럽", "○○ 룸", "○○ 노트", "○○ 스토리", "○○ 토크",
    ]
    channels: list[dict] = []
    used: set[str] = set()
    while len(channels) < count:
        prefix = rng.choice(prefixes_good if good else prefixes_bad)
        suffix = rng.choice(suffixes)
        name = f"{prefix} {suffix}"
        if name in used:
            continue
        used.add(name)
        subs_k = rng.randint(40, 1800)
        subs = f"{subs_k}K" if subs_k < 1000 else f"{subs_k / 1000:.2f}M"
        if good:
            risk = rng.randint(3, 22)
            grade = "A" if risk <= 15 else "B"
        else:
            risk = rng.randint(55, 92)
            grade = "C"
        channels.append({
            "rank": len(channels) + 1,
            "name": name,
            "subs": subs,
            "risk": f"{risk}%",
            "grade": grade,
        })
    return channels


LONG_TERM_CHANNELS_FULL = LONG_TERM_CHANNELS + _generate_channels(42, 147, good=True)
SHORT_TERM_CHANNELS_FULL = SHORT_TERM_CHANNELS + _generate_channels(99, 147, good=False)
# rank 재정렬 (preview 3개 + 생성된 147개 = 150)
for _i, _c in enumerate(LONG_TERM_CHANNELS_FULL, 1):
    _c["rank"] = _i
for _i, _c in enumerate(SHORT_TERM_CHANNELS_FULL, 1):
    _c["rank"] = _i
