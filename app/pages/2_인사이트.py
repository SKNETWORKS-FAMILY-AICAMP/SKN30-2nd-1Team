"""튜브어때 — 웹 인사이트 페이지."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

from components import page_header, render_sidebar
from styles import inject_global_css

ASSETS = Path(__file__).resolve().parent.parent / "assets"

st.set_page_config(
    page_title="인사이트 — 튜브어때",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
render_sidebar("insight")

page_header(
    "인사이트",
    "8083 채널 분석에서 추출한 광고 의사결정 가이드",
)


def _insight_card(title: str, points: list[str]) -> None:
    items = "".join(f"<li>{p}</li>" for p in points)
    st.markdown(
        f"""
        <div style="
            background:#F8FAFF;
            border-left:4px solid #6366F1;
            border-radius:8px;
            padding:16px 20px;
            margin-top:12px;
        ">
            <p style="font-weight:700;font-size:0.95rem;color:#1E293B;margin:0 0 8px 0;">{title}</p>
            <ul style="margin:0;padding-left:18px;color:#334155;font-size:0.88rem;line-height:1.7;">
                {items}
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


tab1, tab2, tab3 = st.tabs(["참여율 분석", "콘텐츠 포맷", "채널 리스크"])

# ── 탭 1: 참여율 분석 ──────────────────────────────────────────
with tab1:
    st.image(
        str(ASSETS / "1_구독자수대비 평균 참여율.png"),
        use_container_width=True,
    )
    _insight_card(
        "채널 발굴 및 타깃팅 전략",
        [
            "스위트 스팟: <b>1~5만 명</b> 채널이 참여율(5%↑)·비용 효율 모두 최적",
            "<b>5~10만</b>: 팬덤 결속력 최고 → 적극적 소통 유도",
            "<b>10~30만</b>: 성장통 구간 → 댓글 이벤트로 소통 강화",
            "<b>50만↑</b>: 규모의 경제 → 브랜딩 강화 및 고관여 유지",
        ],
    )

    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)

    st.image(
        str(ASSETS / "2_채널별 과거 휴지기횟수 대비 최대공백기간.png"),
        use_container_width=True,
    )
    _insight_card(
        "진성 참여율 검증 (거품 걸러내기)",
        [
            "기준: <b>좋아요 10개당 댓글 1개(10%)</b> 이상 = 진성 팬덤 보유",
            "댓글은 시청자의 직접적 행동 → 광고 집행 시 구매 전환율이 훨씬 높음",
            "단순 조회수보다 <b>댓글창 활성도</b>를 최우선 고려",
        ],
    )

# ── 탭 2: 콘텐츠 포맷 ──────────────────────────────────────────
with tab2:
    st.image(
        str(ASSETS / "4_채널 주력포맷별 평균 참여율.png"),
        use_container_width=True,
    )
    _insight_card(
        "콘텐츠 포맷 및 마케팅 매칭",
        [
            "<b>숏폼 중심</b>: 인지도 확산·앱 설치·챌린지 등 바이럴 캠페인에 적합 (참여율 상향 평준화)",
            "<b>롱폼 중심</b>: 상세 스펙 설명·고관여 제품·구매 전환 유도에 안정적 (변동성 낮음)",
            "<b>혼합형</b>: 브랜딩 + 유저 소통 화력 동시 확보 가능한 최적 대안",
        ],
    )

    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)

    st.image(
        str(ASSETS / "8_쇼츠대박이 일반영상으로 이어지는가.png"),
        use_container_width=True,
    )
    _insight_card(
        "포맷 최적화: 쇼츠 vs 롱폼 시너지",
        [
            "핵심: 쇼츠 조회수가 롱폼 충성 시청자로 전환되는가? (괴리율 확인)",
            "<b>팬덤 결집형(롱폼 우세)</b>: 고관여 제품·상세 브랜딩 캠페인 최적 → 안전 자산",
            "<b>휘발성 채널(쇼츠 편향)</b>: 단기 인지도·앱 설치·신제품 런칭용 가성비 타겟",
        ],
    )

# ── 탭 3: 채널 리스크 ──────────────────────────────────────────
with tab3:
    st.image(
        str(ASSETS / "11_영상길이별 조회수 및 관여도.png"),
        use_container_width=True,
    )
    _insight_card(
        "채널 성과·리스크 4분면 진단",
        [
            "<b>① 고위험군</b>(마니아 소통형): 단가 최소 40% 삭감 + 지연 시 100% 환불 조항",
            "<b>② 중위험군</b>(투자 금지): 단가 20% 삭감 + 업로드 일정·요일 확정 조건",
            "<b>③ 저위험군</b>(대중적 메가뷰): 기본 단가 인정 + 조회수 기반 성과 연동 계약",
            "<b>④ 안전군</b>(Sweet Spot): 장기 파트너십 + 보너스 인센티브로 관계 선점",
            "핵심: 장기 잠수 시 조회수 최대 75% 감소 → 업로드 성실도 관리가 매출과 직결",
        ],
    )

    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)

    st.image(
        str(ASSETS / "13_업로드주기 및 상시 성실도별 초기 조회수 부스팅.png"),
        use_container_width=True,
    )
    _insight_card(
        "채널 업로드 주기 및 성향 분석",
        [
            "<b>메가 부스팅형(1~3일)</b>: 반드시 현재 활발히 업로드 중일 때만 계약 (2~3주 공백 채널 배제)",
            "<b>중위 그룹(7~15일)</b>: 성과 변동성 과대 → 매칭 지양",
            "<b>팬덤/장인형(16일↑)</b>: 공백 유무 무관 안전 자산 → 우선 선점, 업로드 일정 확약 조건",
        ],
    )
