"""
YouTube channel churn statistics report (ReportLab CID font version)
====================================================================

Purpose
- Load a CSV created by the YouTube rank scraper.
- Apply filtering rules.
- Generate a PDF report.
- Keep summary text and tables selectable/copyable in the PDF.
- Avoid ReportLab TTFont errors with Noto CJK CFF/PostScript fonts by using
  ReportLab built-in Korean CID fonts for PDF text.

Usage
    python youtube_churn_statistics_report_reportlab_cid.py input.csv output.pdf

Dependencies
    python -m pip install pandas matplotlib seaborn reportlab

Notes
- Summary/table text is written with ReportLab Korean CID font: HYGothic-Medium.
- Charts are rendered as PNG images and inserted into the PDF.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# =========================================
# CLI args
# =========================================
if len(sys.argv) >= 2:
    INPUT_CSV = sys.argv[1]
else:
    INPUT_CSV = "youtube_channels.csv"

if len(sys.argv) >= 3:
    OUTPUT_PDF = sys.argv[2]
else:
    OUTPUT_PDF = "youtube_churn_statistics_report.pdf"

if len(sys.argv) > 3:
    print("Usage: python youtube_churn_statistics_report_reportlab_cid.py [input_csv] [output_pdf]")
    sys.exit(1)

CHURN_THRESHOLD = 180

# =========================================
# ReportLab Korean font - no TTFont required
# =========================================
# ReportLab built-in CID Korean fonts. These avoid CFF/PostScript outline errors.
PDF_FONT = "HYGothic-Medium"
PDF_FONT_BOLD = "HYGothic-Medium"
pdfmetrics.registerFont(UnicodeCIDFont(PDF_FONT))

# =========================================
# Matplotlib Korean font for chart PNGs
# =========================================
def setup_matplotlib_korean_font() -> str:
    """Pick an installed CJK font for chart images."""
    preferred_names = [
        "NanumGothic",
        "Noto Sans CJK KR",
        "Noto Sans CJK JP",
        "Noto Sans CJK SC",
        "Noto Sans CJK TC",
        "DejaVu Sans",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in preferred_names:
        if name in available:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False
            sns.set_theme(style="whitegrid", font=name)
            print(f"[matplotlib font] {name}")
            return name

    # Last resort: default font. Korean may not render in chart images.
    plt.rcParams["axes.unicode_minus"] = False
    sns.set_theme(style="whitegrid")
    print("[matplotlib font] default - Korean may not render in chart images")
    return "default"

setup_matplotlib_korean_font()

# =========================================
# Utilities
# =========================================
def days_since(date_str):
    if pd.isna(date_str):
        return None
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
        return (date.today() - dt).days
    except Exception:
        return None


def is_topic_channel(name) -> bool:
    if pd.isna(name):
        return False
    return str(name).strip().lower().endswith("- topic")


def subscriber_bucket(x):
    if pd.isna(x):
        return "Unknown"
    if x < 200_000:
        return "1~20만"
    if x < 400_000:
        return "20~40만"
    if x < 600_000:
        return "40~60만"
    if x < 800_000:
        return "60~80만"
    if x < 1_000_000:
        return "80~100만"
    return "100만 이상"


def normalize_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = [
        "subscriber_count",
        "total_views",
        "video_count",
        "days_since_latest_video",
        "is_churned",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def save_fig_to_png(fig, prefix: str) -> str:
    tmp = tempfile.NamedTemporaryFile(prefix=prefix, suffix=".png", delete=False)
    path = tmp.name
    tmp.close()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path

# =========================================
# Chart functions
# =========================================
def plot_hist_boxplot(data: pd.DataFrame, x_col: str, title: str) -> str:
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(12, 8),
        gridspec_kw={"height_ratios": [1, 4]},
        sharex=True,
    )
    sns.boxplot(data=data, x=x_col, ax=axes[0])
    sns.histplot(data=data, x=x_col, bins=30, kde=True, ax=axes[1])
    axes[0].set_title(title)
    axes[0].set_xlabel("")
    axes[0].grid(True)
    axes[1].set_xlabel("최근 영상 업로드 후 경과일")
    axes[1].set_ylabel("채널 수")
    axes[1].grid(True)
    fig.tight_layout()
    return save_fig_to_png(fig, "churn_hist_box_")


def plot_bucket_boxplot(data: pd.DataFrame, order: list[str]) -> str:
    fig, ax = plt.subplots(figsize=(13, 6.8))
    sns.boxplot(
        data=data,
        x="subscriber_bucket",
        y="days_since_latest_video",
        order=order,
        ax=ax,
    )
    ax.set_title("구독자 구간별 이탈 채널 days_since_latest_video 박스플롯")
    ax.set_xlabel("구독자 구간")
    ax.set_ylabel("최근 영상 업로드 후 경과일")
    ax.grid(True)
    fig.tight_layout()
    return save_fig_to_png(fig, "bucket_box_")


def plot_bucket_hist(data: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(13, 6.8))
    sns.histplot(
        data=data,
        x="days_since_latest_video",
        hue="subscriber_bucket",
        bins=30,
        multiple="layer",
        kde=True,
        ax=ax,
    )
    ax.set_title("구독자 구간별 이탈 채널 days_since_latest_video 히스토그램")
    ax.set_xlabel("최근 영상 업로드 후 경과일")
    ax.set_ylabel("채널 수")
    ax.grid(True)
    fig.tight_layout()
    return save_fig_to_png(fig, "bucket_hist_")

# =========================================
# ReportLab helpers
# =========================================
def build_styles():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "KoreanTitle",
        parent=styles["Title"],
        fontName=PDF_FONT_BOLD,
        fontSize=18,
        leading=24,
        alignment=TA_LEFT,
        spaceAfter=8,
    )
    h2 = ParagraphStyle(
        "KoreanH2",
        parent=styles["Heading2"],
        fontName=PDF_FONT_BOLD,
        fontSize=13,
        leading=18,
        spaceBefore=8,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "KoreanBody",
        parent=styles["BodyText"],
        fontName=PDF_FONT,
        fontSize=10.5,
        leading=15,
        spaceAfter=3,
    )
    small = ParagraphStyle(
        "KoreanSmall",
        parent=styles["BodyText"],
        fontName=PDF_FONT,
        fontSize=9,
        leading=13,
        spaceAfter=2,
    )
    return title, h2, body, small


def add_kv_table(story, rows: list[tuple[str, str]], col_widths=(75 * mm, 80 * mm)):
    table_data = [[k, v] for k, v in rows]
    table = Table(table_data, colWidths=list(col_widths), hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), PDF_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F3F5")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 7 * mm))


def add_bucket_table(story, bucket_stats: pd.DataFrame):
    data = [["구독자 구간", "활동중", "이탈"]]
    for idx, row in bucket_stats.iterrows():
        data.append([idx, f"{int(row['활동중']):,}", f"{int(row['이탈']):,}"])

    table = Table(data, colWidths=[55 * mm, 40 * mm, 40 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), PDF_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DEE2E6")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 7 * mm))


def add_image_page(story, title: str, image_path: str, styles_tuple):
    _title, h2, _body, _small = styles_tuple
    story.append(PageBreak())
    story.append(Paragraph(title, h2))
    story.append(Spacer(1, 4 * mm))
    story.append(Image(image_path, width=250 * mm, height=140 * mm, kind="proportional"))

# =========================================
# Main analysis
# =========================================
def main() -> None:
    if not Path(INPUT_CSV).exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)
    df = normalize_numeric_columns(df)

    required_cols = [
        "channel_name",
        "created_date",
        "video_count",
        "subscriber_count",
        "days_since_latest_video",
        "is_churned",
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    original_count = len(df)
    df["days_since_created"] = df["created_date"].apply(days_since)

    # 1. Exclude Topic channels
    topic_mask = df["channel_name"].apply(is_topic_channel)
    topic_removed = int(topic_mask.sum())
    df = df[~topic_mask].copy()

    # 2. Exclude zero-video channels
    zero_video_mask = df["video_count"].fillna(0) == 0
    zero_video_removed = int(zero_video_mask.sum())
    df = df[~zero_video_mask].copy()

    # 3. Exclude new active channels
    new_active_mask = (
        df["days_since_created"].notna()
        & (df["days_since_created"] <= CHURN_THRESHOLD)
        & (df["is_churned"] == 0)
    )
    new_active_removed = int(new_active_mask.sum())
    df = df[~new_active_mask].copy()

    final_count = len(df)
    active_count = int((df["is_churned"] == 0).sum())
    churn_count = int((df["is_churned"] == 1).sum())
    unknown_count = int(df["is_churned"].isna().sum())

    bucket_order = ["1~20만", "20~40만", "40~60만", "60~80만", "80~100만", "100만 이상"]
    df["subscriber_bucket"] = df["subscriber_count"].apply(subscriber_bucket)

    bucket_stats = (
        df[df["subscriber_bucket"].isin(bucket_order)]
        .groupby(["subscriber_bucket", "is_churned"])
        .size()
        .unstack(fill_value=0)
        .reindex(bucket_order, fill_value=0)
    )
    if 0.0 not in bucket_stats.columns:
        bucket_stats[0.0] = 0
    if 1.0 not in bucket_stats.columns:
        bucket_stats[1.0] = 0
    bucket_stats = bucket_stats[[0.0, 1.0]]
    bucket_stats.columns = ["활동중", "이탈"]

    churn_df = df[df["is_churned"] == 1].copy()
    churn_df = churn_df[churn_df["days_since_latest_video"].notna()].copy()

    image_paths: list[str] = []
    if len(churn_df) > 0:
        image_paths.append(plot_hist_boxplot(churn_df, "days_since_latest_video", "이탈 채널 days_since_latest_video 분포"))
        image_paths.append(plot_bucket_boxplot(churn_df, bucket_order))
        image_paths.append(plot_bucket_hist(churn_df))

    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=landscape(A4),
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="YouTube 채널 이탈 통계 리포트",
        author="ChatGPT",
    )

    title, h2, body, small = build_styles()
    styles_tuple = (title, h2, body, small)
    story = []

    story.append(Paragraph("YouTube 채널 이탈 통계 요약", title))
    story.append(Paragraph(f"입력 파일: {INPUT_CSV}", small))
    story.append(Paragraph(f"출력 파일: {OUTPUT_PDF}", small))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("필터링 조건", h2))
    filter_rows = [
        ("1", "전체 채널에서 Topic 채널 제외"),
        ("2", "영상이 없는 채널 제외"),
        ("3", "생성 6개월 이하이면서 활동중인 채널 제외"),
    ]
    add_kv_table(story, filter_rows, col_widths=(15 * mm, 145 * mm))

    story.append(Paragraph("필터링 결과", h2))
    add_kv_table(
        story,
        [
            ("원본 전체 채널 수", f"{original_count:,}"),
            ("Topic 채널 제외 수", f"{topic_removed:,}"),
            ("영상 없는 채널 제외 수", f"{zero_video_removed:,}"),
            ("신규 활동 채널 제외 수", f"{new_active_removed:,}"),
            ("최종 분석 대상 채널 수", f"{final_count:,}"),
        ],
    )

    story.append(Paragraph("활동 상태", h2))
    add_kv_table(
        story,
        [
            ("활동중 채널 수", f"{active_count:,}"),
            ("이탈 채널 수", f"{churn_count:,}"),
            ("판정 불가 채널 수", f"{unknown_count:,}"),
        ],
    )

    story.append(Paragraph("구독자 구간별 활동중/이탈 채널 수", h2))
    add_bucket_table(story, bucket_stats)

    if len(image_paths) > 0:
        add_image_page(story, "이탈 채널 days_since_latest_video 분포", image_paths[0], styles_tuple)
        add_image_page(story, "구독자 구간별 이탈 채널 박스플롯", image_paths[1], styles_tuple)
        add_image_page(story, "구독자 구간별 이탈 채널 히스토그램", image_paths[2], styles_tuple)
    else:
        story.append(Paragraph("이탈 채널 데이터가 없어 분포 그래프를 생성하지 않았습니다.", body))

    doc.build(story)

    for path in image_paths:
        try:
            os.remove(path)
        except OSError:
            pass

    print(f"PDF 저장 완료: {OUTPUT_PDF}")
    print(f"최종 분석 대상 채널 수: {final_count:,}")
    print(f"활동중: {active_count:,} / 이탈: {churn_count:,} / 판정 불가: {unknown_count:,}")
    print(f"PDF text font: {PDF_FONT} (ReportLab CID font)")


if __name__ == "__main__":
    main()
