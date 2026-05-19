"""튜브어때 — 광고주 추천."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).parent.parent))

from components import (
    card,
    disclaimer_footer,
    grade_badge_html,
    page_header,
    render_sidebar,
)
from dummy_data import (
    LONG_TERM_CHANNELS,
    LONG_TERM_FEATURES,
    SHORT_TERM_CHANNELS,
    SHORT_TERM_FEATURES,
)
from styles import inject_global_css

st.set_page_config(
    page_title="튜브어때 — 광고주 추천",
    page_icon="🛟",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
render_sidebar("recommend")

page_header(
    title="광고주 추천 채널",
    subtitle="광고 계약에 적합한 안정성 높은 채널을 추천합니다.",
)


def _channel_row(c: dict) -> str:
    return f"""
    <div class="tb-rec-row">
        <div class="tb-rec-rank">{c['rank']}</div>
        <div class="tb-rec-avatar">👤</div>
        <div class="tb-rec-name">{c['name']}</div>
        <div class="tb-rec-meta">{c['subs']}</div>
        <div class="tb-rec-meta">{c['risk']}</div>
        <div style="width:34px; text-align:right;">{grade_badge_html(c['grade'])}</div>
    </div>
    """


_TABLE_HEADER = """
<div style="display:flex; padding:6px 4px 8px 4px;
            font-size:0.74rem; color:#94A3B8; font-weight:500;">
    <div style="width:22px;"></div>
    <div style="width:32px;"></div>
    <div style="flex-grow:1;">채널</div>
    <div style="min-width:60px; text-align:right;">구독자 수</div>
    <div style="min-width:60px; text-align:right;">이탈 위험도</div>
    <div style="width:34px; text-align:right;">등급</div>
</div>
"""

with card("장기 계약 추천 채널", "안정성 높음"):
    fl, fr = st.columns([1, 1.4], gap="medium")
    with fl:
        feats_html = "".join(
            f"""
            <div class="tb-feat-row">
                <div class="tb-feat-icon safe">{f['icon']}</div>
                <div class="tb-feat-label">{f['label']}</div>
            </div>
            """
            for f in LONG_TERM_FEATURES
        )
        st.markdown(feats_html, unsafe_allow_html=True)
    with fr:
        rows = "".join(_channel_row(c) for c in LONG_TERM_CHANNELS)
        st.html(
            _TABLE_HEADER + rows + """
            <div style="margin-top:14px; text-align:center;">
                <a href="/추천_채널_리스트?type=long&page=1" target="_self"
                   style="display:inline-block; padding:8px 18px;
                          border:1px solid #E5E7EB; border-radius:10px;
                          font-size:0.82rem; color:#475569; text-decoration:none; background:white;">
                    더 많은 추천 채널 보기 →
                </a>
            </div>
            """
        )

st.write("")

with card("단기 계약 권장 채널", "주의 필요"):
    sl, sr = st.columns([1, 1.4], gap="medium")
    with sl:
        feats_html = "".join(
            f"""
            <div class="tb-feat-row">
                <div class="tb-feat-icon danger">{f['icon']}</div>
                <div class="tb-feat-label">{f['label']}</div>
            </div>
            """
            for f in SHORT_TERM_FEATURES
        )
        st.markdown(feats_html, unsafe_allow_html=True)
    with sr:
        rows = "".join(_channel_row(c) for c in SHORT_TERM_CHANNELS)
        st.html(
            _TABLE_HEADER + rows + """
            <div style="margin-top:14px; text-align:center;">
                <a href="/추천_채널_리스트?type=short&page=1" target="_self"
                   style="display:inline-block; padding:8px 18px;
                          border:1px solid #FECACA; border-radius:10px;
                          font-size:0.82rem; color:#EF4444; text-decoration:none; background:white;">
                    자세히 보기 →
                </a>
            </div>
            """
        )

st.markdown(
    """
    <div style="margin-top:18px; font-size:0.76rem; color:#94A3B8; text-align:center;">
        * 이 추천은 AI 분석 결과이며, 실제 계약 결정은 광고주의 판단에 따라 이루어져야 합니다.
    </div>
    """,
    unsafe_allow_html=True,
)

disclaimer_footer()
