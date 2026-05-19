"""튜브어때 Streamlit 공용 컴포넌트.

화면별 페이지에서 import 하여 사용한다.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from styles import DATA_SNAPSHOT_DATE


def render_sidebar(active: str = "dashboard") -> None:
    with st.sidebar:
        st.markdown(
            """
            <a href="/" target="_self" class="tb-logo-link">
                <div style="padding: 22px 12px 10px 12px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div style="width: 32px; height: 32px; border-radius: 9px;
                                    background: linear-gradient(135deg, #6366F1, #8B5CF6);
                                    display: flex; align-items: center; justify-content: center;
                                    color: white; font-weight: 700;">🛟</div>
                        <div>
                            <div style="color: white; font-weight: 700; font-size: 0.98rem;">튜브어때</div>
                            <div style="color: #64748B; font-size: 0.72rem;">Creator Credit System</div>
                        </div>
                    </div>
                </div>
            </a>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<hr style='margin: 20px 0 35px;'/>", unsafe_allow_html=True)

        st.page_link("pages/0_대시보드.py", label="대시보드", icon="🏠")
        st.page_link("pages/1_채널_조회.py", label="채널 조회", icon="🔍")
        st.page_link("pages/3_광고주_추천.py", label="광고주 추천", icon="⭐")


        # st.markdown(
        #     f"""
        #     <div class="tb-snapshot-wrap">
        #         <div style="display:flex; justify-content: space-between;
        #                     background: #1E2493B; border-radius: 10px; padding: 12px 14px;
        #                     color: #94A3B8; font-size: 0.74rem; line-height: 1.45;margin-top:50px">
        #             <strong style="color: #E2E8F0;">데이터 스냅샷</strong>
        #             <span>{DATA_SNAPSHOT_DATE} 기준</span>
        #         </div>
        #     </div>
        #     """,
        #     unsafe_allow_html=True,
        # )


def page_header(title: str, subtitle: str, right: str | None = None) -> None:
    cols = st.columns([6, 2]) if right else (st.container(),)
    if right:
        with cols[0]:
            st.markdown(f"<div class='tb-page-title'>{escape(title)}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='tb-page-sub'>{escape(subtitle)}</div>", unsafe_allow_html=True)
        with cols[1]:
            st.markdown(
                f"""
                <div style="display:flex; justify-content:flex-end; align-items:center;
                            height: 100%; padding-top: 6px;">
                  <div style="background:white; border:1px solid #E5E7EB; border-radius:10px;
                              padding:8px 14px; font-size:0.82rem; color:#475569;">
                    {escape(right)}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(f"<div class='tb-page-title'>{escape(title)}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='tb-page-sub'>{escape(subtitle)}</div>", unsafe_allow_html=True)


def kpi_card(label: str, value: str, unit: str, delta: str, tone: str = "neutral") -> None:
    tone_class = {
        "positive": "positive",
        "danger": "danger",
        "warning": "warning",
    }.get(tone, "")
    st.markdown(
        f"""
        <div class="tb-card">
            <div class="tb-kpi-label">{escape(label)}</div>
            <div class="tb-kpi-value">{escape(value)}<span style="font-size:1rem; font-weight:500; color:#94A3B8; margin-left:4px;">{escape(unit)}</span></div>
            <div class="tb-kpi-delta {tone_class}">{escape(delta)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def grade_badge_html(grade: str) -> str:
    return f"<span class='tb-grade tb-grade-{grade}'>{grade}</span>"


def chip(label: str, kind: str = "neutral") -> str:
    return f"<span class='tb-chip tb-chip-{kind}'>{escape(label)}</span>"


def disclaimer_footer() -> None:
    st.markdown(
        f"""
        <div class="tb-footer">
            📌 본 결과는 <strong>{DATA_SNAPSHOT_DATE}</strong> 기준 사전 수집 스냅샷 데이터를 활용한
            통계적 추정치이며, 광고 의사결정의 <strong>참고 자료</strong>로만 사용해 주세요.
            크리에이터 개인에 대한 평가나 제재 목적이 아닙니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


def card(title: str | None = None, subtitle: str | None = None):
    """st.container(border=True) 기반 카드 래퍼.

    `with card("제목", "부제"):` 형태로 사용한다.
    title과 subtitle은 한 줄에서 좌/우 양끝 정렬로 렌더된다.
    """
    container = st.container(border=True)
    if title or subtitle:
        title_html = (
            f"<div class='tb-card-title'>{escape(title)}</div>" if title else "<div></div>"
        )
        subtitle_html = (
            f"<div class='tb-card-sub'>{escape(subtitle)}</div>" if subtitle else ""
        )
        container.markdown(
            f"<div class='tb-card-header'>{title_html}{subtitle_html}</div>",
            unsafe_allow_html=True,
        )
    return container
