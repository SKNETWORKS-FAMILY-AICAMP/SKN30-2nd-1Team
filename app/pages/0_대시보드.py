"""튜브어때 — 대시보드 (데이터 현황)."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.append(str(Path(__file__).parent.parent))

from components import (
    card,
    disclaimer_footer,
    kpi_card,
    page_header,
    render_sidebar,
)
from data_loader import (
    compute_grade_distribution,
    compute_kpis,
    compute_risk_signals,
    compute_subscriber_band_churn,
    compute_top_risky,
)
from styles import DATA_SNAPSHOT_DATE, PRIMARY, inject_global_css

st.set_page_config(
    page_title="튜브어때 — 대시보드",
    page_icon="🛟",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
render_sidebar("dashboard")

page_header(
    title="데이터 현황",
    subtitle="튜브어때가 분석한 유튜브 채널 현황입니다.",
    right=f"{DATA_SNAPSHOT_DATE} 기준",
)

# ---- KPI ----
dashboard_kpi = compute_kpis()
risk_distribution = compute_grade_distribution()
band_data = compute_subscriber_band_churn()
top_risky_channels = compute_top_risky(5)
risk_signals = compute_risk_signals()

kpi_cols = st.columns(4, gap="medium")
for col, k in zip(kpi_cols, dashboard_kpi):
    with col:
        kpi_card(k["label"], k["value"], k["unit"], k["delta"], k["tone"])

st.write("")

# ---- 도넛 + 라인 ----
left, right = st.columns([1, 1.4], gap="medium")

with left:
    with card("이탈 위험도 분포", "180일 이상 미업로드 = 이탈"):
        labels = [r["label"] for r in risk_distribution]
        counts = [r["count"] for r in risk_distribution]
        colors = [r["color"] for r in risk_distribution]
        total = sum(counts)

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=counts,
                    hole=0.7,
                    marker=dict(colors=colors, line=dict(color="white", width=2)),
                    textinfo="none",
                    hovertemplate="%{label}<br>%{value:,}개 (%{percent})<extra></extra>",
                    sort=False,
                )
            ]
        )
        fig.update_layout(
            height=270,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            paper_bgcolor="white",
            plot_bgcolor="white",
            annotations=[
                dict(text="전체 채널", x=0.5, y=0.58, font_size=12, font_color="#94A3B8", showarrow=False),
                dict(text=f"{total:,}", x=0.5, y=0.42, font_size=22, font_color="#0F172A", font_family="Pretendard", showarrow=False),
            ],
        )
        chart_col, legend_col = st.columns([1, 1])
        with chart_col:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with legend_col:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            for r in risk_distribution:
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; gap:10px; padding:8px 0;">
                        <span style="width:10px; height:10px; border-radius:50%; background:{r['color']};"></span>
                        <span style="font-size:0.86rem; color:#0F172A; flex-grow:1;">{r['label']}</span>
                        <span style="font-size:0.86rem; color:#64748B;">{int(r['ratio']*100)}% ({r['count']:,})</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

with right:
    with card("구독자 구간별 안심 채널 비율", "최근 30일 이내 업로드 기준"):
        xs = band_data["labels"]
        ys = band_data["ratios"]
        counts = band_data["counts"]
        totals = band_data["totals"]
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=xs,
                y=ys,
                marker=dict(color=PRIMARY, line=dict(width=0)),
                text=[f"{v:.1f}%" for v in ys],
                textposition="outside",
                textfont=dict(size=12, color="#0F172A", family="Pretendard"),
                customdata=list(zip(counts, totals)),
                hovertemplate=(
                    "%{x}<br>안심 %{customdata[0]:,}건 / 전체 %{customdata[1]:,}건"
                    "<extra></extra>"
                ),
            )
        )
        y_max = max(ys) if ys else 0
        fig.update_layout(
            height=270,
            margin=dict(l=10, r=40, t=20, b=10),
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            bargap=0.45,
            xaxis=dict(showgrid=False, color="#475569", tickfont=dict(size=11)),
            yaxis=dict(
                showgrid=True, gridcolor="#F1F5F9",
                color="#94A3B8", tickfont=dict(size=10),
                range=[0, max(y_max * 1.25, 5)], ticksuffix="%",
            ),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.write("")

# ---- 하단 (TOP 5 + 위험 신호) ----
b_left, b_right = st.columns([1, 1.4], gap="medium")

with b_left:
    with card("즉시 주의 채널 TOP 5", "장기 미업로드 + 업로드 빈도 감소"):
        rows = "".join(
            f"""
            <tr>
                <td class="rank">{c['rank']}</td>
                <td>{c['name']}</td>
                <td style="text-align:right;" class="delta-up">{c['days']:,}일 전</td>
            </tr>
            """
            for c in top_risky_channels
        )
        st.markdown(
            f"""
            <table class="tb-table">
                <tbody>{rows}</tbody>
            </table>
            <div style="margin-top:10px; text-align:right;">
                <a href="#" style="font-size:0.78rem; color:#6366F1; text-decoration:none;">더 보기 →</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

with b_right:
    with card("주요 위험 신호", "전체 채널 대비 비율"):
        signal_html = "".join(
            f"""
            <div class="tb-signal-row">
                <div class="tb-signal-icon">{sig['icon']}</div>
                <div class="tb-signal-label">{sig['label']}</div>
                <div class="tb-signal-bar"><div style="width:{sig['value']}%;"></div></div>
                <div class="tb-signal-value">{sig['value']}%</div>
            </div>
            """
            for sig in risk_signals
        )
        st.markdown(signal_html, unsafe_allow_html=True)

disclaimer_footer()
