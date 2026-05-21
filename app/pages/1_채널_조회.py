"""튜브어때 — 채널 조회 + 이탈 예측 (핵심 페이지)."""

from __future__ import annotations

from html import escape
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.append(str(Path(__file__).parent.parent))

from components import (
    card,
    chip,
    disclaimer_footer,
    page_header,
    render_sidebar,
)
from data_loader import (
    channel_exists_in_snapshot,
    fetch_channel_dump_for_ui,
    find_channel_by_sql_query,
    get_channel_overview,
    get_channel_prediction,
    get_channel_risk_signals,
    get_channel_shap_proxy,
    get_channel_top_reasons,
    get_channel_trends,
    get_channel_video_stats,
)
from styles import GRADE_A, GRADE_B, GRADE_C, PRIMARY, inject_global_css

st.set_page_config(
    page_title="튜브어때 — 채널 조회",
    page_icon="🛟",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
render_sidebar("channel")

page_header(
    title="채널 조회 + 이탈 예측",
    subtitle="YouTube 채널의 활동 지속 가능성을 분석합니다.",
)

INPUT_REQUIRED_MESSAGE = "Channel ID 또는 YouTube URL을 입력해 주세요."


def _db_int(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "-"


def _db_pct(value) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "-"


def _db_date(value) -> str:
    return value.strftime("%Y.%m.%d") if hasattr(value, "strftime") else "-"


def _safe(value) -> str:
    if value is None:
        return "-"
    return escape(str(value))


def _render_search_placeholder() -> None:
    st.markdown(
        """
        <div style="background:#FFFFFF; border:1px dashed #CBD5E1; border-radius:14px;
                    padding:34px 28px; margin-top:18px; text-align:center;">
            <div style="font-size:2rem; margin-bottom:10px;">🔍</div>
            <div style="font-size:1.18rem; font-weight:800; color:#0F172A;">
                Channel ID 또는 YouTube URL을 입력해 분석을 시작하세요
            </div>
            <div style="font-size:0.86rem; color:#64748B; margin-top:8px; line-height:1.6;">
                먼저 SQL 데이터베이스에서 채널을 찾고, 없으면 yt-dlp로 공개 메타데이터를 가져옵니다.<br>
                상세 위험도 분석은 2026-05-17 스냅샷 데이터에 포함된 채널만 제공됩니다.
            </div>
            <div style="margin-top:18px; display:flex; gap:8px; justify-content:center; flex-wrap:wrap;">
                <span class="tb-chip tb-chip-neutral">UC...</span>
                <span class="tb-chip tb-chip-neutral">https://www.youtube.com/channel/UC...</span>
                <span class="tb-chip tb-chip-neutral">@handle</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sql_only_result(row: dict) -> None:
    st.markdown(
        """
        <div style="background:#FFF7ED; border:1px solid #FED7AA; border-radius:10px;
                    padding:10px 14px; margin: 4px 0 14px; font-size:0.82rem; color:#9A3412;">
            SQL에서는 채널을 찾았지만, 2026-05-17 스냅샷 CSV 분석 데이터에는 없어 상세 차트는 표시하지 않습니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with card("SQL 조회 결과", "youtube_model_db 기준"):
        st.markdown(
            f"""
            <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:16px;">
                <div>
                    <div style="font-size:1.1rem; font-weight:800; color:#0F172A;">{_safe(row.get('channel_name'))}</div>
                    <div style="font-size:0.78rem; color:#64748B; margin-top:4px;">
                        {_safe(row.get('youtube_channel_id'))} · 내부키 {_safe(row.get('channel_identifier'))}
                    </div>
                </div>
                <span class="tb-chip tb-chip-neutral">{_safe(row.get('category_names') or '카테고리 없음')}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        metrics = [
            ("구독자 수", _db_int(row.get("subscriber_count"))),
            ("총 조회수", _db_int(row.get("total_views"))),
            ("영상 수", _db_int(row.get("video_count"))),
            ("최근 업로드", f"{_db_int(row.get('days_since_latest_video'))}일 전"),
            ("이탈 확률", _db_pct(row.get("churn_prob"))),
            ("팬 유형", row.get("fan_type_label") or row.get("fan_type_code") or "-"),
            ("가입일", _db_date(row.get("created_date"))),
            ("마지막 영상일", _db_date(row.get("latest_video_date"))),
        ]
        rows_html = ""
        for i in range(0, len(metrics), 4):
            cells = "".join(
                f"""
                <div style="flex:1; background:#FFFFFF; border:1px solid #F1F5F9;
                            border-radius:10px; padding:12px 14px; min-width:0;">
                    <div style="font-size:0.75rem; color:#64748B; margin-bottom:4px;">{label}</div>
                    <div style="font-size:0.98rem; font-weight:700; color:#0F172A;">{value}</div>
                </div>
                """
                for label, value in metrics[i : i + 4]
            )
            rows_html += f'<div style="display:flex; gap:10px; margin-top:10px;">{cells}</div>'
        st.html(rows_html)


def _fallback_channel_title(dump: dict) -> str:
    entries = dump.get("entries") or []
    first = next((entry for entry in entries if isinstance(entry, dict) and not entry.get("error")), {})
    return (
        dump.get("channel")
        or dump.get("uploader")
        or dump.get("title")
        or first.get("channel")
        or first.get("uploader")
        or "YouTube 채널"
    )


def _fallback_channel_id(dump: dict) -> str:
    entries = dump.get("entries") or []
    first = next((entry for entry in entries if isinstance(entry, dict) and not entry.get("error")), {})
    return dump.get("channel_id") or first.get("channel_id") or "-"


def _fallback_upload_date(video: dict) -> str:
    raw = str(video.get("upload_date") or "")
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}.{raw[4:6]}.{raw[6:8]}"
    return raw or "-"


def _render_fallback_dump(dump: dict) -> None:
    entries = [entry for entry in dump.get("entries", []) if isinstance(entry, dict)]
    good_entries = [entry for entry in entries if not entry.get("error")]
    view_total = sum(int(v.get("view_count") or 0) for v in good_entries)
    latest = next((entry for entry in good_entries if entry.get("upload_date")), None)

    st.markdown(
        """
        <div style="background:#ECFEFF; border:1px solid #A5F3FC; border-radius:10px;
                    padding:10px 14px; margin: 4px 0 14px; font-size:0.82rem; color:#155E75;">
            실시간 수집 결과입니다. 이 화면은 예측 결과가 아닌 공개 메타데이터 미리보기이며,
            위험도 게이지와 상세 차트는 2026-05-17 스냅샷 분석 데이터에 포함된 채널만 표시됩니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with card("실시간 수집 결과", "yt-dlp 공개 메타데이터 기준"):
        st.markdown(
            f"""
            <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:16px;">
                <div>
                    <div style="font-size:1.1rem; font-weight:800; color:#0F172A;">
                        {_safe(_fallback_channel_title(dump))}
                    </div>
                    <div style="font-size:0.78rem; color:#64748B; margin-top:4px;">
                        {_safe(_fallback_channel_id(dump))}
                    </div>
                </div>
                <span class="tb-chip tb-chip-neutral">분석 대기</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        metrics = [
            ("수집 영상 수", f"{len(good_entries):,}개"),
            ("총 조회수", _db_int(view_total)),
            ("최근 영상일", _fallback_upload_date(latest or {})),
            ("수집 상태", "화면 표시 전용"),
        ]
        rows_html = ""
        for label, value in metrics:
            rows_html += f"""
            <div style="flex:1; background:#FFFFFF; border:1px solid #F1F5F9;
                        border-radius:10px; padding:12px 14px; min-width:0;">
                <div style="font-size:0.75rem; color:#64748B; margin-bottom:4px;">{label}</div>
                <div style="font-size:0.98rem; font-weight:700; color:#0F172A;">{_safe(value)}</div>
            </div>
            """
        st.html(f'<div style="display:flex; gap:10px; margin-top:12px; flex-wrap:wrap;">{rows_html}</div>')

    with card("최근 영상", f"최대 {len(good_entries):,}개"):
        if not good_entries:
            st.info("표시할 공개 영상 메타데이터가 없습니다.")
            return
        video_rows = ""
        for video in good_entries[:12]:
            title = _safe(video.get("title") or "제목 없음")
            date = _safe(_fallback_upload_date(video))
            views = _db_int(video.get("view_count"))
            likes = _db_int(video.get("like_count"))
            comments = _db_int(video.get("comment_count"))
            url = _safe(video.get("webpage_url") or "")
            title_html = f'<a href="{url}" target="_blank" style="color:#0F172A; text-decoration:none;">{title}</a>' if url else title
            video_rows += f"""
            <div style="display:flex; justify-content:space-between; gap:14px;
                        padding:12px 0; border-bottom:1px solid #F1F5F9;">
                <div style="min-width:0;">
                    <div style="font-size:0.92rem; font-weight:700; color:#0F172A;
                                overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                        {title_html}
                    </div>
                    <div style="font-size:0.74rem; color:#64748B; margin-top:4px;">{date}</div>
                </div>
                <div style="font-size:0.76rem; color:#475569; white-space:nowrap; text-align:right;">
                    조회 {views}<br>좋아요 {likes} · 댓글 {comments}
                </div>
            </div>
            """
        st.html(video_rows)


# ---- 검색 바 ----
search_col, btn_col = st.columns([6, 1])
with search_col:
    query = st.text_input(
        "search",
        placeholder="🔍   Channel ID 또는 YouTube URL 입력",
        label_visibility="collapsed",
        key="channel_query",
    )
with btn_col:
    search_clicked = st.button("분석하기", type="primary", use_container_width=True)

if search_clicked:
    st.session_state.pop("channel_lookup_row", None)
    st.session_state.pop("channel_lookup_error", None)
    st.session_state.pop("channel_fallback_dump", None)
    st.session_state.pop("channel_fallback_error", None)
    st.session_state["channel_lookup_submitted"] = True
    if query.strip():
        with st.spinner("SQL에서 채널을 조회하는 중입니다..."):
            row, error = find_channel_by_sql_query(query)
        st.session_state["channel_lookup_row"] = row
        st.session_state["channel_lookup_error"] = error
        if row is None and error is None:
            with st.spinner("SQL에 없어 YouTube 공개 메타데이터를 수집하는 중입니다..."):
                dump, fallback_error = fetch_channel_dump_for_ui(query)
            st.session_state["channel_fallback_dump"] = dump
            st.session_state["channel_fallback_error"] = fallback_error
    else:
        st.session_state["channel_lookup_error"] = INPUT_REQUIRED_MESSAGE

lookup_row = st.session_state.get("channel_lookup_row")
lookup_error = st.session_state.get("channel_lookup_error")
lookup_submitted = st.session_state.get("channel_lookup_submitted", False)
fallback_dump = st.session_state.get("channel_fallback_dump")
fallback_error = st.session_state.get("channel_fallback_error")

if lookup_error:
    if lookup_error == INPUT_REQUIRED_MESSAGE:
        st.warning(lookup_error)
    else:
        st.error(f"SQL 조회 중 문제가 발생했습니다: {lookup_error}")
    st.stop()

if not lookup_submitted:
    _render_search_placeholder()
    st.stop()

if lookup_row is None:
    if fallback_dump is not None:
        _render_fallback_dump(fallback_dump)
        disclaimer_footer()
    elif fallback_error:
        st.warning(f"SQL 데이터베이스와 YouTube 공개 메타데이터에서 채널을 찾지 못했습니다: {fallback_error}")
    else:
        st.warning("SQL 데이터베이스와 YouTube 공개 메타데이터에서 채널을 찾지 못했습니다.")
    st.stop()

channel_id = lookup_row["youtube_channel_id"]

if lookup_row and not channel_exists_in_snapshot(channel_id):
    _render_sql_only_result(lookup_row)
    disclaimer_footer()
    st.stop()

ch = get_channel_overview(channel_id)
pred = get_channel_prediction(channel_id)
reasons = get_channel_top_reasons(channel_id)
trends = get_channel_trends(channel_id, n_months=12)
stats = get_channel_video_stats(channel_id)
risk_signals = get_channel_risk_signals(channel_id)
shap_factors = get_channel_shap_proxy(channel_id)

st.markdown(
    f"""
    <div style="background:#EEF2FF; border:1px solid #C7D2FE; border-radius:10px;
                padding:10px 14px; margin: 4px 0 14px; font-size:0.82rem; color:#3730A3;">
        ℹ️ {("SQL 조회 결과" if lookup_row else "예시 채널")}: <b>{ch['name']}</b>
        {f"({lookup_row['youtube_channel_id']})" if lookup_row else "(검색어를 입력하고 분석하기를 누르면 SQL에서 채널을 조회합니다)"}
    </div>
    """,
    unsafe_allow_html=True,
)

GRADE_COLOR = {"A": GRADE_A, "B": GRADE_B, "C": GRADE_C}
GRADE_BG = {"A": "#ECFDF5", "B": "#FFFBEB", "C": "#FEF2F2"}
GRADE_LABEL = {"A": "안심", "B": "관찰", "C": "주의"}

# ---- 좌(채널 정보) / 우(예측 결과) ----
left, right = st.columns([1, 1.2], gap="medium")

with left:
    with card("채널 기본 정보"):
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:14px; margin-bottom:18px;">
                <div style="width:64px; height:64px; border-radius:50%;
                            background: linear-gradient(135deg,#A5B4FC,#6366F1);
                            display:flex; align-items:center; justify-content:center;
                            color:white; font-size:1.6rem;">{ch['category_emoji']}</div>
                <div>
                    <div style="font-size:1.05rem; font-weight:700; color:#0F172A;">{ch['name']}</div>
                    <div style="font-size:0.82rem; color:#64748B; margin-top:2px;">
                        {ch['handle']} · <span class="tb-chip tb-chip-neutral" style="margin-left:4px;">{ch['category']}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        delta_color = "#EF4444" if ch["avg_view_delta"].startswith("-") else "#10B981"
        metric_pairs = [
            ("구독자 수", ch["subscriber_count"]),
            ("총 조회수", ch["total_views"]),
            ("가입일", ch["joined_at"]),
            (
                "최근 업로드",
                f"{ch['last_upload_days']}<div style='font-size:0.72rem; color:#94A3B8;'>{ch['last_upload_date']}</div>",
            ),
            ("최근 30일 업로드 수", ch["uploads_30d"]),
            (
                "평균 조회수 (최근 5개)",
                f"{ch['avg_view']}<span style='color:{delta_color}; font-size:0.78rem; margin-left:6px;'>{ch['avg_view_delta']}</span>",
            ),
        ]
        rows_html = ""
        for i in range(0, len(metric_pairs), 2):
            cells = ""
            for j in range(2):
                if i + j < len(metric_pairs):
                    label, value = metric_pairs[i + j]
                    cells += f"""
                    <div style="flex:1; background:#FFFFFF; border:1px solid #F1F5F9;
                                border-radius:10px; padding:12px 14px;">
                        <div style="font-size:0.75rem; color:#64748B; margin-bottom:4px;">{label}</div>
                        <div style="font-size:0.98rem; font-weight:700; color:#0F172A;">{value}</div>
                    </div>
                    """
            rows_html += f'<div style="display:flex; gap:10px; margin-bottom:10px;">{cells}</div>'
        st.html(rows_html)

with right:
    grade = pred["grade"]
    risk_pct = pred["risk_pct"]
    g_color = GRADE_COLOR[grade]
    g_bg = GRADE_BG[grade]
    chip_kind = {"A": "positive", "B": "warning", "C": "danger"}[grade]

    with card():
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; justify-content:space-between;">
                <div class="tb-card-title">이탈 예측 결과</div>
                <div>{chip(GRADE_LABEL[grade], chip_kind)}</div>
            </div>
            <div style="display:flex; align-items:center; gap:24px; margin-top:18px;
                        background: linear-gradient(180deg, {g_bg} 0%, #FFFFFF 80%);
                        border-radius: 12px; padding: 18px 18px;">
                <div style="position:relative;">
                    <div style="width:108px; height:108px; border-radius:50%;
                                background:{g_color};
                                box-shadow: 0 8px 22px {g_color}33;
                                display:flex; align-items:center; justify-content:center;
                                color:white; font-size:3rem; font-weight:800;">{grade}</div>
                    <div style="font-size:0.7rem; color:#64748B; text-align:center; margin-top:6px;">등급</div>
                </div>
                <div style="flex-grow:1;">
                    <div style="font-size:0.82rem; color:#64748B;">이탈 위험도</div>
                    <div style="font-size:2.4rem; font-weight:800; color:{g_color}; letter-spacing:-1px; line-height:1;">{risk_pct}<span style="font-size:1.2rem;">%</span></div>
                    <div class="tb-gauge-wrap">
                        <div class="tb-gauge-track">
                            <div class="tb-gauge-marker" style="left:{risk_pct}%;"></div>
                        </div>
                        <div class="tb-gauge-scale">
                            <span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with card(f"주요 위험 사유 TOP {len(reasons)}"):
        reasons_html = "".join(
            f"""
            <div class="tb-reason">
                <div class="tb-reason-num">{i}</div>
                <div>
                    <div class="tb-reason-title">{r['title']}</div>
                    <div class="tb-reason-desc">{r['desc']}</div>
                </div>
            </div>
            """
            for i, r in enumerate(reasons, 1)
        )
        st.markdown(reasons_html, unsafe_allow_html=True)

st.write("")

# ---- 요약 지표 (3개) ----
with card("요약 지표", "wide CSV 기준"):
    sum_cols = st.columns(3, gap="medium")
    tone_color = {"danger": "#EF4444", "warning": "#F59E0B", "positive": "#10B981"}
    for col, m in zip(sum_cols, pred["summary"]):
        color = tone_color.get(m["tone"], "#64748B")
        with col:
            st.markdown(
                f"""
                <div style="background:#FFFFFF; border:1px solid #F1F5F9; border-radius:12px; padding:14px 16px;">
                    <div style="font-size:0.78rem; color:#64748B; margin-bottom:6px;">{m['label']}</div>
                    <div style="font-size:1.35rem; font-weight:700; color:#0F172A;">{m['value']}</div>
                    <div style="font-size:0.76rem; color:{color}; margin-top:4px;">{m['delta']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.write("")

# ---- 상세 분석 ----
st.markdown("<div class='tb-page-title' style='font-size:1.2rem;'>상세 분석</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='tb-page-sub'>업로드/조회수/참여율 추이와 영상별 분포를 확인합니다.</div>",
    unsafe_allow_html=True,
)


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


def _line_chart(xs, ys, color, ysuffix="", height=220, fill=True):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs, y=ys, mode="lines+markers",
            line=dict(color=color, width=2.4, shape="spline"),
            marker=dict(size=5, color=color, line=dict(color="white", width=1.2)),
            fill="tozeroy" if fill else None,
            fillcolor=f"rgba({_hex_to_rgb(color)},0.10)" if fill else None,
            hovertemplate="%{x}<br>%{y}" + ysuffix + "<extra></extra>",
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(showgrid=False, color="#94A3B8", tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", color="#94A3B8",
                   tickfont=dict(size=10), ticksuffix=ysuffix),
    )
    return fig


def _bar_chart(xs, ys, color, ysuffix="", height=220, text_format=None):
    text = [text_format(v) if text_format else str(v) for v in ys]
    fig = go.Figure(
        data=[
            go.Bar(
                x=xs, y=ys,
                marker=dict(color=color, line=dict(width=0)),
                text=text, textposition="outside",
                textfont=dict(color="#475569", size=10),
                hovertemplate="%{x}<br>%{y}" + ysuffix + "<extra></extra>",
            )
        ]
    )
    y_max = max(ys) if ys else 0
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=18, b=8),
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        bargap=0.35,
        xaxis=dict(showgrid=False, color="#94A3B8", tickfont=dict(size=10)),
        yaxis=dict(
            showgrid=True, gridcolor="#F1F5F9", color="#94A3B8",
            tickfont=dict(size=10), ticksuffix=ysuffix,
            range=[0, max(y_max * 1.2, 1)],
        ),
    )
    return fig


def _mini_kpi(label: str, value: str, color: str = "#0F172A") -> str:
    return f"""
    <div style="background:#FFFFFF; border:1px solid #F1F5F9; border-radius:12px;
                padding:14px 16px;">
        <div style="font-size:0.75rem; color:#64748B; margin-bottom:6px;">{label}</div>
        <div style="font-size:1.25rem; font-weight:700; color:{color};">{value}</div>
    </div>
    """


tabs = st.tabs(["종합 분석", "업로드 분석", "조회수 분석", "참여율 분석"])

# ── 종합 분석 ─────────────────────────────────────────────
with tabs[0]:
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with card("월별 업로드", "최근 12개월"):
            xs = [p[0] for p in trends["upload"]]
            ys = [p[1] for p in trends["upload"]]
            st.plotly_chart(
                _bar_chart(xs, ys, "#C7D2FE", ysuffix="개", height=220),
                use_container_width=True, config={"displayModeBar": False},
            )

    with c2:
        with card("월별 평균 조회수", "최근 12개월"):
            xs = [p[0] for p in trends["view"]]
            ys = [round(p[1]) for p in trends["view"]]
            st.plotly_chart(
                _line_chart(xs, ys, PRIMARY, ysuffix="", height=220),
                use_container_width=True, config={"displayModeBar": False},
            )

    c3, c4 = st.columns(2, gap="medium")
    with c3:
        with card("월별 참여율", "(좋아요+댓글) / 조회수"):
            xs = [p[0] for p in trends["engagement"]]
            ys = [round(p[1], 2) for p in trends["engagement"]]
            st.plotly_chart(
                _line_chart(xs, ys, "#A855F7", ysuffix="%", height=220),
                use_container_width=True, config={"displayModeBar": False},
            )

    with c4:
        with card("Shorts vs 일반 영상", "수집 영상 50개 기준"):
            sr = stats["summary"]["shorts_ratio"]
            shorts_pct = sr * 100
            normal_pct = (1 - sr) * 100
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=["Shorts", "일반 영상"],
                        values=[shorts_pct, normal_pct],
                        hole=0.65,
                        marker=dict(colors=["#F59E0B", PRIMARY], line=dict(color="white", width=2)),
                        textinfo="none",
                        hovertemplate="%{label}<br>%{value:.0f}%<extra></extra>",
                        sort=False,
                    )
                ]
            )
            fig.update_layout(
                height=220,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
                paper_bgcolor="white", plot_bgcolor="white",
                annotations=[
                    dict(text="Shorts 비율", x=0.5, y=0.58, font_size=11, font_color="#94A3B8", showarrow=False),
                    dict(text=f"{shorts_pct:.0f}%", x=0.5, y=0.42, font_size=24, font_color="#0F172A", showarrow=False),
                ],
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ── 업로드 분석 ───────────────────────────────────────────
with tabs[1]:
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with card("월별 업로드 횟수", "최근 12개월"):
            xs = [p[0] for p in trends["upload"]]
            ys = [p[1] for p in trends["upload"]]
            st.plotly_chart(
                _bar_chart(xs, ys, PRIMARY, ysuffix="개", height=260),
                use_container_width=True, config={"displayModeBar": False},
            )

    with c2:
        with card("업로드 간격 분포", "영상 사이 일수"):
            intervals = stats["upload_intervals"]
            bins = [(0, 5, "0~5일"), (5, 15, "5~15일"), (15, 30, "15~30일"),
                    (30, 60, "30~60일"), (60, 180, "60~180일"), (180, 10_000, "180일+")]
            counts = [sum(1 for v in intervals if lo <= v < hi) for lo, hi, _ in bins]
            labels = [lb for _, _, lb in bins]
            st.plotly_chart(
                _bar_chart(labels, counts, "#A5B4FC", ysuffix="회", height=260),
                use_container_width=True, config={"displayModeBar": False},
            )

    s = stats["summary"]
    kpi_cols = st.columns(3, gap="medium")
    with kpi_cols[0]:
        st.html(_mini_kpi("평균 업로드 주기", f"{s['avg_interval_days']:.1f}일"))
    with kpi_cols[1]:
        st.html(_mini_kpi("역대 최대 공백", f"{s['max_gap_days']:,}일",
                           color="#EF4444" if s["max_gap_days"] > 90 else "#0F172A"))
    with kpi_cols[2]:
        st.html(_mini_kpi("30일+ 공백 횟수", f"{s['hiatus_count_30d']}회",
                           color="#F59E0B" if s["hiatus_count_30d"] > 0 else "#0F172A"))

# ── 조회수 분석 ───────────────────────────────────────────
with tabs[2]:
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with card("월별 평균 조회수", "최근 12개월"):
            xs = [p[0] for p in trends["view"]]
            ys = [round(p[1]) for p in trends["view"]]
            st.plotly_chart(
                _line_chart(xs, ys, PRIMARY, ysuffix="", height=260),
                use_container_width=True, config={"displayModeBar": False},
            )

    with c2:
        with card("영상별 조회수 분포", "상위 20개 영상"):
            top20 = sorted(stats["view_distribution"], reverse=True)[:20]
            ranks = [f"#{i + 1}" for i in range(len(top20))]
            st.plotly_chart(
                _bar_chart(ranks, top20, "#C7D2FE", ysuffix="", height=260),
                use_container_width=True, config={"displayModeBar": False},
            )

    s = stats["summary"]
    kpi_cols = st.columns(3, gap="medium")
    with kpi_cols[0]:
        st.html(_mini_kpi("평균 조회수", f"{int(s['avg_view']):,}"))
    with kpi_cols[1]:
        cv = s["std_view"] / s["avg_view"] if s["avg_view"] > 0 else 0
        st.html(_mini_kpi("조회수 표준편차", f"{int(s['std_view']):,}",
                           color="#EF4444" if cv > 1 else "#0F172A"))
    with kpi_cols[2]:
        st.html(_mini_kpi("최고 조회수", f"{s['max_view']:,}"))

# ── 참여율 분석 ──────────────────────────────────────────
with tabs[3]:
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with card("월별 참여율 추이", "(좋아요+댓글) / 조회수"):
            xs = [p[0] for p in trends["engagement"]]
            ys = [round(p[1], 2) for p in trends["engagement"]]
            st.plotly_chart(
                _line_chart(xs, ys, "#A855F7", ysuffix="%", height=260),
                use_container_width=True, config={"displayModeBar": False},
            )

    with c2:
        with card("좋아요·댓글 비율 추이", "조회수 대비 %"):
            xs = [p[0] for p in trends["like_ratio"]]
            like_ys = [round(p[1], 2) for p in trends["like_ratio"]]
            comm_ys = [round(p[1], 3) for p in trends["comment_ratio"]]
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=xs, y=like_ys, mode="lines+markers", name="좋아요/조회수",
                    line=dict(color=GRADE_A, width=2.4, shape="spline"),
                    marker=dict(size=5, color=GRADE_A),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=xs, y=comm_ys, mode="lines+markers", name="댓글/조회수",
                    line=dict(color=GRADE_C, width=2.4, shape="spline", dash="dot"),
                    marker=dict(size=5, color=GRADE_C),
                )
            )
            fig.update_layout(
                height=260,
                margin=dict(l=8, r=8, t=8, b=8),
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", x=0, y=1.18, font=dict(size=10, color="#64748B")),
                xaxis=dict(showgrid=False, color="#94A3B8", tickfont=dict(size=10)),
                yaxis=dict(showgrid=True, gridcolor="#F1F5F9", color="#94A3B8",
                           tickfont=dict(size=10), ticksuffix="%"),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    s = stats["summary"]
    kpi_cols = st.columns(3, gap="medium")
    with kpi_cols[0]:
        st.html(_mini_kpi("평균 참여율", f"{s['avg_engagement_rate']:.2f}%",
                           color="#EF4444" if s["avg_engagement_rate"] < 1 else "#0F172A"))
    with kpi_cols[1]:
        st.html(_mini_kpi("평균 좋아요 비율", f"{s['avg_like_rate']:.2f}%"))
    with kpi_cols[2]:
        st.html(_mini_kpi("평균 댓글 비율", f"{s['avg_comment_rate']:.3f}%"))

st.write("")

# ---- 위험 신호 요약 + SHAP ----
sl, sr = st.columns([1.2, 1], gap="medium")

with sl:
    with card("위험 신호 요약"):
        cards_cols = st.columns(4, gap="small")
        tone_to_chip = {"danger": "danger", "warning": "warning", "positive": "positive"}
        tone_to_color = {"danger": GRADE_C, "warning": GRADE_B, "positive": GRADE_A}
        for col, sig in zip(cards_cols, risk_signals):
            color = tone_to_color.get(sig["tone"], "#64748B")
            with col:
                st.markdown(
                    f"""
                    <div style="background:#FFFFFF; border:1px solid #F1F5F9; border-radius:12px;
                                padding:14px 14px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="width:8px; height:8px; border-radius:50%; background:{color};"></span>
                            <div style="font-size:0.85rem; font-weight:600; color:#0F172A;">{sig['label']}</div>
                        </div>
                        <div style="font-size:0.74rem; color:#64748B; margin-top:8px; line-height:1.4;">
                            {sig['desc']}
                        </div>
                        <div style="margin-top:10px;">{chip(f"위험도 {sig['level']}", tone_to_chip.get(sig['tone'], 'neutral'))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

with sr:
    with card("위험 기여도", "룰 기반 (SHAP 모델 대체)"):
        labels = [s["label"] for s in shap_factors]
        values = [s["value"] for s in shap_factors]
        fig = go.Figure(
            data=[
                go.Bar(
                    y=labels[::-1],
                    x=values[::-1],
                    orientation="h",
                    marker=dict(color="#FCA5A5", line=dict(color=GRADE_C, width=0)),
                    text=[f"+{v:.2f}" for v in values[::-1]],
                    textposition="outside",
                    textfont=dict(color="#475569", size=11),
                )
            ]
        )
        fig.update_layout(
            height=240,
            margin=dict(l=8, r=40, t=8, b=8),
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(showgrid=True, gridcolor="#F1F5F9", color="#94A3B8",
                       tickfont=dict(size=10), range=[0, 0.55]),
            yaxis=dict(showgrid=False, color="#0F172A", tickfont=dict(size=11)),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

disclaimer_footer()
