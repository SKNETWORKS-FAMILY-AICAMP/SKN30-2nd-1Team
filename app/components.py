"""튜브어때 Streamlit 공용 컴포넌트.

화면별 페이지에서 import 하여 사용한다.
"""

from __future__ import annotations

import base64
import io
import json
import os
import socket
import urllib.request
from html import escape

import streamlit as st

from styles import DATA_SNAPSHOT_DATE


def _detect_app_url() -> str | None:
    """HOST_IP 환경변수 우선, 없으면 ngrok, 없으면 로컬 IP URL."""
    host_ip = os.environ.get("HOST_IP")
    if host_ip:
        port = os.environ.get("HOST_PORT", "18080")
        return f"{host_ip}:{port}"
    try:
        with urllib.request.urlopen(
            "http://localhost:4040/api/tunnels", timeout=0.4
        ) as resp:
            tunnels = json.loads(resp.read()).get("tunnels", [])
            https = next((t for t in tunnels if t.get("proto") == "https"), None)
            if https:
                return https.get("public_url")
            if tunnels:
                return tunnels[0].get("public_url")
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        port = os.environ.get("STREAMLIT_SERVER_PORT", "8501")
        return f"http://{ip}:{port}"
    except Exception:
        return None


def _generate_qr_b64(url: str) -> str:
    import qrcode
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


@st.dialog("📱 QR 공유")
def _qr_dialog() -> None:
    detected = _detect_app_url() or ""
    url = st.text_input(
        "공유할 URL",
        value=detected,
        help="ngrok이 켜져있으면 public URL을, 아니면 같은 와이파이용 로컬 IP를 자동 감지합니다.",
    )
    if not url:
        st.info("URL을 입력하면 QR 코드가 생성됩니다.")
        return
    try:
        qr_b64 = _generate_qr_b64(url)
    except Exception as e:
        st.error(f"QR 생성 실패: {e}")
        return
    st.html(
        f'<div style="text-align:center; padding:14px 0;">'
        f'<img src="data:image/png;base64,{qr_b64}" '
        f'style="width:260px; height:260px; image-rendering:pixelated; '
        f'border:1px solid #E5E7EB; border-radius:14px; background:white; padding:12px;" />'
        f'</div>'
    )
    st.caption("📷 휴대폰 카메라로 스캔하거나 URL을 복사해 공유하세요.")


def render_sidebar(active: str = "dashboard") -> None:
    with st.sidebar:
        st.markdown(
            """
            <a href="/" target="_self" class="tb-logo-link">
                <div style="padding: 22px 12px 10px 12px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div style="width: 32px; height: 32px; border-radius: 9px;
                                    background: linear-gradient(135deg, #6366F1, #8B5CF6);
                                    display: flex; align-items: center; justify-content: center;
                                    color: white; font-weight: 700;">🛟</div>
                        <div>
                            <div style="color: white; font-weight: 700; font-size: 0.98rem;">튜브어때</div>
                            <div style="color: #64748B; font-size: 0.72rem;">Creator Credit System</div>
                        </div>
                    </div>
                </div>
            </a>
            """,
            unsafe_allow_html=True,
        )

        if st.button("📱 QR 공유하기", key="sb_qr_share", use_container_width=True):
            _qr_dialog()

        st.markdown("<hr style='margin: 16px 0 30px;'/>", unsafe_allow_html=True)

        # st.page_link("pages/0_대시보드.py", label="대시보드", icon="🏠")
        st.page_link("pages/1_채널_조회.py", label="채널 조회", icon="🔍")
        st.page_link("pages/3_광고주_추천.py", label="광고주 추천", icon="⭐")
        st.page_link("pages/2_인사이트.py", label="인사이트", icon="📊")


        # st.markdown(
        #     f"""
        #     <div class="tb-snapshot-wrap">
        #         <div style="display:flex; justify-content: space-between;
        #                     background: #1E2493B; border-radius: 10px; padding: 12px 14px;
        #                     color: #94A3B8; font-size: 0.74rem; line-height: 1.45;margin-top:50px">
        #             <strong style="color: #E2E8F0;">데이터 스냅샷</strong>
        #             <span>{DATA_SNAPSHOT_DATE} 기준</span>
        #         </div>
        #     </div>
        #     """,
        #     unsafe_allow_html=True,
        # )


def page_header(title: str, subtitle: str, right: str | None = None) -> None:
    cols = st.columns([6, 2]) if right else (st.container(),)
    if right:
        with cols[0]:
            st.markdown(f"<div class='tb-page-title'>{escape(title)}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='tb-page-sub'>{escape(subtitle)}</div>", unsafe_allow_html=True)
        with cols[1]:
            st.markdown(
                f"""
                <div style="display:flex; justify-content:flex-end; align-items:center;
                            height: 100%; padding-top: 6px;">
                  <div style="background:white; border:1px solid #E5E7EB; border-radius:10px;
                              padding:8px 14px; font-size:0.82rem; color:#475569;">
                    {escape(right)}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(f"<div class='tb-page-title'>{escape(title)}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='tb-page-sub'>{escape(subtitle)}</div>", unsafe_allow_html=True)


def kpi_card(label: str, value: str, unit: str, delta: str, tone: str = "neutral") -> None:
    tone_class = {
        "positive": "positive",
        "danger": "danger",
        "warning": "warning",
    }.get(tone, "")
    st.markdown(
        f"""
        <div class="tb-card">
            <div class="tb-kpi-label">{escape(label)}</div>
            <div class="tb-kpi-value">{escape(value)}<span style="font-size:1rem; font-weight:500; color:#94A3B8; margin-left:4px;">{escape(unit)}</span></div>
            <div class="tb-kpi-delta {tone_class}">{escape(delta)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def grade_badge_html(grade: str) -> str:
    return f"<span class='tb-grade tb-grade-{grade}'>{grade}</span>"


def chip(label: str, kind: str = "neutral") -> str:
    return f"<span class='tb-chip tb-chip-{kind}'>{escape(label)}</span>"


def disclaimer_footer() -> None:
    st.markdown(
        f"""
        <div class="tb-footer">
            📌 본 결과는 <strong>{DATA_SNAPSHOT_DATE}</strong> 기준 사전 수집 스냅샷 데이터를 활용한
            통계적 추정치이며, 광고 의사결정의 <strong>참고 자료</strong>로만 사용해 주세요.
            크리에이터 개인에 대한 평가나 제재 목적이 아닙니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


_card_counter = 0


def card(title: str | None = None, subtitle: str | None = None):
    """st.container 기반 카드 래퍼.

    `with card("제목", "부제"):` 형태로 사용한다.
    title과 subtitle은 한 줄에서 좌/우 양끝 정렬로 렌더된다.

    각 카드에 `tb-card-{N}` key를 부여해 Streamlit이 자동 생성하는
    `st-key-tb-card-{N}` class로 styles.py에서 안정적으로 타겟한다.
    (Streamlit 1.50부터 border=True 컨테이너에 별도 testid가 없어 emotion 해시
    class에 의존해야 하는 문제를 회피.)
    """
    global _card_counter
    _card_counter += 1
    container = st.container(key=f"tb-card-{_card_counter}")
    if title or subtitle:
        title_html = (
            f"<div class='tb-card-title'>{escape(title)}</div>" if title else "<div></div>"
        )
        subtitle_html = (
            f"<div class='tb-card-sub'>{escape(subtitle)}</div>" if subtitle else ""
        )
        container.markdown(
            f"<div class='tb-card-header'>{title_html}{subtitle_html}</div>",
            unsafe_allow_html=True,
        )
    return container
