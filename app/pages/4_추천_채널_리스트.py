"""튜브어때 — 추천 채널 전체 리스트 (장기/단기, 페이지네이션)."""

from __future__ import annotations

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
from dummy_data import LONG_TERM_CHANNELS_FULL, SHORT_TERM_CHANNELS_FULL
from styles import inject_global_css

st.set_page_config(
    page_title="튜브어때 — 추천 채널 리스트",
    page_icon="🛟",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
render_sidebar("recommend")

PAGE_SIZE = 50

list_type = st.query_params.get("type", "long")
if list_type not in ("long", "short"):
    list_type = "long"

try:
    current_page = int(st.query_params.get("page", "1"))
except (TypeError, ValueError):
    current_page = 1

if list_type == "short":
    title = "단기 계약 권장 채널"
    subtitle = "주의가 필요한 채널 — 전체 리스트"
    channels = SHORT_TERM_CHANNELS_FULL
else:
    title = "장기 계약 추천 채널"
    subtitle = "안정성이 높은 채널 — 전체 리스트"
    channels = LONG_TERM_CHANNELS_FULL

total = len(channels)
total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
current_page = max(1, min(current_page, total_pages))

start = (current_page - 1) * PAGE_SIZE
visible = channels[start : start + PAGE_SIZE]

page_header(title=title, subtitle=subtitle, right=f"총 {total:,}개")


_TABLE_HEADER = """
<div style="display:flex; padding:6px 4px 8px 4px;
            font-size:0.74rem; color:#94A3B8; font-weight:500;">
    <div style="width:32px;">순위</div>
    <div style="width:32px;"></div>
    <div style="flex-grow:1;">채널</div>
    <div style="min-width:80px; text-align:right;">구독자 수</div>
    <div style="min-width:80px; text-align:right;">이탈 위험도</div>
    <div style="width:44px; text-align:right;">등급</div>
</div>
"""


def _row(c: dict) -> str:
    return f"""
    <div class="tb-rec-row">
        <div class="tb-rec-rank" style="width:32px;">{c['rank']}</div>
        <div class="tb-rec-avatar">👤</div>
        <div class="tb-rec-name">{c['name']}</div>
        <div class="tb-rec-meta" style="min-width:80px;">{c['subs']}</div>
        <div class="tb-rec-meta" style="min-width:80px;">{c['risk']}</div>
        <div style="width:44px; text-align:right;">{grade_badge_html(c['grade'])}</div>
    </div>
    """


with card():
    rows_html = "".join(_row(c) for c in visible)
    st.html(_TABLE_HEADER + rows_html)


# ---- 페이지네이션 ----
def _qs(page_num: int) -> str:
    return urlencode({"type": list_type, "page": page_num})


def _link(label: str, page_num: int, *, active: bool = False, disabled: bool = False) -> str:
    cls = "tb-page-num"
    if active:
        cls += " active"
    if disabled:
        cls += " disabled"
        return f'<span class="{cls}">{label}</span>'
    return f'<a class="{cls}" href="?{_qs(page_num)}" target="_self">{label}</a>'


# 현재 페이지 주변 ±2 + 처음/끝
window = 2
page_nums = sorted(
    {1, total_pages}
    | {p for p in range(current_page - window, current_page + window + 1)
       if 1 <= p <= total_pages}
)

parts: list[str] = []
parts.append(_link("‹", max(1, current_page - 1), disabled=(current_page == 1)))

prev_p = 0
for p in page_nums:
    if p > prev_p + 1:
        parts.append('<span class="tb-page-ellipsis">…</span>')
    parts.append(_link(str(p), p, active=(p == current_page)))
    prev_p = p

parts.append(_link("›", min(total_pages, current_page + 1), disabled=(current_page == total_pages)))

st.html(
    f'<div class="tb-pagination">{"".join(parts)}</div>'
    f'<div class="tb-pagination-info">{start + 1:,} – {min(start + PAGE_SIZE, total):,} / {total:,}</div>'
)

disclaimer_footer()
