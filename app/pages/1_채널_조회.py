"""튜브어때 — 채널 조회 + 이탈 예측 (핵심 페이지)."""

from __future__ import annotations

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
from dummy_data import (
    ENGAGEMENT_TREND,
    PREDICTION_RESULT,
    RISK_SIGNAL_SUMMARY,
    SAMPLE_CHANNEL,
    SENTIMENT_TREND,
    SHAP_FACTORS,
    TOP_REASONS,
    UPLOAD_TREND,
    VIEW_TREND,
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

# ---- 검색 바 ----
search_col, btn_col = st.columns([6, 1])
with search_col:
    st.text_input(
        "search",
        placeholder="🔍   Channel ID 또는 YouTube URL 입력",
        label_visibility="collapsed",
        key="channel_query",
    )
with btn_col:
    st.button("분석하기", type="primary", use_container_width=True)

st.write("")

# ---- 좌(채널 정보) / 우(예측 결과) ----
left, right = st.columns([1, 1.2], gap="medium")

with left:
    with card("채널 기본 정보"):
        ch = SAMPLE_CHANNEL
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:14px; margin-bottom:18px;">
                <div style="width:64px; height:64px; border-radius:50%;
                            background: linear-gradient(135deg,#A5B4FC,#6366F1);
                            display:flex; align-items:center; justify-content:center;
                            color:white; font-size:1.6rem;">🎮</div>
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

        metric_pairs = [
            ("구독자 수", ch["subscriber_count"]),
            ("총 조회수", ch["total_views"]),
            ("가입일", ch["joined_at"]),
            ("최근 업로드", f"{ch['last_upload_days']}<div style='font-size:0.72rem; color:#94A3B8;'>{ch['last_upload_date']}</div>"),
            ("최근 30일 업로드 수", ch["uploads_30d"]),
            ("평균 조회수 (최근 30일)", f"{ch['avg_view']}<span style='color:#EF4444; font-size:0.78rem; margin-left:6px;'>{ch['avg_view_delta']}</span>"),
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
    risk_pct = PREDICTION_RESULT["risk_pct"]
    grade = PREDICTION_RESULT["grade"]

    with card():
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; justify-content:space-between;">
                <div class="tb-card-title">이탈 예측 결과</div>
                <div>{chip("위험", "danger")}</div>
            </div>
            <div style="display:flex; align-items:center; gap:24px; margin-top:18px;
                        background: linear-gradient(180deg, #FEF2F2 0%, #FFFFFF 80%);
                        border-radius: 12px; padding: 18px 18px;">
                <div style="position:relative;">
                    <div style="width:108px; height:108px; border-radius:50%;
                                background:{GRADE_C};
                                box-shadow: 0 8px 22px rgba(239,68,68,0.30);
                                display:flex; align-items:center; justify-content:center;
                                color:white; font-size:3rem; font-weight:800;">{grade}</div>
                    <div style="font-size:0.7rem; color:#64748B; text-align:center; margin-top:6px;">등급</div>
                </div>
                <div style="flex-grow:1;">
                    <div style="font-size:0.82rem; color:#64748B;">이탈 위험도</div>
                    <div style="font-size:2.4rem; font-weight:800; color:#EF4444; letter-spacing:-1px; line-height:1;">{risk_pct}<span style="font-size:1.2rem;">%</span></div>
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

    with card("예상 사유 TOP 3"):
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
            for i, r in enumerate(TOP_REASONS, 1)
        )
        st.markdown(reasons_html, unsafe_allow_html=True)

st.write("")

# ---- 요약 지표 ----
with card("요약 지표", "최근 6개월"):
    sum_cols = st.columns(4, gap="medium")
    tone_color = {"danger": "#EF4444", "warning": "#F59E0B", "positive": "#10B981"}
    for col, m in zip(sum_cols, PREDICTION_RESULT["summary"]):
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

# ---- 상세 분석 (구 위험 분석 상세 페이지에서 통합) ----
st.markdown("<div class='tb-page-title' style='font-size:1.2rem;'>상세 분석</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='tb-page-sub'>신호별 추이와 위험 요인 기여도를 확인합니다.</div>",
    unsafe_allow_html=True,
)


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


def _line_chart(xs, ys, color, ysuffix="", height=200, fill=True):
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


tabs = st.tabs(["종합 분석", "업로드 분석", "조회수 분석", "댓글 감성 분석", "참여율 분석"])

with tabs[0]:
    c1, c2 = st.columns(2, gap="medium")

    with c1:
        with card("업로드 추이", "업로드 횟수 (월별)"):
            xs = [p[0] for p in UPLOAD_TREND]
            ys = [p[1] for p in UPLOAD_TREND]
            bar = go.Figure(
                data=[
                    go.Bar(
                        x=xs, y=ys,
                        marker=dict(color="#C7D2FE", line=dict(color=PRIMARY, width=0)),
                        text=ys, textposition="outside",
                        textfont=dict(color="#475569", size=11),
                    )
                ]
            )
            bar.update_layout(
                height=200,
                margin=dict(l=8, r=8, t=18, b=8),
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white",
                xaxis=dict(showgrid=False, color="#94A3B8", tickfont=dict(size=10)),
                yaxis=dict(showgrid=True, gridcolor="#F1F5F9", color="#94A3B8", tickfont=dict(size=10)),
            )
            st.plotly_chart(bar, use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                f"<div style='text-align:right; font-size:0.78rem;'>{chip('-83%', 'danger')}</div>",
                unsafe_allow_html=True,
            )

    with c2:
        with card("조회수 추이", "평균 조회수 (월별)"):
            xs = [p[0] for p in VIEW_TREND]
            ys = [p[1] for p in VIEW_TREND]
            st.plotly_chart(
                _line_chart(xs, ys, GRADE_C, ysuffix="", height=200),
                use_container_width=True, config={"displayModeBar": False},
            )
            st.markdown(
                f"<div style='text-align:right; font-size:0.78rem;'>{chip('-61%', 'danger')}</div>",
                unsafe_allow_html=True,
            )

    c3, c4 = st.columns(2, gap="medium")

    with c3:
        with card("댓글 감성 변화", "긍정/부정 비율"):
            pos_xs = [p[0] for p in SENTIMENT_TREND["positive"]]
            pos_ys = [p[1] for p in SENTIMENT_TREND["positive"]]
            neg_ys = [p[1] for p in SENTIMENT_TREND["negative"]]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=pos_xs, y=pos_ys, mode="lines+markers", name="긍정",
                                     line=dict(color=GRADE_A, width=2.4, shape="spline"),
                                     marker=dict(size=5, color=GRADE_A)))
            fig.add_trace(go.Scatter(x=pos_xs, y=neg_ys, mode="lines+markers", name="부정",
                                     line=dict(color=GRADE_C, width=2.4, shape="spline", dash="dot"),
                                     marker=dict(size=5, color=GRADE_C)))
            fig.update_layout(
                height=200,
                margin=dict(l=8, r=8, t=8, b=8),
                plot_bgcolor="white",
                paper_bgcolor="white",
                legend=dict(orientation="h", x=0, y=1.18, font=dict(size=10, color="#64748B")),
                xaxis=dict(showgrid=False, color="#94A3B8", tickfont=dict(size=10)),
                yaxis=dict(showgrid=True, gridcolor="#F1F5F9", color="#94A3B8",
                           tickfont=dict(size=10), ticksuffix="%", range=[0, 80]),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c4:
        with card("참여율 추이", "좋아요+댓글 / 조회수 비율"):
            xs = [p[0] for p in ENGAGEMENT_TREND]
            ys = [p[1] for p in ENGAGEMENT_TREND]
            st.plotly_chart(
                _line_chart(xs, ys, "#A855F7", ysuffix="%", height=200),
                use_container_width=True, config={"displayModeBar": False},
            )
            st.markdown(
                f"<div style='text-align:right; font-size:0.78rem;'>{chip('5% → 2.1%', 'warning')}</div>",
                unsafe_allow_html=True,
            )

for ph_tab in tabs[1:]:
    with ph_tab:
        st.info("이 탭은 디자인 시안에서는 종합 분석 탭과 동일한 시각화 패턴을 사용합니다. 실제 구현 시 세부 차트로 확장됩니다.")

st.write("")

# ---- 위험 신호 요약 + SHAP ----
sl, sr = st.columns([1.2, 1], gap="medium")

with sl:
    with card("위험 신호 요약"):
        cards_cols = st.columns(4, gap="small")
        tone_to_chip = {"danger": "danger", "warning": "warning"}
        tone_to_color = {"danger": GRADE_C, "warning": GRADE_B}
        for col, s in zip(cards_cols, RISK_SIGNAL_SUMMARY):
            color = tone_to_color.get(s["tone"], "#64748B")
            with col:
                st.markdown(
                    f"""
                    <div style="background:#FFFFFF; border:1px solid #F1F5F9; border-radius:12px;
                                padding:14px 14px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="width:8px; height:8px; border-radius:50%; background:{color};"></span>
                            <div style="font-size:0.85rem; font-weight:600; color:#0F172A;">{s['label']}</div>
                        </div>
                        <div style="font-size:0.74rem; color:#64748B; margin-top:8px; line-height:1.4;">
                            {s['desc']}
                        </div>
                        <div style="margin-top:10px;">{chip(f"위험도 {s['level']}", tone_to_chip.get(s['tone'], 'neutral'))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

with sr:
    with card("SHAP 주요 영향 요인", "위험도 증가 기여 (+)"):
        labels = [s["label"] for s in SHAP_FACTORS]
        values = [s["value"] for s in SHAP_FACTORS]
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
            height=220,
            margin=dict(l=8, r=40, t=8, b=8),
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(showgrid=True, gridcolor="#F1F5F9", color="#94A3B8",
                       tickfont=dict(size=10), range=[0, 0.55]),
            yaxis=dict(showgrid=False, color="#0F172A", tickfont=dict(size=11)),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

disclaimer_footer()
