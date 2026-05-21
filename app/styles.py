"""튜브어때 Streamlit 대시보드 - 전역 스타일.

PRD §13 / designer SKILL §UX 원칙에 맞춰 Stripe·Linear 풍 SaaS 톤을 구현한다.
"""

import streamlit as st

PRIMARY = "#6366F1"
PRIMARY_DARK = "#4F46E5"
GRADE_A = "#10B981"
GRADE_B = "#F59E0B"
GRADE_C = "#EF4444"

BG_APP = "#F7F8FA"
BG_CARD = "#FFFFFF"
BORDER = "#D1D5DB"
TEXT_PRIMARY = "#0F172A"
TEXT_SECONDARY = "#64748B"
TEXT_MUTED = "#94A3B8"

SIDEBAR_BG = "#0F172A"
SIDEBAR_ACTIVE = "#1E293B"
SIDEBAR_TEXT = "#CBD5E1"

DATA_SNAPSHOT_DATE = "2026-05-17"


def inject_global_css() -> None:
    st.markdown(
        f"""
        <style>
        /* ---- 폰트 ---- */
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

        html, body, [class*="css"], .stApp {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: {TEXT_PRIMARY};
            -webkit-font-smoothing: antialiased;
        }}

        /* ---- Streamlit 기본 UI 정리 (헤더는 살려둬야 사이드바 토글이 보임) ---- */
        #MainMenu {{visibility: hidden;}}
        [data-testid="stToolbar"] {{visibility: hidden;}}
        [data-testid="stDecoration"] {{display: none;}}
        footer {{visibility: hidden;}}

        header[data-testid="stHeader"] {{
            background: transparent;
            height: 2.75rem;
            pointer-events: none;
        }}
        /* 사이드바 토글 버튼만 다시 노출 */
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stExpandSidebarButton"],
        [data-testid="stSidebarCollapsedControl"] {{
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            visibility: visible !important;
            opacity: 1 !important;
            z-index: 999999;
            pointer-events: auto !important;
        }}
        [data-testid="stExpandSidebarButton"],
        [data-testid="stSidebarCollapsedControl"] {{
            position: fixed !important;
            top: 0.65rem !important;
            left: 0.65rem !important;
            width: 2.25rem !important;
            height: 2.25rem !important;
            background: #FFFFFF !important;
            border: 1px solid {BORDER} !important;
            border-radius: 8px !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12) !important;
            color: {TEXT_PRIMARY} !important;
        }}
        [data-testid="stExpandSidebarButton"] svg {{
            color: {TEXT_PRIMARY} !important;
            fill: currentColor !important;
        }}
        [data-testid="stExpandSidebarButton"] > * {{
            opacity: 0 !important;
        }}
        [data-testid="stExpandSidebarButton"]::before,
        [data-testid="stExpandSidebarButton"]::after {{
            content: "";
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0.48rem;
            height: 0.48rem;
            border-top: 2px solid {TEXT_PRIMARY};
            border-right: 2px solid {TEXT_PRIMARY};
        }}
        [data-testid="stExpandSidebarButton"]::before {{
            transform: translate(-80%, -50%) rotate(45deg);
        }}
        [data-testid="stExpandSidebarButton"]::after {{
            transform: translate(-25%, -50%) rotate(45deg);
        }}

        .stApp {{
            background: {BG_APP};
        }}

        .block-container {{
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1480px;
        }}

        /* ---- 사이드바 ---- */
        section[data-testid="stSidebar"] {{
            background: {SIDEBAR_BG} !important;
            border-right: 1px solid #1E293B;
        }}
        /* Streamlit 자동 페이지 네비게이션 숨김 (우리가 render_sidebar에서 직접 그림) */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"],
        section[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] {{
            display: none !important;
        }}
        .st-emotion-cache-1echtaq {{
            padding-top: 0 !important;
        }}
        /* 데이터 스냅샷을 사이드바 맨 아래에 absolute로 고정 — 기준점 설정 */
        section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
            position: relative !important;
            min-height: 100vh;
        }}
        section[data-testid="stSidebar"] > div {{
            background: {SIDEBAR_BG} !important;
        }}
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] div,
        section[data-testid="stSidebar"] a {{
            color: {SIDEBAR_TEXT};
        }}
        section[data-testid="stSidebar"] .stPageLink {{
            border-radius: 10px;
            margin: 2px 6px;
        }}
        section[data-testid="stSidebar"] .stPageLink a {{
            padding: 10px 14px !important;
            border-radius: 10px;
            font-weight: 500;
            color: {SIDEBAR_TEXT} !important;
        }}
        section[data-testid="stSidebar"] .stPageLink a:hover {{
            background: {SIDEBAR_ACTIVE};
            color: #FFFFFF !important;
        }}
        section[data-testid="stSidebar"] hr {{
            border-color: #1E293B;
        }}
        /* 사이드바 내 일반 버튼 (QR 공유 등) */
        section[data-testid="stSidebar"] [data-testid="stButton"] > button {{
            background: rgba(255, 255, 255, 0.06) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            color: #E2E8F0 !important;
            font-weight: 500;
            border-radius: 10px;
            margin: 4px 6px 0;
            width: calc(100% - 12px);
        }}
        section[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {{
            background: rgba(99, 102, 241, 0.20) !important;
            border-color: rgba(99, 102, 241, 0.45) !important;
            color: #FFFFFF !important;
        }}

        /* ---- 카드 (components.card() 매핑)
           Streamlit 1.50부터 st.container(border=True)에 별도 testid가 없어
           components.py의 card()가 key="tb-card-N"를 박아주고, Streamlit이
           자동 생성하는 st-key-tb-card-N class를 selector로 사용한다. ---- */
        div[data-testid="stVerticalBlock"][class*="st-key-tb-card-"] {{
            background: {BG_CARD} !important;
            background-color: {BG_CARD} !important;
            border: 1px solid {BORDER} !important;
            border-radius: 16px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.03) !important;
            padding: 22px 24px !important;
        }}
        /* 카드 안의 중첩 카드는 스타일 초기화 */
        div[data-testid="stVerticalBlock"][class*="st-key-tb-card-"]
            div[data-testid="stVerticalBlock"][class*="st-key-tb-card-"] {{
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
        }}
        /* 기존 markdown 기반 카드(하위 호환) */
        .tb-card {{
            background: {BG_CARD};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 22px 24px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.03);
        }}
        .tb-card-tight {{
            padding: 18px 20px;
        }}
        .tb-card-title {{
            font-size: 0.95rem;
            font-weight: 600;
            color: {TEXT_PRIMARY};
            margin-bottom: 4px;
        }}
        .tb-card-sub {{
            font-size: 0.8rem;
            color: {TEXT_SECONDARY};
            margin-bottom: 16px;
        }}
        /* title + subtitle 한 줄 양끝 정렬 */
        .tb-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 12px;
            margin-bottom: 14px;
        }}
        .tb-card-header .tb-card-title,
        .tb-card-header .tb-card-sub {{
            margin-bottom: 0;
        }}
        .tb-card-header .tb-card-sub {{
            text-align: right;
            flex-shrink: 0;
        }}

        /* ---- KPI ---- */
        .tb-kpi-label {{
            font-size: 0.8rem;
            color: {TEXT_SECONDARY};
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .tb-kpi-value {{
            font-size: 1.85rem;
            font-weight: 700;
            color: {TEXT_PRIMARY};
            letter-spacing: -0.5px;
            line-height: 1.1;
        }}
        .tb-kpi-delta {{
            font-size: 0.78rem;
            margin-top: 8px;
            color: {TEXT_MUTED};
        }}
        .tb-kpi-delta.positive {{ color: {GRADE_A}; }}
        .tb-kpi-delta.warning  {{ color: {GRADE_B}; }}
        .tb-kpi-delta.danger   {{ color: {GRADE_C}; }}

        /* ---- 등급 배지 ---- */
        .tb-grade {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            font-weight: 700;
            font-size: 0.85rem;
            color: white;
        }}
        .tb-grade-A {{ background: {GRADE_A}; }}
        .tb-grade-B {{ background: {GRADE_B}; }}
        .tb-grade-C {{ background: {GRADE_C}; }}

        .tb-chip {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
        }}
        .tb-chip-danger  {{ background: #FEE2E2; color: {GRADE_C}; }}
        .tb-chip-warning {{ background: #FEF3C7; color: #B45309; }}
        .tb-chip-safe    {{ background: #D1FAE5; color: #047857; }}
        .tb-chip-neutral {{ background: #EEF2FF; color: {PRIMARY_DARK}; }}

        /* ---- 페이지 헤더 ---- */
        .tb-page-title {{
            font-size: 1.55rem;
            font-weight: 700;
            color: {TEXT_PRIMARY};
            letter-spacing: -0.4px;
            margin-bottom: 4px;
        }}
        .tb-page-sub {{
            font-size: 0.88rem;
            color: {TEXT_SECONDARY};
            margin-bottom: 22px;
        }}

        /* ---- 테이블 ---- */
        .tb-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.86rem;
        }}
        .tb-table th {{
            text-align: left;
            font-weight: 500;
            color: {TEXT_MUTED};
            padding: 10px 4px;
            border-bottom: 1px solid {BORDER};
        }}
        .tb-table td {{
            padding: 12px 4px;
            border-bottom: 1px solid #F1F5F9;
            color: {TEXT_PRIMARY};
        }}
        .tb-table tr:last-child td {{ border-bottom: none; }}
        .tb-table .rank {{
            color: {TEXT_MUTED};
            font-variant-numeric: tabular-nums;
            width: 30px;
        }}
        .tb-table .delta-up   {{ color: {GRADE_C}; font-weight: 600; }}
        .tb-table .delta-down {{ color: {GRADE_A}; font-weight: 600; }}

        /* ---- 신호 막대 ---- */
        .tb-signal-row {{
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 8px 0;
        }}
        .tb-signal-icon {{
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #EEF2FF;
            color: {PRIMARY_DARK};
            font-size: 0.95rem;
            flex-shrink: 0;
        }}
        .tb-signal-label {{
            font-size: 0.86rem;
            color: {TEXT_PRIMARY};
            flex-grow: 1;
        }}
        .tb-signal-bar {{
            flex-basis: 160px;
            height: 6px;
            background: #F1F5F9;
            border-radius: 999px;
            overflow: hidden;
        }}
        .tb-signal-bar > div {{
            height: 100%;
            background: {PRIMARY};
            border-radius: 999px;
        }}
        .tb-signal-value {{
            font-size: 0.82rem;
            font-weight: 600;
            color: {TEXT_PRIMARY};
            width: 40px;
            text-align: right;
        }}

        /* ---- 위험도 게이지 ---- */
        .tb-gauge-wrap {{
            margin-top: 16px;
        }}
        .tb-gauge-track {{
            position: relative;
            height: 10px;
            border-radius: 999px;
            background: linear-gradient(to right, {GRADE_A} 0%, {GRADE_A} 33%, {GRADE_B} 33%, {GRADE_B} 66%, {GRADE_C} 66%, {GRADE_C} 100%);
        }}
        .tb-gauge-marker {{
            position: absolute;
            top: -4px;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: white;
            border: 3px solid {TEXT_PRIMARY};
            transform: translateX(-50%);
        }}
        .tb-gauge-scale {{
            display: flex;
            justify-content: space-between;
            font-size: 0.7rem;
            color: {TEXT_MUTED};
            margin-top: 6px;
        }}

        /* ---- 사유 리스트 ---- */
        .tb-reason {{
            display: flex;
            gap: 14px;
            padding: 12px 0;
            border-bottom: 1px solid #F1F5F9;
        }}
        .tb-reason:last-child {{ border-bottom: none; }}
        .tb-reason-num {{
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: {PRIMARY};
            color: white;
            font-size: 0.78rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            margin-top: 1px;
        }}
        .tb-reason-title {{
            font-size: 0.92rem;
            font-weight: 600;
            color: {TEXT_PRIMARY};
            margin-bottom: 2px;
        }}
        .tb-reason-desc {{
            font-size: 0.8rem;
            color: {TEXT_SECONDARY};
            line-height: 1.4;
        }}

        /* ---- 푸터 ---- */
        .tb-footer {{
            margin-top: 28px;
            padding: 14px 18px;
            background: #EEF2FF;
            border: 1px solid #E0E7FF;
            border-radius: 10px;
            font-size: 0.78rem;
            color: {PRIMARY_DARK};
            line-height: 1.5;
        }}

        /* ---- 버튼 ---- */
        div[data-testid="stButton"] > button[kind="primary"] {{
            background: {PRIMARY};
            border: none;
            color: white;
            font-weight: 600;
            border-radius: 10px;
            height: 44px;
            padding: 0 22px;
        }}
        div[data-testid="stButton"] > button[kind="primary"]:hover {{
            background: {PRIMARY_DARK};
        }}

        /* ---- 텍스트 입력 (흰 배경 + 버튼과 같은 높이) ---- */
        [data-testid="stTextInput"] [data-baseweb="input"] {{
            background: {BG_CARD} !important;
            border: 1px solid {BORDER} !important;
            border-radius: 10px !important;
            height: 44px !important;
            box-shadow: none !important;
            outline: none !important;
        }}
        [data-testid="stTextInput"] [data-baseweb="base-input"] {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            height: 100% !important;
        }}
        [data-testid="stTextInput"] [data-baseweb="input"]:focus-within {{
            border-color: {PRIMARY} !important;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
        }}
        [data-testid="stTextInput"] input {{
            background: transparent !important;
            color: {TEXT_PRIMARY} !important;
            height: 100% !important;
            padding: 0 14px !important;
            font-size: 0.9rem !important;
            box-shadow: none !important;
        }}
        [data-testid="stTextInput"] input::placeholder {{
            color: {TEXT_MUTED} !important;
        }}

        /* ---- 탭 (st.tabs) ---- */
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {{
            gap: 4px;
            border-bottom: 1px solid {BORDER};
        }}
        div[data-testid="stTabs"] button[data-baseweb="tab"] {{
            height: 42px;
            padding: 0 18px;
            background: transparent;
            color: {TEXT_SECONDARY} !important;
            font-weight: 500;
            font-size: 0.92rem;
        }}
        div[data-testid="stTabs"] button[data-baseweb="tab"] p {{
            color: inherit !important;
            font-weight: inherit !important;
            font-size: inherit !important;
        }}
        div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {{
            color: {TEXT_PRIMARY} !important;
            background: rgba(99, 102, 241, 0.06);
            border-radius: 8px 8px 0 0;
        }}
        div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {{
            color: {PRIMARY} !important;
            font-weight: 700;
        }}
        div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
            background: {PRIMARY} !important;
            height: 2.5px !important;
        }}
        div[data-testid="stTabs"] [data-baseweb="tab-border"] {{
            display: none;
        }}

        /* ---- 추천 행 ---- */
        .tb-rec-row {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 4px;
            border-bottom: 1px solid #F1F5F9;
        }}
        .tb-rec-row:last-child {{ border-bottom: none; }}
        .tb-rec-rank {{
            width: 22px;
            color: {TEXT_MUTED};
            font-size: 0.85rem;
            font-variant-numeric: tabular-nums;
        }}
        .tb-rec-avatar {{
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: #EEF2FF;
            display: flex;
            align-items: center;
            justify-content: center;
            color: {PRIMARY_DARK};
            font-size: 1rem;
            flex-shrink: 0;
        }}
        .tb-rec-name {{
            font-size: 0.88rem;
            font-weight: 500;
            color: {TEXT_PRIMARY};
            flex-grow: 1;
        }}
        .tb-rec-meta {{
            font-size: 0.82rem;
            color: {TEXT_SECONDARY};
            min-width: 60px;
            text-align: right;
        }}

        /* ---- 사이드바 로고 링크 ---- */
        .tb-logo-link, .tb-logo-link:hover, .tb-logo-link:visited {{
            text-decoration: none !important;
            color: inherit !important;
            display: block;
            border-radius: 10px;
            transition: background 0.15s ease;
        }}
        .tb-logo-link:hover {{
            background: rgba(99, 102, 241, 0.08);
        }}

        /* ---- 랜딩 페이지 ---- */
        .tb-landing {{
            text-align: center;
            padding: 56px 24px 40px;
            margin: 0 auto 36px;
            max-width: 880px;
            background: #fff;
            border: 1px solid {BORDER};
            border-radius: 24px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 6px 24px rgba(15, 23, 42, 0.04);
        }}
        .tb-landing-logo {{
            width: 76px;
            height: 76px;
            border-radius: 20px;
            margin: 0 auto 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.1rem;
            background: linear-gradient(135deg, #6366F1, #8B5CF6);
            box-shadow: 0 12px 28px rgba(99, 102, 241, 0.28);
            color: white;
        }}
        .tb-landing-hero-img {{
            display: block;
            width: 320px;
            max-width: 78%;
            height: auto;
            margin: 0 auto 12px;
        }}
        .tb-landing-title {{
            font-size: 2.6rem;
            font-weight: 800;
            color: {TEXT_PRIMARY};
            letter-spacing: -1px;
            margin-bottom: 4px;
        }}
        .tb-landing-en {{
            font-size: 0.95rem;
            color: {PRIMARY};
            font-weight: 600;
            letter-spacing: 1px;
            margin-bottom: 18px;
        }}
        .tb-landing-sub {{
            font-size: 1.02rem;
            color: {TEXT_SECONDARY};
            line-height: 1.6;
            max-width: 620px;
            margin: 0 auto;
        }}
        .tb-landing-divider {{
            width: 36px;
            height: 3px;
            border-radius: 999px;
            background: linear-gradient(90deg, #6366F1, #8B5CF6);
            margin: 22px auto 14px;
        }}
        .tb-landing-tag {{
            font-size: 0.78rem;
            color: {TEXT_MUTED};
            letter-spacing: 0.5px;
        }}

        .tb-landing-card-link,
        .tb-landing-card-link:hover,
        .tb-landing-card-link:visited,
        .tb-landing-card-link:active {{
            text-decoration: none !important;
            color: inherit !important;
            display: block;
        }}
        .tb-landing-card {{
            background: {BG_CARD};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 22px 20px 18px;
            min-height: 188px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
            cursor: pointer;
            display: flex;
            flex-direction: column;
        }}
        .tb-landing-card-link:hover .tb-landing-card {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
            border-color: #C7D2FE;
        }}
        .tb-landing-card-link:hover .tb-landing-card-icon {{
            background: {PRIMARY};
            color: white;
        }}
        .tb-landing-card-link:hover .tb-landing-card-cta {{
            color: {PRIMARY_DARK};
        }}
        .tb-landing-card-icon {{
            width: 40px;
            height: 40px;
            border-radius: 11px;
            background: #EEF2FF;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            margin-bottom: 12px;
            transition: background 0.15s ease, color 0.15s ease;
        }}
        .tb-landing-card-title {{
            font-size: 1.02rem;
            font-weight: 700;
            color: {TEXT_PRIMARY};
            margin-bottom: 6px;
        }}
        .tb-landing-card-desc {{
            font-size: 0.82rem;
            color: {TEXT_SECONDARY};
            line-height: 1.5;
            flex-grow: 1;
        }}
        .tb-landing-card-cta {{
            margin-top: 14px;
            font-size: 0.82rem;
            font-weight: 600;
            color: {PRIMARY};
            transition: color 0.15s ease;
        }}

        /* ---- 페이지네이션 (추천 채널 리스트) ---- */
        .tb-pagination {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 6px;
            margin: 22px 0 6px;
            flex-wrap: wrap;
        }}
        .tb-page-num {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 36px;
            height: 36px;
            padding: 0 12px;
            border-radius: 8px;
            background: {BG_CARD};
            border: 1px solid {BORDER};
            font-size: 0.85rem;
            font-weight: 500;
            color: {TEXT_SECONDARY};
            text-decoration: none !important;
            transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
        }}
        .tb-page-num:hover:not(.disabled):not(.active) {{
            background: #EEF2FF;
            border-color: #C7D2FE;
            color: {PRIMARY_DARK};
        }}
        .tb-page-num.active {{
            background: {PRIMARY};
            border-color: {PRIMARY};
            color: white !important;
        }}
        .tb-page-num.disabled {{
            color: #CBD5E1;
            cursor: not-allowed;
        }}
        .tb-page-ellipsis {{
            color: {TEXT_MUTED};
            padding: 0 6px;
            font-size: 0.85rem;
        }}
        .tb-pagination-info {{
            text-align: center;
            font-size: 0.78rem;
            color: {TEXT_MUTED};
            margin-top: 4px;
        }}

        /* ---- 특성 카드 (추천 페이지) ---- */
        .tb-feat-row {{
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 10px 0;
        }}
        .tb-feat-icon {{
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.05rem;
            flex-shrink: 0;
        }}
        .tb-feat-icon.safe   {{ background: #D1FAE5; color: {GRADE_A}; }}
        .tb-feat-icon.danger {{ background: #FEE2E2; color: {GRADE_C}; }}
        .tb-feat-label {{
            font-size: 0.88rem;
            font-weight: 500;
            color: {TEXT_PRIMARY};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
