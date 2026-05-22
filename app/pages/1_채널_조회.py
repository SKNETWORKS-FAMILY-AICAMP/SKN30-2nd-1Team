"""튜브어때 — 채널 조회 + 이탈 예측 (핵심 페이지)."""

from __future__ import annotations

import html as _html
import sys
from pathlib import Path

import pandas as pd
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
    get_channel_overview,
    get_channel_prediction,
    get_channel_top_reasons,
    find_channel_id_in_all_channels,
    get_sql_export_stats,
    get_channel_thumbnail,
    get_growth_score,
    load_long,
)
from styles import inject_global_css
from churn_predictor import predict_for_query

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

st.markdown(
    """
    <style>
        div[data-testid="stButton"] > button:not([kind="primary"]) {
            height: 44px;
            min-width: 44px;
            padding: 0;
            border-radius: 10px;
            border: 1px solid #E2E8F0;
            background: #FFFFFF;
            color: #64748B;
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1;
        }
        div[data-testid="stButton"] > button:not([kind="primary"]):hover {
            border-color: #CBD5E1;
            background: #F8FAFC;
            color: #0F172A;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


_C = {"primary": "#6366F1", "green": "#10B981", "amber": "#F59E0B", "red": "#EF4444", "gray": "#94A3B8"}
_PLOTLY_CFG = {"displayModeBar": False}


def _fmt_int(value: float | int | None) -> str:
    try:
        if value is None or pd.isna(value):
            return "-"
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return "-"


def _fmt_days(value: float | int | None) -> str:
    base = _fmt_int(value)
    return "-" if base == "-" else f"{base}일"


def _chart_layout(title: str, ytitle: str = "", **extra) -> dict:
    base = dict(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=11, color="#0F172A"),
        margin=dict(l=40, r=10, t=16, b=96),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(color="#334155", size=11)),
        hovermode="x unified",
        title=dict(text=""),
        xaxis=dict(type="date", tickformat="%y.%m", showgrid=False,
                   linecolor="#E2E8F0", linewidth=1,
                   tickfont=dict(color="#9b9b9b"), title=dict(font=dict(color="#9b9b9b"))),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", linecolor="#E2E8F0", linewidth=1,
                   tickfont=dict(color="#9b9b9b"),
                   title=dict(text=ytitle, font=dict(color="#9b9b9b"))),
    )
    base.update(extra)
    return base



def _render_video_charts(df: pd.DataFrame) -> None:
    """영상 단위 DataFrame으로 2×2 시계열 차트 렌더링.

    df 필수 컬럼: date(datetime), view_count, like_count, comment_count
    df 선택 컬럼: is_shorts(bool)
    """
    df = df.copy().sort_values("date").reset_index(drop=True)
    if df.empty:
        st.caption("날짜 정보가 없어 차트를 표시할 수 없습니다.")
        return

    df["engagement"]   = (df["like_count"] + df["comment_count"]) / (df["view_count"] + 1e-9) * 100
    df["like_rate"]    = df["like_count"]    / (df["view_count"] + 1e-9) * 100
    df["comment_rate"] = df["comment_count"] / (df["view_count"] + 1e-9) * 100
    df["rolling_avg"]  = df["view_count"].rolling(5, min_periods=1).mean()
    df["interval"]     = df["date"].diff().dt.days
    has_shorts = "is_shorts" in df.columns

    n          = len(df)
    mode       = "lines+markers" if n <= 20 else "lines"
    tick_fmt   = "%Y.%m.%d"
    last_date  = df["date"].max()
    last_label = last_date.strftime("%Y.%m.%d")

    def _labels(fig: go.Figure, title: str, subtitle: str = "") -> None:
        fig.add_annotation(
            text=f"<b>{title}</b>",
            xref="paper", yref="paper",
            x=0.5, y=-0.10,
            showarrow=False,
            font=dict(size=13, color="#475569", family="Inter, sans-serif"),
            xanchor="center", yanchor="top",
        )
        if subtitle:
            fig.add_annotation(
                text=subtitle,
                xref="paper", yref="paper",
                x=0.5, y=-0.15,
                showarrow=False,
                font=dict(size=10, color="#94A3B8", family="Inter, sans-serif"),
                xanchor="center", yanchor="top",
            )
        fig.add_annotation(
            text=f"마지막 업로드: {last_label}",
            xref="paper", yref="paper",
            x=0, y=-0.32,
            showarrow=False,
            font=dict(size=10, color="#64748B"),
            xanchor="left", yanchor="top",
        )

    col1, col2 = st.columns(2)

    # ── 조회수 추이 ──────────────────────────────────────────────────
    with col1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=df["date"], y=df["view_count"],
            name="조회수",
            mode=mode,
            line=dict(color=_C["primary"], width=2),
            marker=dict(size=6, color=_C["primary"]),
            fill="tozeroy",
            fillcolor="rgba(99,102,241,0.12)",
            hovertemplate="%{x|" + tick_fmt + "}<br>조회수: %{y:,}<extra></extra>",
        ))
        if n >= 3:
            fig1.add_trace(go.Scatter(
                x=df["date"], y=df["rolling_avg"],
                name="이동평균 (5구간)",
                mode="lines",
                line=dict(color=_C["red"], width=2, dash="dot"),
                hovertemplate="이동평균: %{y:,.0f}<extra></extra>",
            ))
        _labels(fig1, "조회수 추이", "업로드일별 영상 조회수 · 점선=5구간 이동평균")
        fig1.update_layout(**_chart_layout("", "조회수"))
        st.plotly_chart(fig1, use_container_width=True, config=_PLOTLY_CFG)

    # ── 참여율 추이 ──────────────────────────────────────────────────
    with col2:
        if has_shorts:
            marker_colors = [_C["amber"] if s else _C["primary"] for s in df["is_shorts"]]
            shorts_note = " · 주황=Shorts"
        else:
            marker_colors = _C["primary"]
            shorts_note = ""
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df["date"], y=df["engagement"],
            name="참여율  =  (좋아요+댓글) ÷ 조회수",
            mode="lines+markers",
            line=dict(color=_C["green"], width=2),
            marker=dict(color=marker_colors, size=7, line=dict(width=1.5, color="white")),
            fill="tozeroy",
            fillcolor="rgba(16,185,129,0.10)",
            hovertemplate="%{x|" + tick_fmt + "}<br>참여율: %{y:.2f}%<extra></extra>",
        ))
        _labels(fig2, f"참여율 추이{shorts_note}", "(좋아요+댓글) ÷ 조회수 × 100")
        fig2.update_layout(**_chart_layout("", "참여율 (%)"))
        st.plotly_chart(fig2, use_container_width=True, config=_PLOTLY_CFG)

    col3, col4 = st.columns(2)

    # ── 좋아요율 / 댓글율 ───────────────────────────────────────────
    with col3:
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=df["date"], y=df["like_rate"],
            name="좋아요율  =  좋아요 ÷ 조회수",
            mode="lines+markers",
            line=dict(color=_C["primary"], width=2),
            marker=dict(size=5, color=_C["primary"]),
            hovertemplate="%{x|" + tick_fmt + "}<br>좋아요율: %{y:.2f}%<extra></extra>",
        ))
        fig3.add_trace(go.Scatter(
            x=df["date"], y=df["comment_rate"],
            name="댓글율  =  댓글 ÷ 조회수",
            mode="lines+markers",
            line=dict(color=_C["amber"], width=2),
            marker=dict(size=5, color=_C["amber"]),
            hovertemplate="%{x|" + tick_fmt + "}<br>댓글율: %{y:.3f}%<extra></extra>",
        ))
        _labels(fig3, "좋아요율 · 댓글율", "조회수 대비 각 반응의 비율")
        fig3.update_layout(**_chart_layout("", "비율 (%)"))
        st.plotly_chart(fig3, use_container_width=True, config=_PLOTLY_CFG)

    # ── 업로드 간격 ──────────────────────────────────────────────────
    with col4:
        if n < 2:
            st.caption("영상이 2개 미만이어서 간격을 표시할 수 없습니다.")
        else:
            gap_df     = df.iloc[1:].copy()
            bar_colors = [_C["red"] if v >= 30 else _C["primary"] for v in gap_df["interval"]]
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(
                x=gap_df["date"],
                y=gap_df["interval"],
                name="업로드 간격 (일)  ·  빨강=30일 초과",
                marker_color=bar_colors,
                opacity=0.8,
                hovertemplate="%{x|" + tick_fmt + "}<br>간격: %{y}일<extra></extra>",
            ))
            fig4.add_hline(
                y=30, line_dash="dot", line_color=_C["red"], opacity=0.5,
                annotation_text="30일 기준선", annotation_position="top right",
                annotation_font=dict(size=10, color=_C["red"]),
            )
            _labels(fig4, "업로드 간격", "연속 영상 사이의 날짜 차이 · 빨강=30일 초과")
            fig4.update_layout(**_chart_layout("", "간격 (일)", bargap=0.3))
            st.plotly_chart(fig4, use_container_width=True, config=_PLOTLY_CFG)


def _render_live_charts(entries: list[dict]) -> None:
    """실시간 수집된 50개 영상 entries로 시계열 차트 렌더링."""
    df = pd.DataFrame(entries)
    df["date"] = pd.to_datetime(df["upload_date"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["date"])
    if "duration" in df.columns:
        df["is_shorts"] = df["duration"] <= 60
    _render_video_charts(df)


def _render_csv_charts(channel_id: str) -> None:
    """CSV long 데이터 기반 영상 단위 시계열 차트 렌더링."""
    long = load_long()
    sub = long[long["channel_id"] == channel_id].copy()
    if sub.empty:
        st.caption("영상 데이터가 없습니다.")
        return
    sub["date"] = sub["published_at"].dt.tz_localize(None)
    sub = sub.rename(columns={"view_count": "view_count", "like_count": "like_count",
                               "comment_count": "comment_count"})
    chart_df = sub[["date", "view_count", "like_count", "comment_count"]]
    _render_video_charts(chart_df)


def _entries_to_latest_videos(entries: list[dict]) -> list[dict]:
    """실시간 entries에서 최신 5개 영상 dict 반환."""
    top5 = sorted(entries, key=lambda x: x.get("upload_date", ""), reverse=True)[:5]
    result = []
    for e in top5:
        ud = e.get("upload_date", "")
        date_str = f"{ud[:4]}.{ud[4:6]}.{ud[6:]}" if len(ud) == 8 else "-"
        result.append({
            "thumbnail": e.get("thumbnail", ""),
            "title": e.get("title", ""),
            "url": e.get("webpage_url", ""),
            "view_count": int(e.get("view_count") or 0),
            "like_count": int(e.get("like_count") or 0),
            "comment_count": int(e.get("comment_count") or 0),
            "upload_date": date_str,
        })
    return result


def _get_latest_videos_from_csv(channel_id: str) -> list[dict]:
    """CSV long 데이터에서 채널 최신 5개 영상 dict 반환. 썸네일은 video_id로 생성."""
    long = load_long()
    sub = long[long["channel_id"] == channel_id].copy()
    if sub.empty:
        return []
    sub = sub.sort_values("published_at", ascending=False).head(5)
    result = []
    for _, row in sub.iterrows():
        vid_id = str(row.get("video_id", "") or "")
        date_val = row.get("published_at")
        date_str = str(date_val)[:10] if pd.notna(date_val) else "-"
        result.append({
            "thumbnail": f"https://i.ytimg.com/vi/{vid_id}/mqdefault.jpg" if vid_id else "",
            "title": str(row.get("video_title", "") or ""),
            "url": f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "",
            "view_count": int(row.get("view_count") or 0),
            "like_count": int(row.get("like_count") or 0),
            "comment_count": int(row.get("comment_count") or 0),
            "upload_date": date_str,
        })
    return result


def _render_latest_videos(videos: list[dict]) -> None:
    """최신 영상 5개 썸네일 카드 렌더링 (썸네일→제목→조회수·좋아요·댓글)."""
    if not videos:
        return

    cols = st.columns(len(videos))
    for col, v in zip(cols, videos):
        with col:
            raw_title = v["title"]
            title_short = raw_title[:36] + "…" if len(raw_title) > 36 else raw_title
            # HTML 속성에 들어가는 문자열은 반드시 escape (쌍따옴표 등 특수문자 방지)
            title_attr = _html.escape(raw_title, quote=True)
            title_text = _html.escape(title_short)
            if v["thumbnail"] and v["url"]:
                thumb_block = (
                    f'<a href="{v["url"]}" target="_blank" rel="noopener noreferrer"'
                    f' style="display:block;">'
                    f'<img src="{v["thumbnail"]}" alt="{title_attr}"'
                    f' style="width:100%;border-radius:8px;display:block;'
                    f'aspect-ratio:16/9;object-fit:cover;">'
                    f'</a>'
                )
            elif v["thumbnail"]:
                thumb_block = (
                    f'<img src="{v["thumbnail"]}" alt="{title_attr}"'
                    f' style="width:100%;border-radius:8px;display:block;'
                    f'aspect-ratio:16/9;object-fit:cover;">'
                )
            else:
                thumb_block = (
                    '<div style="width:100%;aspect-ratio:16/9;'
                    'background:#E2E8F0;border-radius:8px;"></div>'
                )
            st.markdown(
                f'{thumb_block}'
                f'<div style="font-size:0.75rem;font-weight:600;color:#0F172A;'
                f'line-height:1.35;margin:6px 0 4px;min-height:2.5em;"'
                f' title="{title_attr}">{title_text}</div>'
                f'<div style="font-size:0.72rem;color:#64748B;">'
                f'👁 {int(v["view_count"]):,}&nbsp;&nbsp;'
                f'👍 {int(v["like_count"]):,}&nbsp;&nbsp;'
                f'💬 {int(v["comment_count"]):,}</div>',
                unsafe_allow_html=True,
            )


def _render_growth_card(channel_id: str) -> None:
    """광고주 추천 성장률 카드 렌더링. risk_ranking에 없으면 무시."""
    g = get_growth_score(channel_id)
    if g is None:
        return

    cs, tg, fe = g["content_safety"], g["traffic_growth"], g["fandom_engagement"]
    score = g["growth_score"]
    grade = g["grade"]

    score_color = (
        "#10B981" if score >= 0.65
        else "#F59E0B" if score >= 0.40
        else "#EF4444"
    )
    grade_colors = {"S": "#6366F1", "A": "#10B981", "B": "#3B82F6", "C": "#F59E0B", "D": "#EF4444"}
    grade_color = grade_colors.get(grade, "#94A3B8")

    with card("광고주 추천 성장률"):
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between;
                        align-items:flex-start; margin-bottom:16px; gap:12px; flex-wrap:wrap;">
                <div>
                    <div style="font-size:0.72rem; color:#64748B; margin-bottom:2px;">종합 성장 점수</div>
                    <div style="display:flex; align-items:baseline; gap:10px;">
                        <div style="font-size:2.4rem; font-weight:800; color:{score_color};
                                    line-height:1.05;">{score * 100:.1f}%</div>
                        <div style="font-size:1.1rem; font-weight:700;
                                    color:{grade_color}; line-height:1;">등급 {grade}</div>
                    </div>
                    <div style="font-size:0.8rem; color:#475569; margin-top:6px;">
                        추천 이유: <b>{g['reasons']}</b>
                    </div>
                </div>
                <div style="font-size:0.72rem; color:#94A3B8; align-self:flex-end;">
                    위험도(risk_ranking) 반전 기준
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        left_col, right_col = st.columns([1, 1])

        with left_col:
            axis_col = "".join([
                _cell("평판 안전성", f"{cs * 100:.1f}%", "민감 콘텐츠 낮을수록 높음"),
                _cell("트래픽 성장성", f"{tg * 100:.1f}%", "이탈·정체·변동성 낮을수록 높음"),
                _cell("팬덤 참여도", f"{fe * 100:.1f}%", "활성 시청자 비율 높을수록 높음"),
            ])
            st.html(f'<div style="display:flex; flex-direction:column; gap:8px;">{axis_col}</div>')

        with right_col:
            fig = go.Figure(go.Scatterpolar(
                r=[cs, tg, fe, cs],
                theta=["평판 안전성", "트래픽 성장성", "팬덤 참여도", "평판 안전성"],
                fill="toself",
                fillcolor="rgba(99,102,241,0.15)",
                line=dict(color="#6366F1", width=2),
                name="성장률",
            ))
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(range=[0, 1], tickvals=[0.25, 0.5, 0.75, 1.0],
                                    tickfont=dict(size=9, color="#94A3B8")),
                    angularaxis=dict(tickfont=dict(size=11, color="#334155")),
                ),
                paper_bgcolor="white",
                margin=dict(l=30, r=30, t=30, b=30),
                height=280,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)


def _clear_channel_search() -> None:
    st.session_state["channel_query"] = ""
    st.session_state["last_prediction"] = None
    st.session_state["csv_channel_id"] = None
    st.session_state["sql_export_data"] = None
    st.session_state["latest_video_selected"] = None
    st.query_params.clear()


# ---- 채널 클릭 진입 처리 (3/4 페이지에서 채널 클릭 시) ----
channel_id_param = st.query_params.get("channel_id", "")

if channel_id_param and st.session_state.get("csv_channel_id") != channel_id_param:
    st.session_state["csv_channel_id"] = channel_id_param
    st.session_state["channel_query"] = channel_id_param
    st.session_state["last_prediction"] = None

# ---- 검색 바 ----
search_col, btn_col = st.columns([6, 1])
with search_col:
    query = st.text_input(
        "search",
        placeholder="🔍   YouTube URL 또는 @채널핸들을 입력하세요",
        label_visibility="collapsed",
        key="channel_query",
    )

with btn_col:
    analyze_clicked = st.button(
        "분석하기", type="primary", use_container_width=True, key="analyze_btn"
    )
# with clear_col:
#     st.button(
#         "×",
#         use_container_width=True,
#         key="clear_channel_query_btn",
#         help="검색어와 결과 지우기",
#         on_click=_clear_channel_search,
#     )

# ---- 분석하기 버튼: 로딩 → all_channels → SQL export → (없으면) yt-dlp ----
if analyze_clicked and query.strip():
    import time as _time

    st.session_state["last_prediction"] = None
    st.session_state["csv_channel_id"] = None
    st.session_state["sql_export_data"] = None

    loading_slot = st.empty()
    t0 = _time.time()

    def _show_loading(label: str, frac: float) -> None:
        elapsed = _time.time() - t0
        loading_slot.markdown(
            f"""
            <style>
                @keyframes tb-spin {{
                    from {{ transform: rotate(0deg); }}
                    to {{ transform: rotate(360deg); }}
                }}
                .tb-loading-wrap {{
                    min-height: 220px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                }}
                .tb-loading-spinner {{
                    width: 58px;
                    height: 58px;
                    border-radius: 50%;
                    border: 6px solid #E2E8F0;
                    border-top-color: #6366F1;
                    animation: tb-spin 0.8s linear infinite;
                    margin: 0 auto 16px;
                }}
                .tb-loading-title {{
                    font-size: 0.98rem;
                    font-weight: 700;
                    color: #0F172A;
                }}
                .tb-loading-sub {{
                    margin-top: 6px;
                    font-size: 0.8rem;
                    color: #64748B;
                }}
            </style>
            <div class="tb-loading-wrap">
                <div>
                    <div class="tb-loading-spinner"></div>
                    <div class="tb-loading-title">{label}</div>
                    <div class="tb-loading-sub">진행률 {frac * 100:.0f}% · 경과 {elapsed:0.1f}s</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Step 1: all_channels에서 channel_id 탐색
    _show_loading("채널 정보 조회 중...", 0.1)
    channel_id_found, handle_found = find_channel_id_in_all_channels(query.strip())

    # Step 2: SQL export 조회
    _sql_stats = None
    if channel_id_found:
        _show_loading("데이터베이스 조회 중...", 0.5)
        _sql_stats = get_sql_export_stats(channel_id_found, handle_found)

    if _sql_stats:
        loading_slot.empty()
        st.session_state["sql_export_data"] = _sql_stats
        st.rerun()
    else:
        # Step 3: SQL에 없으면 yt-dlp 실시간 수집
        _fetch_query = channel_id_found if channel_id_found else query.strip()
        try:
            st.session_state["last_prediction"] = predict_for_query(
                _fetch_query, on_stage=_show_loading, force_fetch=True
            )
            total = _time.time() - t0
            loading_slot.empty()
            # st.success(f"완료 · 총 {total:0.1f}s")
        except Exception as e:
            loading_slot.empty()
            st.session_state["last_prediction"] = None
            st.error(f"예측 실패: {e}")


# ---- 결과 표시 ----
prediction = st.session_state.get("last_prediction")
csv_channel_id = st.session_state.get("csv_channel_id")
sql_export_data = st.session_state.get("sql_export_data")


def _avatar_html(thumbnail_url: str, fallback_emoji: str, channel_url: str = "") -> str:
    link_open  = f'<a href="{channel_url}" target="_blank" rel="noopener noreferrer" style="display:block;width:56px;height:56px;border-radius:50%;overflow:hidden;flex-shrink:0;cursor:pointer;">' if channel_url else ""
    link_close = "</a>" if channel_url else ""
    if thumbnail_url:
        inner = f'<img src="{thumbnail_url}" alt="" style="width:100%;height:100%;object-fit:cover;">'
        if channel_url:
            return f"{link_open}{inner}{link_close}"
        return f'<div style="width:56px;height:56px;border-radius:50%;overflow:hidden;flex-shrink:0;">{inner}</div>'
    fallback = (
        f'<div style="width:56px;height:56px;border-radius:50%;'
        f'background:linear-gradient(135deg,#A5B4FC,#6366F1);'
        f'display:flex;align-items:center;justify-content:center;'
        f'color:white;font-size:1.5rem;flex-shrink:0;">{fallback_emoji}</div>'
    )
    return f"{link_open}{fallback}{link_close}" if channel_url else fallback


def _cell(label: str, value: str, sub: str = "") -> str:
    sub_html = (
        f"<div style='font-size:0.7rem; color:#94A3B8; margin-top:2px;'>{sub}</div>"
        if sub and sub != "-" else ""
    )
    return f"""
    <div style="flex:1; min-width:130px; background:#F8FAFC;
                border:1px solid #E2E8F0; border-radius:10px; padding:12px 14px;">
        <div style="font-size:0.72rem; color:#64748B; margin-bottom:4px;">{label}</div>
        <div style="font-size:0.95rem; font-weight:700; color:#0F172A;">{value}</div>
        {sub_html}
    </div>"""


if prediction:
    # ---- 채널 데이터 준비 ----
    channel_id = prediction["channel_id"]
    meta = prediction.get("channel_meta") or {}

    ch = None
    if prediction["source"] == "DB" and channel_id:
        try:
            ch = get_channel_overview(channel_id)
        except Exception:
            ch = None

    if ch is None:
        sub = meta.get("subscriber_count")
        sub_str = f"{int(sub):,}명" if sub else "-"

        tv = meta.get("total_channel_views")
        tv_str = f"{int(tv):,}" if tv else "-"

        vid_cnt = meta.get("collected_video_count")
        vid_str = f"{int(vid_cnt):,}개" if vid_cnt else "-"

        last_d = meta.get("last_upload_date") or ""
        last_str = (
            f"{last_d[:4]}.{last_d[4:6]}.{last_d[6:]}"
            if len(last_d) == 8 else "-"
        )

        avg_v = meta.get("avg_view_5") or 0
        avg_v_str = f"{int(avg_v):,}" if avg_v else "-"

        trend = meta.get("recent_view_trend") or 0.0
        trend_str = f"{trend:+.0f}%" if trend else "-"

        eng = meta.get("engagement_rate") or 0.0
        eng_str = f"{eng * 100:.1f}%"

        sr = meta.get("shorts_ratio") or 0.0
        sr_str = f"{sr * 100:.0f}%"

        interval = meta.get("avg_upload_interval") or 0.0
        interval_str = f"{interval:.1f}일" if interval else "-"

        handle = meta.get("handle") or (f"({channel_id})" if channel_id else "-")

        ch = {
            "name": prediction["channel_name"],
            "handle": handle,
            "category": "알 수 없음",
            "category_emoji": "🎬",
            "subscriber_count": sub_str,
            "total_views": tv_str,
            "joined_at": "-",
            "last_upload_days": "-",
            "last_upload_date": last_str,
            "uploads_30d": vid_str,
            "avg_view": avg_v_str,
            "avg_view_delta": trend_str,
            "engagement_rate": eng_str,
            "shorts_ratio": sr_str,
            "avg_upload_interval": interval_str,
        }

    prob_color = (
        "#EF4444" if prediction["churn_prob"] >= 0.7
        else "#F59E0B" if prediction["churn_prob"] >= 0.4
        else "#10B981"
    )
    src_chip_kind = "positive" if prediction["source"] == "DB" else "warning"
    pred_chip_kind = "danger" if prediction["churn_pred"] else "positive"
    delta_color = (
        "#EF4444" if str(ch.get("avg_view_delta", "")).startswith("-")
        else "#10B981"
    )

    _thumb_pred = get_channel_thumbnail(channel_id)
    with card("채널 분석 결과"):
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between;
                        align-items:flex-start; margin-bottom:18px; gap:12px;">
                <div style="display:flex; align-items:center; gap:14px; flex:1; min-width:0;">
                    {_avatar_html(_thumb_pred, ch['category_emoji'], f"https://www.youtube.com/channel/{channel_id}")}
                    <div style="min-width:0;">
                        <div style="font-size:1.1rem; font-weight:700; color:#0F172A;
                                    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                            {ch['name']}
                        </div>
                        <div style="font-size:0.82rem; color:#64748B; margin-top:2px;">
                            {ch['handle']} · {ch['category']}
                        </div>
                        <div style="margin-top:8px; display:flex; gap:6px; flex-wrap:wrap;">
                            {chip(f"출처: {prediction['source']}", src_chip_kind)}
                            {chip(prediction['risk_level'], pred_chip_kind)}
                        </div>
                    </div>
                </div>
                <div style="text-align:right; flex-shrink:0; min-width:130px;">
                    <div style="font-size:0.72rem; color:#64748B; margin-bottom:2px;">이탈 확률</div>
                    <div style="font-size:2.4rem; font-weight:800; color:{prob_color};
                                line-height:1.05;">
                        {prediction['churn_prob'] * 100:.1f}%
                    </div>
                    <div style="font-size:0.9rem; font-weight:600; color:#0F172A; margin-top:4px;">
                        {prediction['prediction_label']}
                    </div>
                    <div style="font-size:0.7rem; color:#94A3B8; margin-top:2px;">임계 0.5 기준</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        row1 = "".join([
            _cell("구독자 수", ch["subscriber_count"]),
            _cell("총 조회수", ch["total_views"]),
            _cell("마지막 업로드", ch["last_upload_date"], ch["last_upload_days"]),
            _cell("수집 영상 수", ch["uploads_30d"]),
        ])

        avg_view_html = (
            f"{ch['avg_view']}"
            f"<span style='color:{delta_color}; font-size:0.78rem; margin-left:6px;'>"
            f"{ch['avg_view_delta']}</span>"
        )
        row2_cells = [
            f"""
            <div style="flex:1; min-width:130px; background:#FFFFFF;
                        border:1px solid #F1F5F9; border-radius:10px; padding:12px 14px;">
                <div style="font-size:0.72rem; color:#64748B; margin-bottom:4px;">평균 조회수 (최근 5개)</div>
                <div style="font-size:0.95rem; font-weight:700; color:#0F172A;">{avg_view_html}</div>
            </div>""",
            _cell("참여율", ch.get("engagement_rate", "-")).replace("#F8FAFC", "#FFFFFF").replace("#E2E8F0", "#F1F5F9"),
            _cell("Shorts 비율", ch.get("shorts_ratio", "-")).replace("#F8FAFC", "#FFFFFF").replace("#E2E8F0", "#F1F5F9"),
            _cell("평균 업로드 간격", ch.get("avg_upload_interval", "-")).replace("#F8FAFC", "#FFFFFF").replace("#E2E8F0", "#F1F5F9"),
        ]
        row2 = "".join(row2_cells)

        st.html(
            f'<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">{row1}</div>'
            f'<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:4px;">{row2}</div>'
        )

        st.markdown(
            "<div style='border-top:1px solid #E2E8F0; margin:14px 0 10px;'></div>"
            "<div style='font-size:0.88rem; font-weight:700; color:#0F172A; margin-bottom:6px;'>"
            "주요 이탈 원인 Top 3 (shap)</div>",
            unsafe_allow_html=True,
        )
        reasons_df = pd.DataFrame([
            {
                "피처": r["ko_name"],
                "실제값": f"{r['value']:,.4f}",
                "위험기여도(SHAP)": f"{r['shap']:+.4f}",
                "방향": f"→ {r['direction']}",
            }
            for r in prediction["top_reasons"]
        ])
        st.dataframe(reasons_df, hide_index=True, use_container_width=True)

    _render_growth_card(channel_id)

    entries = prediction.get("video_entries") or []
    if entries:
        with card("채널 활동 추이 분석"):
            _render_live_charts(entries)

    _latest = _entries_to_latest_videos(entries) if entries else []
    if _latest:
        with card("최근 영상"):
            _render_latest_videos(_latest)

    disclaimer_footer()

elif sql_export_data:
    # ---- SQL export 기반 채널 분석 결과 ----
    ch = sql_export_data
    grade = ch["grade"]
    risk_pct = ch["risk_pct"]
    prob_color = (
        "#EF4444" if risk_pct >= 70
        else "#F59E0B" if risk_pct >= 40
        else "#10B981"
    )

    with card("채널 분석 결과 (SQL 데이터 기준)"):
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between;
                        align-items:flex-start; margin-bottom:18px; gap:12px;">
                <div style="display:flex; align-items:center; gap:14px; flex:1; min-width:0;">
                    {_avatar_html(ch.get('thumbnail_url', ''), ch['category_emoji'])}
                    <div style="min-width:0;">
                        <div style="font-size:1.1rem; font-weight:700; color:#0F172A;
                                    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                            {ch['name']}
                        </div>
                        <div style="font-size:0.82rem; color:#64748B; margin-top:2px;">
                            {ch['handle']} · {ch['category']}
                        </div>
                        <div style="margin-top:8px; display:flex; gap:6px; flex-wrap:wrap;">
                            {chip("출처: SQL", "positive")}
                            {chip(f"등급: {grade}", "positive" if grade == "A" else "warning" if grade == "B" else "danger")}
                            {chip("이탈 예측: 있음" if ch['is_churned'] else "이탈 예측: 없음", "danger" if ch['is_churned'] else "positive")}
                        </div>
                    </div>
                </div>
                <div style="text-align:right; flex-shrink:0; min-width:130px;">
                    <div style="font-size:0.72rem; color:#64748B; margin-bottom:2px;">이탈 위험도</div>
                    <div style="font-size:2.4rem; font-weight:800; color:{prob_color};
                                line-height:1.05;">
                        {risk_pct}%
                    </div>
                    <div style="font-size:0.7rem; color:#94A3B8; margin-top:4px;">SQL export 기준</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        row1 = "".join([
            _cell("구독자 수", ch["subscriber_count"]),
            _cell("총 조회수", ch["total_views"]),
            _cell("마지막 업로드", ch["last_upload_date"], ch["last_upload_days"]),
            _cell("수집 영상 수", ch["uploads_30d"]),
        ])
        row2_cells = [
            _cell("평균 조회수", ch["avg_view"]).replace("#F8FAFC", "#FFFFFF").replace("#E2E8F0", "#F1F5F9"),
            _cell("참여율", ch["engagement_rate"]).replace("#F8FAFC", "#FFFFFF").replace("#E2E8F0", "#F1F5F9"),
            _cell("Shorts 비율", ch["shorts_ratio"]).replace("#F8FAFC", "#FFFFFF").replace("#E2E8F0", "#F1F5F9"),
            _cell("평균 업로드 간격", ch["avg_upload_interval"]).replace("#F8FAFC", "#FFFFFF").replace("#E2E8F0", "#F1F5F9"),
        ]
        row2 = "".join(row2_cells)

        st.html(
            f'<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">{row1}</div>'
            f'<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:4px;">{row2}</div>'
        )

        # 주요 SQL 지표
        st.markdown(
            "<div style='border-top:1px solid #E2E8F0; margin:14px 0 10px;'></div>"
            "<div style='font-size:0.88rem; font-weight:700; color:#0F172A; margin-bottom:6px;'>"
            "주요 지표 (SQL 기준)</div>",
            unsafe_allow_html=True,
        )
        try:
            reg_val = f"{float(ch['regularity_score']):.3f}" if ch['regularity_score'] not in ("-", "", None) else "-"
            av_val = f"{float(ch['active_viewer_score']):.3f}" if ch['active_viewer_score'] not in ("-", "", None) else "-"
            mg_val = f"{int(float(ch['max_gap_days']))}일" if ch['max_gap_days'] not in ("-", "", None) else "-"
        except (ValueError, TypeError):
            reg_val, av_val, mg_val = "-", "-", "-"

        row3 = "".join([
            _cell("규칙성 점수", reg_val),
            _cell("활성 시청자 점수", av_val),
            _cell("최대 업로드 공백", mg_val),
        ])
        st.html(f'<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:4px;">{row3}</div>')

    _render_growth_card(ch["channel_id"])

    try:
        with card("영상 지표 분석 (CSV 스냅샷 기준)"):
            _render_csv_charts(ch["channel_id"])
    except Exception:
        pass

    _latest_sql = _get_latest_videos_from_csv(ch["channel_id"])
    if _latest_sql:
        with card("최근 영상"):
            _render_latest_videos(_latest_sql)

    disclaimer_footer()

elif csv_channel_id:
    # ---- CSV 스냅샷 기반 채널 정보 표시 ----
    try:
        ch = get_channel_overview(csv_channel_id)
        pred = get_channel_prediction(csv_channel_id)
        reasons = get_channel_top_reasons(csv_channel_id, n=3)
    except Exception:
        st.warning("CSV 데이터에서 해당 채널을 찾을 수 없습니다.")
    else:
        risk_pct = pred["risk_pct"]
        grade = pred["grade"]
        prob_color = (
            "#EF4444" if risk_pct >= 70
            else "#F59E0B" if risk_pct >= 40
            else "#10B981"
        )
        delta_color = (
            "#EF4444" if str(ch.get("avg_view_delta", "")).startswith("-")
            else "#10B981"
        )

        _thumb_csv = get_channel_thumbnail(csv_channel_id)
        with card("채널 정보 (CSV 스냅샷 기준)"):
            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between;
                            align-items:flex-start; margin-bottom:18px; gap:12px;">
                    <div style="display:flex; align-items:center; gap:14px; flex:1; min-width:0;">
                        {_avatar_html(_thumb_csv, ch['category_emoji'], f"https://www.youtube.com/channel/{csv_channel_id}")}
                        <div style="min-width:0;">
                            <div style="font-size:1.1rem; font-weight:700; color:#0F172A;
                                        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                                {ch['name']}
                            </div>
                            <div style="font-size:0.82rem; color:#64748B; margin-top:2px;">
                                {ch['handle']} · {ch['category']}
                            </div>
                            <div style="margin-top:8px; display:flex; gap:6px; flex-wrap:wrap;">
                                {chip("출처: CSV", "positive")}
                                {chip(f"등급: {grade}", "positive" if grade == "A" else "warning" if grade == "B" else "danger")}
                            </div>
                        </div>
                    </div>
                    <div style="text-align:right; flex-shrink:0; min-width:130px;">
                        <div style="font-size:0.72rem; color:#64748B; margin-bottom:2px;">이탈 위험도</div>
                        <div style="font-size:2.4rem; font-weight:800; color:{prob_color};
                                    line-height:1.05;">
                            {risk_pct}%
                        </div>
                        <div style="font-size:0.7rem; color:#94A3B8; margin-top:4px;">스냅샷 기준 (2026-05-17)</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            row1 = "".join([
                _cell("구독자 수", ch["subscriber_count"]),
                _cell("총 조회수", ch["total_views"]),
                _cell("마지막 업로드", ch["last_upload_date"], ch["last_upload_days"]),
                _cell("최근 30일 업로드 (최대 50개)", ch["uploads_30d"]),
            ])

            avg_view_html = (
                f"{ch['avg_view']}"
                f"<span style='color:{delta_color}; font-size:0.78rem; margin-left:6px;'>"
                f"{ch['avg_view_delta']}</span>"
            )
            row2_cells = [
                f"""
                <div style="flex:1; min-width:130px; background:#FFFFFF;
                            border:1px solid #F1F5F9; border-radius:10px; padding:12px 14px;">
                    <div style="font-size:0.72rem; color:#64748B; margin-bottom:4px;">평균 조회수 (최근 5개)</div>
                    <div style="font-size:0.95rem; font-weight:700; color:#0F172A;">{avg_view_html}</div>
                </div>""",
                _cell("참여율", ch.get("engagement_rate", "-")).replace("#F8FAFC", "#FFFFFF").replace("#E2E8F0", "#F1F5F9"),
                _cell("Shorts 비율", ch.get("shorts_ratio", "-")).replace("#F8FAFC", "#FFFFFF").replace("#E2E8F0", "#F1F5F9"),
                _cell("평균 업로드 간격", ch.get("avg_upload_interval", "-")).replace("#F8FAFC", "#FFFFFF").replace("#E2E8F0", "#F1F5F9"),
            ]
            row2 = "".join(row2_cells)

            st.html(
                f'<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">{row1}</div>'
                f'<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:4px;">{row2}</div>'
            )

            st.markdown(
                "<div style='border-top:1px solid #E2E8F0; margin:14px 0 10px;'></div>"
                "<div style='font-size:0.88rem; font-weight:700; color:#0F172A; margin-bottom:6px;'>"
                "주요 이탈 원인 Top 3 (규칙 기반)</div>",
                unsafe_allow_html=True,
            )
            for i, r in enumerate(reasons, start=1):
                st.markdown(
                    f"<div style='font-size:0.85rem; color:#0F172A; padding:6px 0;'>"
                    f"<b>{i}.</b> {r['title']}"
                    f"<span style='color:#64748B; font-size:0.78rem; margin-left:8px;'>{r['desc']}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        _render_growth_card(csv_channel_id)

        try:
            with card("채널 활동 추이 분석"):
                _render_csv_charts(csv_channel_id)
        except Exception:
            pass

        _latest_csv = _get_latest_videos_from_csv(csv_channel_id)
        if _latest_csv:
            with card("최근 영상"):
                _render_latest_videos(_latest_csv)

        disclaimer_footer()

else:
    st.html(
        """
        <div style="
            min-height: 430px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
        ">
            <div>
                <div style="
                    width: 64px;
                    height: 64px;
                    border-radius: 18px;
                    background: #EEF2FF;
                    color: #6366F1;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 18px;
                    font-size: 1.9rem;
                ">🔍</div>
                <div style="
                    font-size: 1.18rem;
                    font-weight: 800;
                    color: #0F172A;
                    margin-bottom: 8px;
                ">채널을 조회해보세요</div>
                <div style="
                    font-size: 0.9rem;
                    color: #64748B;
                    line-height: 1.55;
                ">
                    YouTube URL 또는 @채널핸들을 입력하면<br>
                    활동 지속 가능성과 이탈 예측 결과를 확인할 수 있습니다.
                </div>
            </div>
        </div>
        """
    )
