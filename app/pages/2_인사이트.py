"""튜브어때 — 인사이트 페이지.

EDA 노트북(10_data_EDA.ipynb) 핵심 인사이트 4개를 광고주 관점으로 재구성.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as _pd
import plotly.graph_objects as go
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

from components import page_header, render_sidebar
from data_loader import (
    compute_channel_quadrant,
    compute_format_engagement,
    compute_shorts_longform_synergy,
    compute_upload_cycle_performance,
)
from styles import inject_global_css

st.set_page_config(
    page_title="인사이트 — 튜브어때",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
render_sidebar("insight")

page_header(
    "데이터 인사이트",
    "3,336개 채널 분석에서 추출한 광고 의사결정 가이드",
)

# ── 색상 상수 ──────────────────────────────────────────────────
PRIMARY = "#6366F1"
PRIMARY_DARK = "#4F46E5"
GRADE_A = "#10B981"
GRADE_B = "#F59E0B"
GRADE_C = "#EF4444"
TEXT_MUTED = "#94A3B8"
BORDER = "#D1D5DB"

CHART_LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="white",
    font_family="Pretendard, -apple-system, sans-serif",
    font_color="#0F172A",
    margin=dict(l=12, r=12, t=36, b=12),
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        font_size=11,
    ),
)


def _callout(text: str) -> None:
    st.markdown(
        f'<div class="tb-insight-callout">💡 {text}</div>',
        unsafe_allow_html=True,
    )


# ── 상단 행: Chart 4 (포맷별 참여율) + Chart 8 (쇼츠 vs 롱폼) ──
col_l, col_r = st.columns(2, gap="medium")

# ── Chart 4: 콘텐츠 포맷별 참여율 박스플롯 ──────────────────────
with col_l:
    with st.container(border=True):
        st.markdown("**콘텐츠 포맷별 참여율 분포**")
        _callout("숏폼 채널의 참여율 상향 평준화 — 바이럴·앱설치 캠페인에 최적")

        data = compute_format_engagement()
        colors = {
            "숏폼 중심": GRADE_C,
            "혼합형": TEXT_MUTED,
            "롱폼 중심": PRIMARY,
        }
        fill_colors = {
            "숏폼 중심": "rgba(239,68,68,0.2)",
            "혼합형": "rgba(148,163,184,0.2)",
            "롱폼 중심": "rgba(99,102,241,0.2)",
        }
        fig4 = go.Figure()
        for label in ["숏폼 중심", "혼합형", "롱폼 중심"]:
            fig4.add_trace(
                go.Box(
                    y=data[label],
                    name=label,
                    boxmean=True,
                    marker_color=colors[label],
                    line_color=colors[label],
                    fillcolor=fill_colors[label],
                    boxpoints=False,
                )
            )
        fig4.update_layout(
            **CHART_LAYOUT,
            yaxis=dict(
                title="평균 참여율 (%)",
                ticksuffix="%",
                range=[0, 15],
                gridcolor="#F1F5F9",
            ),
            xaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})

# ── Chart 8: 쇼츠 vs 롱폼 시너지 산점도 ───────────────────────
with col_r:
    with st.container(border=True):
        st.markdown("**쇼츠 vs 롱폼 조회수 시너지**")
        _callout("쇼츠 유입이 롱폼 충성 시청자로 전환 — 채널 유형 즉시 판별")

        syn = compute_shorts_longform_synergy()
        max_val = max(max(syn["shorts"]), max(syn["longform"]))
        diag = [100, max_val]

        fig8 = go.Figure()
        fig8.add_trace(
            go.Scatter(
                x=syn["shorts"],
                y=syn["longform"],
                mode="markers",
                marker=dict(color=PRIMARY, opacity=0.35, size=5),
                name="채널",
                hovertemplate="쇼츠: %{x:,.0f}<br>롱폼: %{y:,.0f}<extra></extra>",
            )
        )
        fig8.add_trace(
            go.Scatter(
                x=diag,
                y=diag,
                mode="lines",
                line=dict(color=GRADE_C, dash="dot", width=1.5),
                name="균형선 (Y=X)",
                hoverinfo="skip",
            )
        )
        fig8.add_annotation(
            x=0.08, y=0.92,
            xref="paper", yref="paper",
            text="▲ 롱폼 우세 채널",
            showarrow=False,
            font=dict(size=10, color=GRADE_A),
            align="left",
        )
        fig8.add_annotation(
            x=0.92, y=0.08,
            xref="paper", yref="paper",
            text="쇼츠 편향 채널 ▶",
            showarrow=False,
            font=dict(size=10, color=GRADE_C),
            align="right",
        )
        fig8.update_layout(
            **CHART_LAYOUT,
            xaxis=dict(
                title="평균 쇼츠 조회수",
                type="log",
                gridcolor="#F1F5F9",
                tickformat=".2s",
            ),
            yaxis=dict(
                title="평균 롱폼 조회수",
                type="log",
                gridcolor="#F1F5F9",
                tickformat=".2s",
            ),
        )
        st.plotly_chart(fig8, use_container_width=True, config={"displayModeBar": False})

# ── 하단 행: Chart 11 (4분면) + Chart 13 (업로드 주기) ──────────
col_l2, col_r2 = st.columns(2, gap="medium")

# ── Chart 11: 채널 성과·리스크 4분면 ───────────────────────────
with col_l2:
    with st.container(border=True):
        st.markdown("**채널 성과·리스크 4분면 진단**")
        _callout("업로드 성실도 × 팬덤 결집력 — 리스크 정량화로 단가 협상 근거 확보")

        quad = compute_channel_quadrant()
        quad_colors = {
            "①고위험 (마니아 소통형)": GRADE_B,
            "②중위험 (투자금지)": GRADE_C,
            "③저위험 (대중적 메가뷰)": "#60A5FA",
            "④안전 (Sweet Spot)": GRADE_A,
        }
        fig11 = go.Figure()

        _df11 = _pd.DataFrame({
            "x": quad["x"],
            "y": quad["y"],
            "q": quad["quadrant"],
            "t": quad["titles"],
        })

        for q_label, color in quad_colors.items():
            sub = _df11[_df11["q"] == q_label]
            fig11.add_trace(
                go.Scatter(
                    x=sub["x"],
                    y=sub["y"],
                    mode="markers",
                    name=q_label,
                    marker=dict(color=color, opacity=0.5, size=5),
                    hovertemplate="%{text}<br>최대공백: %{x:.0f}일<br>참여율: %{y:.2f}%<extra></extra>",
                    text=sub["t"],
                )
            )

        fig11.add_vline(
            x=quad["gap_threshold"],
            line_dash="dash",
            line_color=TEXT_MUTED,
            line_width=1,
            annotation_text="365일",
            annotation_position="top right",
            annotation_font_size=10,
        )
        fig11.add_hline(
            y=quad["eng_median"],
            line_dash="dash",
            line_color=TEXT_MUTED,
            line_width=1,
            annotation_text=f"중앙값 {quad['eng_median']:.2f}%",
            annotation_position="bottom right",
            annotation_font_size=10,
        )
        fig11.update_layout(
            **CHART_LAYOUT,
            xaxis=dict(
                title="최대 공백 기간 (일)",
                type="log",
                gridcolor="#F1F5F9",
            ),
            yaxis=dict(
                title="평균 참여율 (%)",
                ticksuffix="%",
                gridcolor="#F1F5F9",
                range=[0, quad["eng_median"] * 6],
            ),
        )
        st.plotly_chart(fig11, use_container_width=True, config={"displayModeBar": False})

# ── Chart 13: 업로드 주기별 중앙 조회수 수평 막대 ───────────────
with col_r2:
    with st.container(border=True):
        st.markdown("**업로드 주기 그룹별 조회수 성과**")
        _callout("팬덤/장인형 채널의 중앙 조회수가 메가 부스팅형의 약 2배 — 안전 자산")

        cyc = compute_upload_cycle_performance()
        bar_colors = [PRIMARY, "#818CF8", "#A5B4FC"]

        fig13 = go.Figure(
            go.Bar(
                x=cyc["medians"],
                y=cyc["groups"],
                orientation="h",
                marker_color=bar_colors,
                text=[f"{v:,.0f}회  (n={c})" for v, c in zip(cyc["medians"], cyc["counts"])],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="%{y}<br>중앙 조회수: %{x:,.0f}<extra></extra>",
            )
        )
        fig13.update_layout(
            **{**CHART_LAYOUT, "showlegend": False, "margin": dict(l=12, r=90, t=36, b=12)},
            xaxis=dict(
                title="중앙 평균 조회수 (회)",
                tickformat=",",
                gridcolor="#F1F5F9",
            ),
            yaxis=dict(showgrid=False, autorange="reversed"),
        )
        st.plotly_chart(fig13, use_container_width=True, config={"displayModeBar": False})
