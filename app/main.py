"""튜브어때 — 랜딩 페이지."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).parent))

from components import render_sidebar
from styles import inject_global_css

st.set_page_config(
    page_title="튜브어때 — TubeEottae",
    page_icon="🛟",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
render_sidebar("home")


def _hero_logo_html() -> str:
    """app/assets/logo.{png,jpg,jpeg,webp} 가 있으면 인라인 이미지로 렌더, 없으면 이모지 폴백."""
    assets_dir = Path(__file__).parent / "assets"
    for ext, mime in (("png", "image/png"), ("webp", "image/webp"),
                      ("jpg", "image/jpeg"), ("jpeg", "image/jpeg")):
        candidate = assets_dir / f"logo.{ext}"
        if candidate.exists():
            b64 = base64.b64encode(candidate.read_bytes()).decode("ascii")
            return (
                f'<img class="tb-landing-hero-img" '
                f'src="data:{mime};base64,{b64}" alt="튜브어때 로고" />'
            )
    return '<div class="tb-landing-logo">🛟</div>'


st.markdown(
    f"""
    <div class="tb-landing">
        {_hero_logo_html()}
        <div class="tb-landing-sub">
            YouTube 크리에이터 분석을 통한 광고효율 및 지속가능성 추천 시스템
        </div>
        <div class="tb-landing-divider"></div>
        <div class="tb-landing-tag">데이터 기반 · 머신러닝 · 광고 매칭</div>
    </div>
    """,
    unsafe_allow_html=True,
)

features = [
    {
        "icon": "🏠",
        "title": "대시보드",
        "desc": "전체 채널의 이탈 위험도 분포와 주요 신호를 한눈에 확인합니다.",
        "url": "/대시보드",
    },
    {
        "icon": "🔍",
        "title": "채널 조회",
        "desc": "채널 활동 지속 가능성과 신호별 상세 분석을 한 번에 확인합니다.",
        "url": "/채널_조회",
    },
    {
        "icon": "⭐",
        "title": "광고주 추천",
        "desc": "건강한 채널을 매칭해 광고 의사결정의 참고 자료를 제공합니다.",
        "url": "/광고주_추천",
    },
]

cols = st.columns(3, gap="medium")
for col, f in zip(cols, features):
    with col:
        st.markdown(
            f"""
            <a href="{f['url']}" target="_self" class="tb-landing-card-link">
                <div class="tb-landing-card">
                    <div class="tb-landing-card-icon">{f['icon']}</div>
                    <div class="tb-landing-card-title">{f['title']}</div>
                    <div class="tb-landing-card-desc">{f['desc']}</div>
                    <div class="tb-landing-card-cta">바로가기 →</div>
                </div>
            </a>
            """,
            unsafe_allow_html=True,
        )
