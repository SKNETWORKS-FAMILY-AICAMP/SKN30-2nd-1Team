"""튜브어때 — 광고주 추천."""

from __future__ import annotations

from html import escape
import sys
from pathlib import Path
from urllib.parse import urlencode

import streamlit as st

sys.path.append(str(Path(__file__).parent.parent))

from components import (
    card,
    disclaimer_footer,
    grade_badge_html,
    page_header,
    render_sidebar,
)
from data_loader import get_recommended_channels
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

LONG_TERM_FEATURES = [
    {"icon": "📅", "label": "꾸준한 업로드"},
    {"icon": "📊", "label": "안정적인 조회수"},
    {"icon": "👥", "label": "높은 참여율"},
]
PAGE_SIZE = 50
LONG_TERM_CHANNELS = get_recommended_channels("long")

try:
    current_page = int(st.query_params.get("recommend_page", "1"))
except (TypeError, ValueError):
    current_page = 1

total = len(LONG_TERM_CHANNELS)
total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
current_page = max(1, min(current_page, total_pages))
start = (current_page - 1) * PAGE_SIZE
visible_channels = LONG_TERM_CHANNELS[start : start + PAGE_SIZE]


def _channel_row(c: dict) -> str:
    name_link = (
        f'<a href="/채널_조회?channel_id={escape(c["channel_id"], quote=True)}" target="_self"'
        f' style="color:inherit; text-decoration:none; cursor:pointer;">{escape(c["name"])}</a>'
    )
    thumb = c.get("thumbnail_url", "")
    if thumb:
        avatar = f'<img src="{escape(thumb)}" alt="" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">'
    else:
        avatar = "👤"
    return f"""
    <div class="tb-rec-row">
        <div class="tb-rec-rank" style="width:44px;">{c['rank']}</div>
        <div class="tb-rec-avatar">{avatar}</div>
        <div class="tb-rec-name">{name_link}</div>
        <div class="tb-rec-meta" style="min-width:80px;">{c['subs']}</div>
        <div style="width:44px; text-align:right;">{grade_badge_html(c['grade'])}</div>
    </div>
    """


_TABLE_HEADER = """
<div style="display:flex; padding:6px 4px 8px 4px;
            font-size:0.74rem; color:#94A3B8; font-weight:500;">
    <div style="width:44px;">순위</div>
    <div style="width:32px;"></div>
    <div style="flex-grow:1;">채널</div>
    <div style="min-width:80px; text-align:right;">구독자 수</div>
    <div style="width:44px; text-align:right;">등급</div>
</div>
"""


def _qs(page_num: int) -> str:
    return urlencode({"recommend_page": page_num})


def _link(label: str, page_num: int, *, active: bool = False, disabled: bool = False) -> str:
    cls = "tb-page-num"
    if active:
        cls += " active"
    if disabled:
        cls += " disabled"
        return f'<span class="{cls}">{label}</span>'
    return f'<a class="{cls}" href="?{_qs(page_num)}" target="_self">{label}</a>'


def _pagination() -> str:
    window = 2
    page_nums = sorted(
        {1, total_pages}
        | {
            p
            for p in range(current_page - window, current_page + window + 1)
            if 1 <= p <= total_pages
        }
    )
    parts: list[str] = [_link("‹", max(1, current_page - 1), disabled=(current_page == 1))]
    prev_p = 0
    for p in page_nums:
        if p > prev_p + 1:
            parts.append('<span class="tb-page-ellipsis">…</span>')
        parts.append(_link(str(p), p, active=(p == current_page)))
        prev_p = p
    parts.append(_link("›", min(total_pages, current_page + 1), disabled=(current_page == total_pages)))
    return (
        f'<div class="tb-pagination">{"".join(parts)}</div>'
        f'<div class="tb-pagination-info">'
        f'{start + 1:,} – {min(start + PAGE_SIZE, total):,} / {total:,}'
        f'</div>'
    )


with card("장기 계약 추천 채널", "안정성 높음"):
    feats_html = "".join(
        f"""
        <div class="tb-feat-row">
            <div class="tb-feat-icon safe">{f['icon']}</div>
            <div class="tb-feat-label">{f['label']}</div>
        </div>
        """
        for f in LONG_TERM_FEATURES
    )
    st.html(
        f"""
        <div style="display:flex; align-items:center; gap:28px; flex-wrap:wrap;">
            {feats_html}
        </div>
        """
    )

st.write("")

with card("추천 채널 전체 목록", f"총 {total:,}개"):
    rows = "".join(_channel_row(c) for c in visible_channels)
    st.html(_TABLE_HEADER + rows + _pagination())

st.markdown(
    """
    <div style="margin-top:18px; font-size:0.76rem; color:#94A3B8; text-align:center;">
        * 이 추천은 AI 분석 결과이며, 실제 계약 결정은 광고주의 판단에 따라 이루어져야 합니다.
    </div>
    """,
    unsafe_allow_html=True,
)

disclaimer_footer()
