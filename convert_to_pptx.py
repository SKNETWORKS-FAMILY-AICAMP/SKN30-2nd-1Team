#!/usr/bin/env python3
"""Convert reports/presentation HTML slides → TubeEottae_Presentation.pptx"""

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

BASE   = Path(__file__).parent / "reports/presentation"
ASSETS = BASE / "assets"
OUT    = Path(__file__).parent / "reports/TubeEottae_Presentation.pptx"

# ── Colors ────────────────────────────────────────────────────────────────
def rgb(r, g, b): return RGBColor(r, g, b)

BG       = rgb(0xFF,0xFF,0xFF)
COVER_BG = rgb(0x1E,0x1B,0x4B)
ACCENT   = rgb(0x63,0x66,0xF1)
ACCENT_S = rgb(0xEE,0xF2,0xFF)
TEXT     = rgb(0x0F,0x17,0x2A)
TEXT2    = rgb(0x47,0x55,0x69)
TEXT3    = rgb(0x94,0xA3,0xB8)
BORDER   = rgb(0xE2,0xE8,0xF0)
SURFACE  = rgb(0xF8,0xFA,0xFC)
SURFACE2 = rgb(0xF1,0xF5,0xF9)
GRD_A    = rgb(0x10,0xB9,0x81)
GRD_B    = rgb(0xF5,0x9E,0x0B)
GRD_C    = rgb(0xEF,0x44,0x44)
HI_ROW   = rgb(0xED,0xE9,0xFE)
WARN_BG  = rgb(0xFF,0xF7,0xED)

FONT = "맑은 고딕"
SW, SH = Inches(10), Inches(5.625)
ML, CW = Inches(0.4), Inches(9.2)

# ── Low-level helpers ─────────────────────────────────────────────────────
def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])

def bg_color(slide, color=BG):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color

def rect(slide, x, y, w, h, fill=None, line=None, lw=0.75):
    s = slide.shapes.add_shape(1, x, y, w, h)
    if fill: s.fill.solid(); s.fill.fore_color.rgb = fill
    else:    s.fill.background()
    if line: s.line.color.rgb = line; s.line.width = Pt(lw)
    else:    s.line.fill.background()
    return s

def txt(slide, text, x, y, w, h, size=11, bold=False,
        color=TEXT, align=PP_ALIGN.LEFT, wrap=True):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return tb

def txt_lines(slide, lines, x, y, w, h, default_size=11, align=PP_ALIGN.LEFT):
    """lines = list of (text, size, bold, color) tuples"""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, (t, sz, bd, cl) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        run = p.add_run()
        run.text = t
        run.font.name = FONT
        run.font.size = Pt(sz or default_size)
        run.font.bold = bd
        run.font.color.rgb = cl or TEXT
    return tb

def img(slide, path, x, y, w, h=None):
    if not Path(path).exists(): return
    try:
        if h: slide.shapes.add_picture(str(path), x, y, w, h)
        else: slide.shapes.add_picture(str(path), x, y, w)
    except Exception as e:
        print(f"  [img] {path}: {e}")

# ── Compound helpers ──────────────────────────────────────────────────────
def header(slide, title, subtitle=None):
    rect(slide, ML, Inches(0.1), Inches(0.035), Inches(0.48), fill=ACCENT)
    txt(slide, title, ML+Inches(0.09), Inches(0.1), CW, Inches(0.5),
        size=22, bold=True, color=TEXT)
    y = Inches(0.63)
    if subtitle:
        txt(slide, subtitle, ML+Inches(0.09), y, CW, Inches(0.27),
            size=11, color=TEXT2)
        y = Inches(0.93)
    rect(slide, ML, y, CW, Pt(1), fill=BORDER)
    return y + Pt(6)

def footer(slide, left, right="SKN30 · 너놀자"):
    txt(slide, left,  ML,          Inches(5.32), Inches(5), Inches(0.22), size=9, color=TEXT3)
    txt(slide, right, Inches(5.1), Inches(5.32), Inches(4.5), Inches(0.22),
        size=9, color=TEXT3, align=PP_ALIGN.RIGHT)

def card(slide, x, y, w, h, title=None, body=None,
         fill=SURFACE, border=BORDER, title_color=TEXT,
         accent_top=None, font_size=10.5):
    rect(slide, x, y, w, h, fill=fill, line=border)
    if accent_top:
        rect(slide, x, y, w, Pt(3), fill=accent_top)
    cy = y + Inches(0.1)
    if title:
        txt(slide, title, x+Inches(0.1), cy, w-Inches(0.2), Inches(0.3),
            size=font_size+1, bold=True, color=title_color)
        cy += Inches(0.3)
    if body:
        txt(slide, body, x+Inches(0.1), cy, w-Inches(0.2),
            h-(cy-y)-Inches(0.08), size=font_size, color=TEXT2, wrap=True)

def kpi_box(slide, x, y, w, h, label, value, delta="",
            val_color=TEXT, border=BORDER, fill=SURFACE):
    rect(slide, x, y, w, h, fill=fill, line=border)
    txt(slide, label, x+Inches(0.1), y+Inches(0.08), w-Inches(0.2), Inches(0.25),
        size=10, color=TEXT2)
    txt(slide, value, x+Inches(0.1), y+Inches(0.33), w-Inches(0.2), Inches(0.45),
        size=26, bold=True, color=val_color)
    if delta:
        txt(slide, delta, x+Inches(0.1), y+Inches(0.78), w-Inches(0.2), Inches(0.22),
            size=9, color=TEXT3)

def section_label(slide, label, x, y, w, h, color=ACCENT):
    rect(slide, x, y, w, h, fill=SURFACE2, line=BORDER)
    txt(slide, label, x, y, w, h, size=10, bold=True, color=color,
        align=PP_ALIGN.CENTER)

def add_table(slide, headers, rows, x, y, w, h,
              hi_rows=None, col_widths=None):
    nrows, ncols = len(rows)+1, len(headers)
    tbl = slide.shapes.add_table(nrows, ncols, x, y, w, h).table
    # Column widths
    if col_widths:
        for i, cw in enumerate(col_widths):
            tbl.columns[i].width = cw
    # Header row
    for ci, hdr in enumerate(headers):
        cell = tbl.cell(0, ci)
        cell.fill.solid(); cell.fill.fore_color.rgb = ACCENT
        cell.text = hdr
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.runs[0] if p.runs else p.add_run()
        run.font.name = FONT; run.font.size = Pt(10); run.font.bold = True
        run.font.color.rgb = BG
    # Data rows
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = tbl.cell(ri+1, ci)
            is_hi = hi_rows and ri in hi_rows
            if is_hi:
                cell.fill.solid(); cell.fill.fore_color.rgb = HI_ROW
            else:
                cell.fill.solid(); cell.fill.fore_color.rgb = BG
            cell.text = str(val)
            p = cell.text_frame.paragraphs[0]
            run = p.runs[0] if p.runs else p.add_run()
            run.font.name = FONT; run.font.size = Pt(9.5)
            run.font.color.rgb = TEXT
    return tbl

def callout(slide, text, x, y, w, h, fill=ACCENT_S, border=ACCENT, bold_prefix=None):
    rect(slide, x, y, w, h, fill=fill, line=border)
    full = (bold_prefix + "  " + text) if bold_prefix else text
    txt(slide, full, x+Inches(0.12), y+Inches(0.07),
        w-Inches(0.24), h-Inches(0.14), size=10.5, color=TEXT2, wrap=True)

# ══════════════════════════════════════════════════════════════════════════
#  SLIDE BUILDERS
# ══════════════════════════════════════════════════════════════════════════

def s01_title(prs):
    sl = blank(prs); bg_color(sl, COVER_BG)
    # Badge
    rect(sl, ML, Inches(0.7), Inches(2.8), Inches(0.32), fill=rgb(0x3B,0x39,0x7A))
    txt(sl,"SKN30 · 2차 단위 프로젝트", ML+Inches(0.1), Inches(0.73),
        Inches(2.6), Inches(0.28), size=11, color=rgb(0xC7,0xD2,0xFE), bold=True)
    # Logo
    logo = ASSETS/"logo.png"
    if logo.exists():
        img(sl, logo, Inches(3.8), Inches(1.15), Inches(2.4), Inches(1.3))
    # Title
    txt(sl,"튜브어때 (TubeEottae)", Inches(1), Inches(2.55), Inches(8), Inches(0.9),
        size=38, bold=True, color=BG, align=PP_ALIGN.CENTER)
    # Subtitle
    txt(sl,"YouTube 크리에이터 분석을 통한 광고효율 및 지속가능성 추천 시스템",
        Inches(1), Inches(3.52), Inches(8), Inches(0.5),
        size=14, color=rgb(0xA5,0xB4,0xFC), align=PP_ALIGN.CENTER)
    rect(sl, 0, Inches(5.2), SW, Inches(0.42), fill=rgb(0x31,0x2E,0x81))
    txt(sl,"팀 너놀자 · 2026.05.15 ~ 2026.05.22", Inches(0), Inches(5.23),
        SW, Inches(0.3), size=10, color=rgb(0x81,0x7C,0xD0), align=PP_ALIGN.CENTER)

def s02_team(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "팀 소개 · 너놀자", '"같이 놀듯이, 데이터로 답을 찾는 5인 팀"')
    members = [
        ("강성준", "데이터 수집\nFeature · ML", "전처리 · ML 모델링"),
        ("김도훈", "데이터 수집\nFeature · ML", "Feature Engineering\nML 모델링"),
        ("천성배", "데이터 수집\nEDA · 분석", "데이터 분석 · EDA"),
        ("서해연", "데이터 수집 · ERD\nDL · 백엔드 · 발표", "딥러닝 · 백엔드"),
        ("정주애", "PM · 데이터 수집\n프론트", "프론트(Streamlit) · PPT"),
    ]
    n = 5; gap = Inches(0.08)
    cw = (CW - gap*(n-1)) / n
    ch = Inches(3.8)
    for i,(name,role,intro) in enumerate(members):
        x = ML + i*(cw+gap)
        rect(sl, x, y0, cw, ch, fill=SURFACE, line=BORDER)
        rect(sl, x, y0, cw, Pt(4), fill=ACCENT)
        txt(sl, name, x+Inches(0.05), y0+Inches(0.12), cw-Inches(0.1), Inches(0.38),
            size=14, bold=True, color=TEXT, align=PP_ALIGN.CENTER)
        txt(sl, role, x+Inches(0.05), y0+Inches(0.54), cw-Inches(0.1), Inches(0.7),
            size=9, color=ACCENT, align=PP_ALIGN.CENTER, wrap=True)
        txt(sl, intro, x+Inches(0.05), y0+Inches(1.28), cw-Inches(0.1), Inches(0.55),
            size=9, color=TEXT2, align=PP_ALIGN.CENTER, wrap=True)
    footer(sl, "02. 팀 소개")

def s03_overview(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "프로젝트 개요")
    # 대상
    rect(sl, ML, y0, CW, Inches(0.42), fill=SURFACE, line=BORDER)
    txt(sl,"대상", ML+Inches(0.1), y0+Inches(0.07), Inches(0.6), Inches(0.3),
        size=9, bold=True, color=TEXT3)
    pills = [("광고주","최적 채널 선정"), ("광고 에이전시","ROI 기반 캠페인"), ("MCN","크리에이터 관리")]
    for pi,(label,sub) in enumerate(pills):
        px = ML+Inches(0.8)+pi*Inches(2.8)
        rect(sl, px, y0+Inches(0.06), Inches(2.5), Inches(0.3), fill=ACCENT_S, line=ACCENT)
        txt(sl, f"{label}  ·  {sub}", px+Inches(0.1), y0+Inches(0.09), Inches(2.3), Inches(0.25),
            size=10, color=TEXT)
    y1 = y0 + Inches(0.48)
    # 배경
    bgs = [
        "01  '진성 인게이지먼트(실질 참여율)'가 광고 단가의 핵심 지표로 부상 — '숫자 거품' 시대 종료",
        "02  광고 구간 이탈 방지의 핵심 = 크리에이터와 시청자 간의 심리적 유대감",
        "03  구독자 10~100만 '허리 계층' 채널의 성장 정체 및 슬럼프 해결 필요",
    ]
    rect(sl, ML, y1, Inches(0.9), Inches(0.95), fill=SURFACE2, line=BORDER)
    txt(sl,"배경", ML+Inches(0.05), y1+Inches(0.3), Inches(0.8), Inches(0.35),
        size=9, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
    rect(sl, ML+Inches(0.9), y1, CW-Inches(0.9), Inches(0.95), fill=BG, line=BORDER)
    body = "\n".join(bgs)
    txt(sl, body, ML+Inches(1.0), y1+Inches(0.06), CW-Inches(1.1), Inches(0.85),
        size=9.5, color=TEXT2, wrap=True)
    y2 = y1 + Inches(1.01)
    # 문제 정의
    probs = [
        ("광고주", "매크로 댓글·친목질 등 전환력 낮은 채널을 걸러낼 정량적 지표 부족"),
        ("에이전시/MCN", "채널 몰락·파편화를 사전 감지 불가 — 조회수·시청시간 중심의 사후적 지표 한계"),
    ]
    rect(sl, ML, y2, Inches(0.9), Inches(0.8), fill=SURFACE2, line=BORDER)
    txt(sl,"문제\n정의", ML+Inches(0.05), y2+Inches(0.17), Inches(0.8), Inches(0.5),
        size=9, bold=True, color=GRD_C, align=PP_ALIGN.CENTER)
    rect(sl, ML+Inches(0.9), y2, CW-Inches(0.9), Inches(0.8), fill=BG, line=BORDER)
    body2 = "\n".join(f"{a}:  {b}" for a,b in probs)
    txt(sl, body2, ML+Inches(1.0), y2+Inches(0.07), CW-Inches(1.1), Inches(0.68),
        size=9.5, color=TEXT2, wrap=True)
    y3 = y2 + Inches(0.86)
    # 목표 + 결과물
    hw = (CW-Inches(0.1))/2
    card(sl, ML, y3, hw, Inches(1.15), title="프로젝트 목표",
         body="· 유튜브 채널 대규모 소셜 네트워크 데이터 구축\n· 상호작용 집중도 및 크리에이터 참여도 정량 분석",
         fill=SURFACE2, title_color=rgb(0x43,0x38,0xCA))
    card(sl, ML+hw+Inches(0.1), y3, hw, Inches(1.15), title="결과물",
         body="[광고주용]  최적 협업 대상 추천 매트릭스\n[MCN용]  유튜버 이탈 위험도 예측 스코어",
         fill=SURFACE2, title_color=GRD_A)
    footer(sl, "03. 프로젝트 개요")

def s04_effect(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "기대 효과 & 한계점", "데이터 기반 의사결정이 만드는 변화, 그리고 보완이 필요한 과제")
    # 기대 효과
    rect(sl, ML, y0, Inches(0.9), Inches(0.78), fill=SURFACE2, line=BORDER)
    txt(sl,"기대\n효과", ML+Inches(0.05), y0+Inches(0.16), Inches(0.8), Inches(0.48),
        size=9, bold=True, color=GRD_A, align=PP_ALIGN.CENTER)
    rect(sl, ML+Inches(0.9), y0, CW-Inches(0.9), Inches(0.78), fill=BG, line=BORDER)
    txt(sl,"광고주:  진성 채널 선별을 통한 마케팅 ROI 극대화 및 광고 단가 최적화\n"
        "에이전시/MCN:  데이터 기반의 선제적 리스크(데드존) 알람 및 장기적 수익 모델 확보",
        ML+Inches(1.0), y0+Inches(0.09), CW-Inches(1.1), Inches(0.62), size=10.5, color=TEXT2, wrap=True)
    y1 = y0 + Inches(0.84)
    # 한계점
    lims = [
        ("데이터 신뢰성", "댓글 샘플링(최신 100개) 기반으로 편향성 발생 가능"),
        ("포맷 차이", "숏폼(휘발성)과 롱폼(깊이) 간 성격 차이로 인한 해석 왜곡"),
        ("정성적 맥락", "단순 상호작용 빈도와 악플(부정 인게이지먼트) 구분을 위한 감성 분석 필터링 필요"),
    ]
    lh = Inches(0.55) * len(lims)
    rect(sl, ML, y1, Inches(0.9), lh, fill=SURFACE2, line=BORDER)
    txt(sl,"한계점 &\n보완 과제", ML+Inches(0.02), y1+Inches(0.45), Inches(0.88), Inches(0.7),
        size=9, bold=True, color=GRD_C, align=PP_ALIGN.CENTER)
    rect(sl, ML+Inches(0.9), y1, CW-Inches(0.9), lh, fill=BG, line=BORDER)
    body = "\n".join(f"[{k}]  {v}" for k,v in lims)
    txt(sl, body, ML+Inches(1.0), y1+Inches(0.07), CW-Inches(1.1), lh-Inches(0.14),
        size=10, color=TEXT2, wrap=True)
    footer(sl, "04. 기대 효과")

def s05_wbs(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "WBS · 작업 일정")
    rows = [
        ("5/15 (목)",     "주제 선정 & 배경 조사"),
        ("5/16~17 (토·일)","데이터 수집"),
        ("5/18 (월)",     "데이터 합치기 + 전처리"),
        ("5/18~19 (월·화)","데이터 분석 EDA"),
        ("5/18~19 (월·화)","Feature Engineering"),
        ("5/20~21 (수·목)","머신러닝 & 딥러닝 ★"),
        ("5/21 (목)",     "프론트 + 백엔드"),
        ("5/22 (금)",     "발표 정리 & 시연"),
    ]
    add_table(sl, ["날짜","작업"], rows, ML+Inches(1.5), y0,
              Inches(6.2), Inches(3.9), hi_rows=[5],
              col_widths=[Inches(2.2), Inches(4)])
    footer(sl, "05. WBS · 작업 일정")

def s06_features(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "핵심 기능", "4가지 기능으로 광고주 의사결정을 지원")
    feats = [
        ("① 채널 위험도 예측",
         "채널 URL/ID 입력 → 사전 수집 CSV 조회\n→ 0~100% 위험도 + A/B/C 등급 출력\n처리 시간 5초 이내"),
        ("② 위험 신호 분석",
         "6가지 위험 신호를 통합:\n이탈 · 정체 · 변동성 · 규칙성 · 민감 키워드 · 활성 시청자"),
        ("③ 광고주 추천",
         "· 장기 협업 (A등급, 안정적 업로드)\n· 단기 광고 (C등급 중 회복 신호)\n· 카테고리별 추천 (게임/음악/요리…)"),
        ("④ SHAP 설명 가능성",
         "각 채널의 위험 원인 TOP 3를 SHAP 값으로 시각화 — 광고주가 의사결정 근거를 직접 확인"),
    ]
    gap = Inches(0.08); fw = (CW-gap*3)/4; fh = Inches(1.7)
    for i,(t,b) in enumerate(feats):
        x = ML+i*(fw+gap)
        card(sl, x, y0, fw, fh, title=t, body=b,
             fill=ACCENT_S if i==0 else SURFACE,
             border=ACCENT if i==0 else BORDER,
             title_color=ACCENT)
    y1 = y0 + fh + Inches(0.12)
    txt(sl,"통합 위험도 구조 (가중 합산)",
        ML, y1, CW, Inches(0.3), size=12, bold=True, color=TEXT2)
    y2 = y1+Inches(0.32)
    risk = [
        ("평판 위험도  33%", "민감 키워드 점수 · (댓글 감성 — 향후)", GRD_C),
        ("트래픽 위험도  33%","이탈 · 정체 · 변동성 · 규칙성 (각 25%)", GRD_B),
        ("팬덤 위험도  33%", "활성 시청자 비율 · (시청 유지율 — 향후)", GRD_A),
    ]
    rw = (CW-gap*2)/3; rh = Inches(1.1)
    for i,(t,b,c) in enumerate(risk):
        x = ML+i*(rw+gap)
        card(sl, x, y2, rw, rh, title=t, body=b, title_color=c, accent_top=c)
    footer(sl, "08. 핵심 기능")

def s07_dataflow(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "데이터 흐름", "수집 → 정제 → 피처 → 모델 → 위험도 통합 (End-to-End)")
    # Flow row 1
    flow1 = [
        ("9,427","youtube_channels.csv\n(youtube-rank 크롤링)", SURFACE),
        ("8,193","cleaned\n(중복·결측 제거)", SURFACE),
        ("8,084","총 수집 채널\n(API 메타 + 영상)", ACCENT_S),
        ("3,337","final\n(개인 크리에이터 필터링)", SURFACE),
    ]
    bw = (CW-Inches(0.3)*3)/4; bh = Inches(0.9)
    for i,(val,lbl,fc) in enumerate(flow1):
        x = ML+i*(bw+Inches(0.3))
        rect(sl, x, y0, bw, bh, fill=fc,
             line=ACCENT if fc==ACCENT_S else BORDER)
        txt(sl, val, x, y0+Inches(0.06), bw, Inches(0.36),
            size=18, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
        txt(sl, lbl, x, y0+Inches(0.44), bw, Inches(0.44),
            size=9, color=TEXT2, align=PP_ALIGN.CENTER, wrap=True)
        if i < 3:
            txt(sl,"→", x+bw-Inches(0.02), y0+Inches(0.32), Inches(0.35), Inches(0.3),
                size=14, bold=True, color=TEXT3)
    y1 = y0+bh+Inches(0.18)
    # Flow row 2
    flow2 = [
        ("166K","videos\n(채널당 50개)", SURFACE),
        ("22","Feature Matrix\n(그룹 0/A/B/C)", ACCENT_S),
        ("6","위험 신호 모델\n(ML + 룰 + K-Means)", rgb(0xFF,0xF7,0xED)),
        ("A/B/C","risk_ranking.csv\n(최종 등급)", rgb(0xD1,0xFA,0xE5)),
    ]
    for i,(val,lbl,fc) in enumerate(flow2):
        x = ML+i*(bw+Inches(0.3))
        rect(sl, x, y1, bw, bh, fill=fc,
             line=ACCENT if fc==ACCENT_S else BORDER)
        txt(sl, val, x, y1+Inches(0.06), bw, Inches(0.36),
            size=18, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
        txt(sl, lbl, x, y1+Inches(0.44), bw, Inches(0.44),
            size=9, color=TEXT2, align=PP_ALIGN.CENTER, wrap=True)
        if i < 3:
            txt(sl,"→", x+bw-Inches(0.02), y1+Inches(0.32), Inches(0.35), Inches(0.3),
                size=14, bold=True, color=TEXT3)
    y2 = y1+bh+Inches(0.18)
    steps = [
        ("1️⃣ 수집","youtube-rank 웹 크롤링 → 채널 시드 확보 → YouTube Data API v3로 메타·영상 정보 수집 (다중 API 키 로테이션)"),
        ("2️⃣ 전처리·피처","영상 50개 미만 채널 제거 → wide/long 분리 → 최신 1개 영상 제외(조회수 미성숙 보정) → 22개 피처 계산"),
        ("3️⃣ 모델·통합","6개 점수 산출 → 가중 합산 (평판 33% + 트래픽 33% + 팬덤 33%) → ABCDF 등급화"),
    ]
    gap2 = Inches(0.08); sw2 = (CW-gap2*2)/3
    for i,(t,b) in enumerate(steps):
        card(sl, ML+i*(sw2+gap2), y2, sw2, Inches(1.1), title=t, body=b)
    footer(sl, "12. 데이터 흐름")

def s08_tech(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "사용한 기술 스택")
    stacks = [
        ("🎨 Frontend",   "Streamlit ≥1.29\nPlotly · Matplotlib\nSeaborn\nqrcode (QR 공유)"),
        ("📊 Data",       "Pandas ≥2.0\nNumPy ≥1.24\nPyYAML · python-dotenv\nPyMySQL · SQLAlchemy"),
        ("🧠 ML",         "scikit-learn ≥1.3\nXGBoost ≥2.0\nLightGBM ≥4.1\nimbalanced-learn (SMOTE)", True),
        ("🤖 DL / NLP",   "PyTorch ≥2.0\ntransformers ≥4.35\nKoBERT (감성 분석)"),
        ("🕷 수집",        "requests · BeautifulSoup4\nSelenium ≥4.15\ngoogle-api-python-client\n(YouTube Data API v3)"),
        ("⚙️ 개발 환경",   "Python ≥3.9\nuv (패키지 관리)\nGit + GitHub\nMySQL (선택)"),
    ]
    gap = Inches(0.08); cw2 = (CW-gap*3)/4; ch = Inches(2.0)
    for i,(t,b,*rest) in enumerate(stacks):
        is_accent = rest and rest[0]
        x = ML + (i%4)*(cw2+gap)
        y = y0 + (i//4)*(ch+Inches(0.1))
        card(sl, x, y, cw2, ch, title=t, body=b,
             fill=ACCENT_S if is_accent else SURFACE,
             border=ACCENT if is_accent else BORDER,
             title_color=ACCENT)
    footer(sl, "13. 기술 스택")

def s09_dataset(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "사용한 데이터", "YouTube 한국 채널 — 크롤링 + Data API v3")
    # KPI row
    kpis = [
        ("총 수집 채널",    "8,084",   "개 (YouTube API 메타·영상 수집 완료)", ACCENT, ACCENT_S),
        ("최종 분석 대상",  "3,337",   "개 (개인 크리에이터 필터링)", TEXT, SURFACE),
        ("영상 데이터",     "166,450", "개 (최신 1개 제외)", TEXT, SURFACE),
        ("사용 피처",       "22",      "개 (그룹 0/A/B/C)", TEXT, SURFACE),
    ]
    kw = (CW-Inches(0.24))/4; kh = Inches(1.05)
    for i,(l,v,d,vc,fc) in enumerate(kpis):
        kpi_box(sl, ML+i*(kw+Inches(0.08)), y0, kw, kh, l, v, d, val_color=vc, fill=fc)
    y1 = y0+kh+Inches(0.12)
    # Two columns
    hw = (CW-Inches(0.12))/2
    # Left: CSV table
    rows = [
        ("youtube_channels.csv",   "1.8 MB", "9,427"),
        ("…_cleaned.csv",          "1.7 MB", "8,193"),
        ("…_filtered.csv",         "732 KB", "3,353"),
        ("dataset_wide.csv",       "1.6 MB", "8,084"),
        ("filtered_dataset_wide.csv","694 KB","3,337"),
        ("filtered_dataset_long.csv","45 MB","166,450"),
        ("risk_ranking.csv [최종]", "381 KB", "3,337"),
    ]
    add_table(sl, ["파일","크기","행"], rows, ML, y1, hw, Inches(2.4),
              hi_rows=[4,5], col_widths=[Inches(3.0), Inches(0.8), Inches(0.8)])
    # Right: Feature groups
    feat_groups = [
        ("그룹 0 · 채널 기본 정보 (4)",
         "subscriber_count · view_count · total_video_count · channel_age_days"),
        ("그룹 A · 활동성 (7)",
         "avg/std_upload_interval · max_gap_days · hiatus_count_30d · upload_freq_change_rate"),
        ("그룹 B · 성과 (5)",
         "avg/std_view_count · avg_like · avg_comment · avg_engagement_rate"),
        ("그룹 C · Shorts (3) + D · 시계열 파생 (4)",
         "shorts_ratio · avg_shorts/normal_view · log_slope · recent_3m · trend_accel"),
    ]
    gh = (Inches(2.4)-Inches(0.09)*3)/4
    for i,(t,b) in enumerate(feat_groups):
        card(sl, ML+hw+Inches(0.12), y1+i*(gh+Inches(0.09)), hw, gh, title=t, body=b)
    footer(sl, "14. 사용한 데이터")

def s10_eda(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "EDA · 탐색적 데이터 분석", "notebooks/01_data_collection/10_data_EDA.ipynb")
    kpis = [
        ("전체 채널", "8,084", "개", TEXT),
        ("이탈 비율", "33.5%", "180일+ 미업로드", GRD_C),
        ("활성 비율", "66.5%", "정상 활동", GRD_A),
        ("정체 채널", "51.4%", "조회수 감소 추세", GRD_B),
    ]
    kw = (CW-Inches(0.24))/4; kh = Inches(0.9)
    for i,(l,v,d,vc) in enumerate(kpis):
        kpi_box(sl, ML+i*(kw+Inches(0.08)), y0, kw, kh, l, v, d, val_color=vc)
    y1 = y0+kh+Inches(0.1)
    hw = (CW-Inches(0.12))/2
    findings = [
        "이탈 라벨 분포: 이탈 33.5% / 활성 66.5% — 클래스 불균형 → class_weight + SMOTE",
        "조회수 분포: 로그 정규 분포에 가까움, 히트작 의존형 채널 다수",
        "업로드 주기: 평균 7~14일, 분산이 매우 큼 (시즌제·휴재 영향)",
        "Shorts 비율: 채널별 편차 큼(0~100%) — 일반 영상과 알고리즘이 다름",
        "활성 시청자 군집: K-Means K=4에서 슈퍼팬/일반/소극적/유령 4개 군집이 명확히 분리",
    ]
    fh = Inches(2.8)
    rect(sl, ML, y1, hw, fh, fill=SURFACE, line=BORDER)
    txt(sl,"핵심 발견 (Key Findings)", ML+Inches(0.1), y1+Inches(0.08), hw-Inches(0.2), Inches(0.28),
        size=12, bold=True, color=TEXT2)
    bullets = "\n".join(f"• {f}" for f in findings)
    txt(sl, bullets, ML+Inches(0.1), y1+Inches(0.38), hw-Inches(0.2), Inches(1.6),
        size=9.5, color=TEXT2, wrap=True)
    callout(sl, "upload_freq_change_rate → clip(-5, 5)\navg_engagement_rate → clip(0, 1)\n"
            "분모 0 채널에서 5e+10 같은 극단값 발생 → 모델 학습 전 클리핑",
            ML+Inches(0.1), y1+Inches(2.05), hw-Inches(0.2), Inches(0.65),
            fill=WARN_BG, border=GRD_B, bold_prefix="이상치 처리")
    # Right: image placeholders
    rh = (fh-Inches(0.08)*2)/3
    for i, lbl in enumerate(["📊 카테고리 분포 (assets/eda/category_dist.png)",
                               "📈 이탈 vs 활성 라벨 분포 (churn_label.png)",
                               "🔥 피처 상관관계 히트맵 (corr_heatmap.png)"]):
        ry = y1+i*(rh+Inches(0.08))
        rect(sl, ML+hw+Inches(0.12), ry, hw, rh, fill=SURFACE2, line=BORDER)
        txt(sl, lbl, ML+hw+Inches(0.22), ry+rh/2-Inches(0.12), hw-Inches(0.2), Inches(0.25),
            size=10, color=TEXT3, align=PP_ALIGN.CENTER)
    footer(sl, "15. EDA")

def s11_preprocess(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "데이터 전처리 결과", "6단계 파이프라인 — 원본 9,427 → 분석 대상 3,337 채널")
    hw = (CW-Inches(0.12))/2
    rows = [
        ("1","외부 크롤링 정제 (중복·결측 제거)","9,427 → 8,193"),
        ("2","영상 50개 미만 채널 제외","8,193 → 7,218"),
        ("3","개인 크리에이터 필터링 (조직 채널 제외)","7,218 → 3,353"),
        ("4","YouTube API 메타 수집 (channels + videos)","3,353 → 3,337"),
        ("5","wide / long 데이터셋 생성","166,450 영상"),
        ("6","최신 1개 영상 제외 (조회수 미성숙 보정) ★","166,450 행"),
    ]
    add_table(sl, ["#","단계","결과"], rows, ML, y0, hw, Inches(2.5),
              hi_rows=[5], col_widths=[Inches(0.3), Inches(2.9), Inches(1.35)])
    y_right = y0
    rw = hw
    rx = ML+hw+Inches(0.12)
    card(sl, rx, y_right, rw, Inches(1.1), title="결측치 (Missing)",
         body="· country — null 다수 + 범주 적음 → 모델 제외\n"
              "· comments 비공개 채널 → feature를 missing 허용으로 처리\n"
              "· Shorts 없는 채널 → avg_shorts_view = 0 채움")
    card(sl, rx, y_right+Inches(1.18), rw, Inches(1.0), title="이상치 (Outlier)",
         body="upload_freq_change_rate → clip(-5, +5)   // 이전 3개월 업로드 0 → 분모 0 → 5e+10 발생\n"
              "avg_engagement_rate → clip(0, 1)          // 조회수 극소 영상 → 분모 0 → 6e+07 발생")
    callout(sl, "days_since_last_upload는 이탈 라벨 생성에 직접 사용되므로 모델 학습 시 피처에서 제외",
            rx, y_right+Inches(2.26), rw, Inches(0.52), bold_prefix="데이터 리크 방지")
    footer(sl, "16. 데이터 전처리")

def s12_erd(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "ERD 구조도")
    erd_path = ASSETS/"SKN_2nd_ERD.png"
    if erd_path.exists():
        img(sl, erd_path, ML, y0, CW, Inches(4.15))
    else:
        rect(sl, ML, y0, CW, Inches(4.15), fill=SURFACE2, line=BORDER)
        txt(sl,"ERD 이미지 (assets/SKN_2nd_ERD.png)",
            ML+Inches(3), y0+Inches(1.9), Inches(3.2), Inches(0.35),
            size=12, color=TEXT3, align=PP_ALIGN.CENTER)
    footer(sl, "12. ERD 구조도")

def s13_model_results(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "모델 결과 (학습 결과서)",
                "3개 ML 모델 × 3개 위험 신호 + 3개 룰/군집 점수 — 5-fold 교차검증")
    rows = [
        ("이탈 (2,707/5,376)","Logistic Regression","0.960","0.861","0.996","0.759","0.080"),
        ("","Random Forest","1.000","0.981","1.000","0.963","0.021"),
        ("","XGBoost (Calibrated) ★","1.000","1.000","1.000","1.000","0.000"),
        ("정체 (1,712/1,621)","Logistic Regression","0.963","0.907","0.894","0.921","0.076"),
        ("","Random Forest","1.000","0.999","0.999","1.000","0.007"),
        ("","XGBoost (Calibrated) ★","1.000","0.999","0.999","0.999","0.001"),
        ("변동성 (1,327/2,006)","Logistic Regression","0.988","0.928","0.949","0.908","0.044"),
        ("","Random Forest","1.000","0.998","0.997","0.998","0.006"),
        ("","XGBoost (Calibrated) ★","1.000","0.997","0.997","0.998","0.002"),
    ]
    add_table(sl, ["위험 신호","모델","AUC-ROC","F1","Recall","Precision","Brier"],
              rows, ML, y0, CW, Inches(2.55), hi_rows=[2,5,8],
              col_widths=[Inches(1.6),Inches(2.2),Inches(0.85),Inches(0.75),
                          Inches(0.8),Inches(0.9),Inches(0.8)])
    y1 = y0+Inches(2.62)
    rule_data = [
        ("📏 규칙성 점수 (룰 기반)",
         "안정 56.1% · 주의 43.8% · 불안정 0%\nCV(50%) + 이상치(30%) + 최대 공백(20%)"),
        ("🚨 민감 키워드 (62개)",
         "안전 80.6% · 중위험 14.5% · 고위험 4.9%\n정치/혐오/자극/성인 4개 카테고리"),
        ("👥 활성 시청자 (K-Means K=4)",
         "슈퍼팬 14.6% · 일반팬 63.6% · 소극적 19.6% · 유령 2.1%"),
    ]
    rw = (CW-Inches(0.16))/3; rh = Inches(0.76)
    for i,(t,b) in enumerate(rule_data):
        card(sl, ML+i*(rw+Inches(0.08)), y1, rw, rh, title=t, body=b)
    callout(sl,"모든 ML 모델이 PRD KPI(Recall ≥ 80%, F1 ≥ 0.7, AUC ≥ 0.85)를 크게 상회 — "
            "단, AUC 1.000은 데이터 자체의 명확한 라벨 분리(180일 기준)에서 비롯된 것으로 과적합 위험 존재.",
            ML, y1+rh+Inches(0.08), CW, Inches(0.42), bold_prefix="KPI 달성")
    footer(sl, "17. 모델 결과")

def s14_model_select(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "모델 선정 · RF / LGBM / XGB 비교",
                "테스트 성능과 모델별 강점을 기준으로 LightGBM 중심 Weighted Soft Voting 전략 선택")
    hw = (CW-Inches(0.12))/2
    rows = [
        ("LightGBM (candidate 2) ★","0.52","0.837","0.679","0.410","0.511","0.834"),
        ("XGBoost (candidate 4)","0.55","0.831","0.671","0.367","0.474","0.837"),
        ("Random Forest (candidate 4)","0.57","0.829","0.736","0.281","0.406","0.839"),
    ]
    add_table(sl, ["모델","Threshold","Accuracy","Precision","Recall","F1","ROC-AUC"],
              rows, ML, y0, hw, Inches(1.3), hi_rows=[0],
              col_widths=[Inches(2.0),Inches(0.65),Inches(0.7),Inches(0.7),
                          Inches(0.65),Inches(0.6),Inches(0.65)])
    y1 = y0+Inches(1.37)
    best = [
        ("Best Targeting","LightGBM\nAccuracy · Recall · F1 1위", ACCENT),
        ("Explainability","XGBoost\nSHAP 설명에 적합", GRD_B),
        ("Stability","Random Forest\nROC-AUC · Precision 강점", GRD_A),
    ]
    bw = (hw-Inches(0.08)*2)/3; bh = Inches(0.8)
    for i,(t,b,c) in enumerate(best):
        card(sl, ML+i*(bw+Inches(0.08)), y1, bw, bh, title=t, body=b,
             title_color=c, accent_top=c)
    callout(sl,"현재 단일 모델 테스트 기준 Recall 최대 41.0%, F1 최대 0.511, "
            "ROC-AUC 최대 0.839로 PRD 목표(Recall 80%, F1 0.7, AUC 0.85)에는 미달",
            ML, y1+bh+Inches(0.08), hw, Inches(0.55),
            fill=WARN_BG, border=GRD_B, bold_prefix="KPI 점검")
    # Right panel
    rx = ML+hw+Inches(0.12); rw = hw
    txt(sl,"선정 전략 · Weighted Soft Voting",
        rx, y0, rw, Inches(0.28), size=12, bold=True, color=TEXT2)
    callout(sl,"가중치:  LGBM 0.50 + XGB 0.30 + RF 0.20",
            rx, y0+Inches(0.3), rw, Inches(0.38))
    strategy = [
        ("① LightGBM 50%", ACCENT,
         "세 모델 중 Accuracy(83.7%), Recall(41.0%), F1(0.511)이 가장 높아 이탈 후보를 찾는 핵심 모델"),
        ("② XGBoost 30%", GRD_B,
         "Accuracy 83.1%, ROC-AUC 0.837. SHAP 기반 원인 설명에 강해 LightGBM 판단을 해석 가능하게 보완"),
        ("③ Random Forest 20%", GRD_A,
         "Precision(0.736)과 ROC-AUC(0.839)가 가장 높아 부스팅 모델의 노이즈 민감도를 완충"),
    ]
    sh2 = (Inches(3.3)-Inches(0.1)*2)/3
    for i,(t,c,b) in enumerate(strategy):
        card(sl, rx, y0+Inches(0.76)+i*(sh2+Inches(0.1)), rw, sh2,
             title=t, body=b, title_color=c,
             border=c, accent_top=None)
    callout(sl,"단일 모델 채택 시 LightGBM이 최우선 후보이며, "
            "서비스 적용 전에는 가중 앙상블 성능 재측정과 threshold 재튜닝이 필요",
            rx, y0+Inches(3.64), rw, Inches(0.55), bold_prefix="결론")
    footer(sl, "18. 모델 선정 이유")

def s15_insights(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "광고주 관점 핵심 인사이트", "10_data_EDA.ipynb 필수 차트 04 · 08 · 11 · 13 기반")
    insights = [
        ("04","채널 포맷별 참여율",
         "숏폼·롱폼·혼합형을 같은 기준으로 비교해 광고 포맷 적합도를 판단.",
         "광고 집행 전, 조회수 규모보다 포맷별 참여율 분포를 먼저 확인해야 함.",
         ASSETS/"eda/insight-04-format-opt.png"),
        ("08","쇼츠 성과의 롱폼 전이",
         "쇼츠 조회수가 긴 영상 성과로 이어지는지 로그축 산점도로 검증.",
         "쇼츠만 높은 채널은 단기 노출형, 롱폼도 강한 채널은 브랜드 설득형에 적합.",
         ASSETS/"eda/insight-08-shorts-synergy.png"),
        ("11","영상 길이별 Sweet Spot",
         "영상 길이 구간별 평균 조회수와 관여도를 나눠 캠페인 메시지 밀도를 조정.",
         "짧은 영상은 도달, 5~20분 구간은 소통과 설득 성과를 함께 봐야 함.",
         ASSETS/"eda/insight-11-duration-sweetspot.png"),
        ("13","업로드 주기 × 방치 기간",
         "평소 성실도와 최근 공백에 따른 초기 조회수 부스팅 편차를 매트릭스로 확인.",
         "엠바고·런칭 캠페인은 최근 업로드 공백과 주기 리스크를 계약 전에 점검.",
         ASSETS/"eda/insight-13-upload-boosting.png"),
    ]
    gap = Inches(0.08); iw = (CW-gap*3)/4; ih = Inches(3.55)
    for i,(num,title,desc,takeaway,ipath) in enumerate(insights):
        x = ML+i*(iw+gap)
        rect(sl, x, y0, iw, ih, fill=SURFACE, line=BORDER)
        # Number badge
        rect(sl, x, y0, iw, Inches(0.28), fill=ACCENT if i==0 else SURFACE2)
        txt(sl, num, x, y0+Inches(0.03), iw, Inches(0.24),
            size=11, bold=True,
            color=BG if i==0 else ACCENT, align=PP_ALIGN.CENTER)
        # Title
        txt(sl, title, x+Inches(0.06), y0+Inches(0.32), iw-Inches(0.12), Inches(0.32),
            size=10, bold=True, color=TEXT)
        # Description
        txt(sl, desc, x+Inches(0.06), y0+Inches(0.66), iw-Inches(0.12), Inches(0.45),
            size=8.5, color=TEXT2, wrap=True)
        # Image
        img_h = Inches(1.7)
        if Path(ipath).exists():
            img(sl, ipath, x+Inches(0.04), y0+Inches(1.14), iw-Inches(0.08), img_h)
        else:
            rect(sl, x+Inches(0.04), y0+Inches(1.14), iw-Inches(0.08), img_h,
                 fill=SURFACE2, line=BORDER)
            txt(sl,"[차트]", x+Inches(0.04), y0+Inches(1.95), iw-Inches(0.08), Inches(0.3),
                size=9, color=TEXT3, align=PP_ALIGN.CENTER)
        # Takeaway
        rect(sl, x, y0+ih-Inches(0.62), iw, Inches(0.62), fill=ACCENT_S, line=ACCENT)
        txt(sl, takeaway, x+Inches(0.05), y0+ih-Inches(0.58), iw-Inches(0.1), Inches(0.55),
            size=8.5, color=TEXT2, wrap=True)
    callout(sl,"구독자 수만 보지 말고 포맷 적합도, 롱폼 전이력, 영상 길이별 관여도, "
            "최근 업로드 성실도를 함께 확인해야 실제 광고 안정성을 판단할 수 있습니다.",
            ML, y0+ih+Inches(0.1), CW, Inches(0.42), bold_prefix="광고주 의사결정 기준")
    footer(sl, "15. 인사이트")

def s16_demo(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "화면 시연")
    rect(sl, ML+Inches(3), y0+Inches(0.4), Inches(3.2), Inches(0.38), fill=ACCENT)
    txt(sl,"Live Demo", ML+Inches(3), y0+Inches(0.4), Inches(3.2), Inches(0.38),
        size=14, bold=True, color=BG, align=PP_ALIGN.CENTER)
    txt(sl,"지금부터 실제 화면을 보여드리겠습니다.",
        ML, y0+Inches(1.0), CW, Inches(0.7),
        size=32, bold=True, color=TEXT, align=PP_ALIGN.CENTER)
    txt(sl,"대시보드, 채널 조회, 추천 화면 흐름을 라이브로 시연합니다.",
        ML, y0+Inches(1.85), CW, Inches(0.42),
        size=14, color=TEXT2, align=PP_ALIGN.CENTER)
    callout(sl,"uv run streamlit run app/main.py  →  http://localhost:8501",
            ML+Inches(2.3), y0+Inches(2.5), Inches(4.6), Inches(0.45), bold_prefix="실행")
    footer(sl, "17. 화면 시연")

def s17_demo_full(prs):
    sl = blank(prs); bg_color(sl, COVER_BG)
    txt(sl,"🔴  LIVE", Inches(0), Inches(2.3), SW, Inches(1.2),
        size=60, bold=True, color=BG, align=PP_ALIGN.CENTER)
    txt(sl,"Streamlit 앱 전체화면 시연",
        Inches(0), Inches(3.6), SW, Inches(0.5),
        size=18, color=rgb(0xA5,0xB4,0xFC), align=PP_ALIGN.CENTER)
    txt(sl,"http://localhost:8501", Inches(0), Inches(4.2), SW, Inches(0.38),
        size=14, color=rgb(0x81,0x7C,0xD0), align=PP_ALIGN.CENTER)

def s18_results(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "프로젝트 결과", "확장 가능성 · 주요 이슈 및 해결")
    callout(sl,"광고주가 채널의 현재 인기뿐 아니라 활동 지속 가능성을 함께 판단할 수 있는 "
            "분석 흐름을 MVP 형태로 구현했습니다.",
            ML, y0, CW, Inches(0.48), bold_prefix="결과 요약")
    y1 = y0+Inches(0.55)
    hw = (CW-Inches(0.12))/2
    card(sl, ML, y1, hw, Inches(3.15), title="🚀 확장 가능성",
         body="· 실시간 YouTube API 분석 (현재는 스냅샷 기반)\n"
              "· 시계열 위험도 추적 대시보드\n"
              "· TikTok / Instagram 멀티 플랫폼 확장\n"
              "· 광고 성과 데이터 연동을 통한 ROI 검증\n"
              "· 뉴스/SNS 외부 데이터 결합으로 논란 탐지",
         fill=ACCENT_S, border=ACCENT, title_color=ACCENT, font_size=11)
    rx = ML+hw+Inches(0.12)
    issues = [
        ("API 쿼터 초과",   "다중 키 로테이션 + 로컬 캐시"),
        ("클래스 불균형",   "SMOTE + class_weight + threshold tuning"),
        ("이상값(분모 0)",  "clip 처리 (-5~+5, 0~1)"),
        ("시즌제 채널 오분류","카테고리별 별도 분석"),
        ("댓글 비공개 채널","feature missing 허용"),
    ]
    add_table(sl, ["이슈","해결"], issues, rx, y1, hw, Inches(3.15),
              col_widths=[Inches(1.9), Inches(2.55)])
    footer(sl, "19. 프로젝트 결과")

def s19_utilization(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "활용 가능성", "3개 핵심 대상 + 4가지 확장 방향")
    txt(sl,"즉시 활용 (현재 MVP로 가능)", ML, y0, CW, Inches(0.28),
        size=12, bold=True, color=TEXT2)
    y1 = y0+Inches(0.3)
    targets = [
        ("🏢 광고주",     "장기 계약 전 채널 위험도 사전 점검 → 계약 후 활동 중단 리스크 차단\n예: A등급 채널 우선 협업"),
        ("🎯 광고 에이전시","캠페인 채널 선정 시 데이터 기반 ROI 의사결정 → 정성 평가 의존도 ↓\n예: 카테고리별 추천 활용"),
        ("📺 MCN",       "소속 크리에이터 활동 모니터링 대시보드 → 위험 신호 조기 발견 + 케어\n예: B → C 등급 하락 시 알림"),
    ]
    tw = (CW-Inches(0.16))/3; th = Inches(1.35)
    for i,(t,b) in enumerate(targets):
        card(sl, ML+i*(tw+Inches(0.08)), y1, tw, th, title=t, body=b,
             fill=ACCENT_S, border=ACCENT, title_color=ACCENT)
    y2 = y1+th+Inches(0.15)
    txt(sl,"향후 확장 방향", ML, y2, CW, Inches(0.28), size=12, bold=True, color=TEXT2)
    y3 = y2+Inches(0.3)
    exts = [
        ("🔄 실시간 분석","스냅샷 → 6h/12h/일 단위 정기 크롤링 + 신규 채널 즉시 분석"),
        ("📈 시계열 추적","동일 채널의 위험도 변화를 시간 축으로 시각화"),
        ("🌐 멀티 플랫폼","TikTok · Instagram 확장 → 통합 인플루언서 평가"),
        ("📰 외부 데이터","뉴스/SNS 논란 탐지 + 실제 광고 성과 데이터 연동"),
    ]
    ew = (CW-Inches(0.24))/4; eh = Inches(0.9)
    for i,(t,b) in enumerate(exts):
        card(sl, ML+i*(ew+Inches(0.08)), y3, ew, eh, title=t, body=b)
    callout(sl,"광고주/에이전시 대상 SaaS 구독 (월 정액) + 채널 분석 리포트 단건 판매 + 추천 API 호출 기반 과금",
            ML, y3+eh+Inches(0.1), CW, Inches(0.42), bold_prefix="비즈니스 모델 (가설)")
    footer(sl, "20. 활용 가능성")

def s20_limits(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "한계점", "현재 MVP 기준에서 남아 있는 제약과 향후 보완 과제")
    hw = (CW-Inches(0.12))/2
    data_lims = [
        "스냅샷 의존성: 2026-05-17 이후 채널 변화는 반영되지 않음",
        "신규 채널 분석 불가: 사전 수집 DB에 없는 채널은 즉시 분석할 수 없음",
        "외부 이슈 미반영: 논란, 건강, 개인 사정 등 비정형 이탈 요인은 포착 어려움",
        "AUC 1.000의 함정: 180일 라벨 분리가 지나치게 명확해 실제 운영 기준 재검토 필요",
    ]
    card(sl, ML, y0, hw, Inches(2.55), title="⚠️ 데이터 · 모델 한계",
         body="\n".join(f"· {l}" for l in data_lims),
         border=GRD_C, accent_top=GRD_C, title_color=GRD_C, font_size=10.5)
    svc_lims = [
        "한국어 중심: 다국어 채널 분석에는 추가 검증이 필요",
        "광고 성과 검증 부재: 실제 ROI와 위험도 상관관계는 아직 입증되지 않음",
        "실시간성 부족: 현재는 정적 배치 기반이라 변화 탐지가 지연될 수 있음",
        "운영 확장 필요: API, 저장소, 배포 구조를 함께 키워야 서비스화 가능",
    ]
    card(sl, ML+hw+Inches(0.12), y0, hw, Inches(2.0), title="🛠 서비스 · 검증 한계",
         body="\n".join(f"· {l}" for l in svc_lims), title_color=TEXT)
    callout(sl,"실시간 수집, 외부 이슈 반영, 광고 성과 연동까지 확장하면 의사결정 도구로서 완성도가 더 높아집니다.",
            ML+hw+Inches(0.12), y0+Inches(2.08), hw, Inches(0.45), bold_prefix="향후 과제")
    footer(sl, "20. 한계점")

def s21_retrospective(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "회고록")
    card(sl, ML, y0, CW, Inches(0.7), title="💬 팀 회고",
         body="이번 프로젝트는 데이터 수집, 모델링, 백엔드, 프론트까지 전 과정을 직접 연결해보며 "
              "협업 방식과 문제 해결 흐름을 함께 다져본 경험이었습니다.",
         fill=ACCENT_S, border=ACCENT, title_color=ACCENT, font_size=11)
    y1 = y0+Inches(0.78)
    members = ["강성준","김도훈","천성배","서해연","정주애"]
    mw = (CW-Inches(0.08)*3)/4
    for i,name in enumerate(members[:4]):
        x = ML+(i%4)*(mw+Inches(0.08))
        card(sl, x, y1, mw, Inches(1.0), title=name,
             body="(한 줄 회고를 입력해주세요)")
    # 5th member spans full width
    card(sl, ML, y1+Inches(1.08), CW, Inches(1.0), title=members[4],
         body="(한 줄 회고를 입력해주세요)")
    footer(sl, "21. 회고록")

def s22_references(prs):
    sl = blank(prs); bg_color(sl)
    y0 = header(sl, "참고 자료", "기술 문서 · 내부 산출물 · 시장 통계")
    hw = (CW-Inches(0.12))/2
    # Left: tech + market
    tech_refs = [
        "YouTube Data API v3 — developers.google.com/youtube/v3",
        "scikit-learn — User Guide (Ensemble, Calibration)",
        "XGBoost — Documentation, Tianqi Chen et al.",
        "LightGBM — Microsoft Research",
        "SHAP — Lundberg & Lee (2017), A Unified Approach to Interpreting Model Predictions",
        "KoBERT — SKTBrain, 한국어 사전학습 BERT",
        "Streamlit — docs.streamlit.io",
        "imbalanced-learn (SMOTE) — Chawla et al. (2002)",
    ]
    market = [
        "국내 디지털 크리에이터 산업 매출 (2025): 약 5조 5천억 원",
        "글로벌 인플루언서 마케팅 시장: 약 330억 달러",
        "미국 크리에이터 광고 지출: 약 370억 달러",
    ]
    rect(sl, ML, y0, hw, Inches(3.85), fill=SURFACE, line=BORDER)
    txt(sl,"📚 기술 문서 & 라이브러리",
        ML+Inches(0.1), y0+Inches(0.08), hw-Inches(0.2), Inches(0.28),
        size=11, bold=True, color=TEXT2)
    txt(sl,"\n".join(f"• {r}" for r in tech_refs),
        ML+Inches(0.1), y0+Inches(0.38), hw-Inches(0.2), Inches(2.0),
        size=9.5, color=TEXT2, wrap=True)
    txt(sl,"📊 시장 통계 출처",
        ML+Inches(0.1), y0+Inches(2.45), hw-Inches(0.2), Inches(0.28),
        size=11, bold=True, color=TEXT2)
    txt(sl,"\n".join(f"• {r}" for r in market),
        ML+Inches(0.1), y0+Inches(2.76), hw-Inches(0.2), Inches(0.9),
        size=9.5, color=TEXT2, wrap=True)
    # Right: internal docs
    rx = ML+hw+Inches(0.12)
    docs = [
        "docs/튜브어때_PRD.md — 전체 PRD (584줄)",
        "docs/02_modeling_정리.md — 모델 파이프라인 상세",
        "docs/csv_파일_정리.md — 데이터 흐름·파일 목록",
        "docs/db_erd.md — ERD 정의",
        "docs/feature_description.md — 피처 설계서",
        "docs/폴더구조.md — 프로젝트 구조",
        "notebooks/02_modeling/*.ipynb — 6개 모델 노트북",
        "notebooks/01_data_collection/10_data_EDA.ipynb",
    ]
    rect(sl, rx, y0, hw, Inches(3.0), fill=SURFACE, line=BORDER)
    txt(sl,"📁 내부 산출물 (프로젝트 문서)",
        rx+Inches(0.1), y0+Inches(0.08), hw-Inches(0.2), Inches(0.28),
        size=11, bold=True, color=TEXT2)
    txt(sl,"\n".join(f"• {d}" for d in docs),
        rx+Inches(0.1), y0+Inches(0.38), hw-Inches(0.2), Inches(2.4),
        size=9.5, color=TEXT2, wrap=True)
    callout(sl,"GitHub: SKNETWORKS-FAMILY-AICAMP / SKN30-2nd-1Team\n팀명: 너놀자 · 5인 · 2026.05.15 ~ 2026.05.22",
            rx, y0+Inches(3.08), hw, Inches(0.65))
    footer(sl, "22. 참고 자료")

def s23_qa(prs):
    sl = blank(prs); bg_color(sl)
    rect(sl, 0, 0, SW, SH, fill=COVER_BG)
    rect(sl, 0, Inches(5.1), SW, Inches(0.52), fill=rgb(0x31,0x2E,0x81))
    rect(sl, ML, Inches(0.8), Inches(1.8), Inches(0.38), fill=rgb(0x3B,0x39,0x7A))
    txt(sl,"Closing", ML+Inches(0.1), Inches(0.83), Inches(1.6), Inches(0.32),
        size=14, bold=True, color=rgb(0xC7,0xD2,0xFE))
    txt(sl,"Q&A", Inches(0), Inches(1.35), SW, Inches(2.1),
        size=96, bold=True, color=BG, align=PP_ALIGN.CENTER)
    txt(sl,"감사합니다", Inches(0), Inches(3.55), SW, Inches(0.8),
        size=32, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
    txt(sl,"질문 주시면 이어서 설명드리겠습니다.",
        Inches(0), Inches(4.4), SW, Inches(0.45),
        size=15, color=rgb(0xA5,0xB4,0xFC), align=PP_ALIGN.CENTER)

# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════
def main():
    prs = Presentation()
    prs.slide_width  = SW
    prs.slide_height = SH

    builders = [
        s01_title, s02_team, s03_overview, s04_effect, s05_wbs,
        s06_features, s07_dataflow, s08_tech, s09_dataset, s10_eda,
        s11_preprocess, s12_erd, s13_model_results, s14_model_select,
        s15_insights, s16_demo, s17_demo_full, s18_results, s19_utilization,
        s20_limits, s21_retrospective, s22_references, s23_qa,
    ]

    for i, builder in enumerate(builders, 1):
        print(f"  [{i:02d}/23] {builder.__name__}")
        builder(prs)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT))
    print(f"\n✓  Saved → {OUT}")

if __name__ == "__main__":
    main()
