"""
frontend/app.py
────────────────────────────────────────────────────────────────────────────
[팀원 A] 오토코어 AI 보안 게이트웨이 — Streamlit 프론트엔드

실행 방법:
    cd frontend
    pip install -r requirements.txt
    streamlit run app.py

백엔드 통신: http://localhost:8000  (팀원 C의 FastAPI 서버)
보안 모듈  : 팀원 B의 security_core.py가 백엔드 /chat에 통합된 상태
────────────────────────────────────────────────────────────────────────────
"""

import os
import html
import time
import streamlit as st
import requests
import pandas as pd
from typing import Optional

# ── 상수 ─────────────────────────────────────────────────────────────────
API_URL = os.getenv("API_URL", "http://api:8000")

# ══════════════════════════════════════════════════════════════════════════
#  페이지 설정 (반드시 최상단, 다른 st 호출 전에 위치)
# ══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AutoCore AI Security Gateway",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ══════════════════════════════════════════════════════════════════════════
#  커스텀 CSS — 프리미엄 다크 테마
# ══════════════════════════════════════════════════════════════════════════
def inject_css() -> None:
    st.markdown("""
    <style>
    /* ── 전역 배경 ── */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #060b18 0%, #0d1b2e 50%, #071120 100%);
        min-height: 100vh;
    }
    [data-testid="stHeader"] { background: transparent; }

    /* ── 사이드바 ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b1628 0%, #0f2040 100%);
        border-right: 1px solid rgba(0, 180, 255, 0.15);
    }
    [data-testid="stSidebar"] * { color: #c8d8f0 !important; }

    /* ── 로그인 카드 ── */
    .login-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(0, 180, 255, 0.2);
        border-radius: 20px;
        padding: 2.5rem 3rem;
        backdrop-filter: blur(16px);
        box-shadow: 0 8px 40px rgba(0,0,0,0.5),
                    0 0 60px rgba(0,100,220,0.08);
        max-width: 480px;
        margin: 0 auto;
    }
    .brand-logo {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00b4ff, #0066ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
        margin-bottom: 0.2rem;
    }
    .brand-sub {
        color: #5580a8;
        font-size: 0.82rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 2rem;
    }

    /* ── 섹션 헤더 ── */
    .section-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #e8f0ff;
        margin-bottom: 0.4rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid rgba(0,180,255,0.15);
    }

    /* ── 메트릭 카드 ── */
    .metric-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(0, 180, 255, 0.15);
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        text-align: center;
        transition: border-color 0.3s;
    }
    .metric-card:hover { border-color: rgba(0,180,255,0.4); }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
    }
    .metric-label {
        font-size: 0.78rem;
        color: #7090b0;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-top: 0.3rem;
    }
    .metric-blocked  { color: #ff5c7a; }
    .metric-masked   { color: #f0b429; }
    .metric-allowed  { color: #22d6a5; }
    .metric-total    { color: #00b4ff; }

    /* ── 보안 차단 배너 ── */
    .block-banner {
        background: rgba(255, 30, 60, 0.1);
        border: 1px solid rgba(255, 60, 80, 0.4);
        border-left: 4px solid #ff3c50;
        border-radius: 10px;
        padding: 0.9rem 1.2rem;
        margin: 0.5rem 0;
        color: #ff8095;
        font-size: 0.92rem;
    }

    /* ── 채팅 말풍선 ── */
    .bubble-row-user {
        display: flex;
        justify-content: flex-end;
        margin: 0.1rem 0 0.6rem;
    }
    .bubble-row-assistant {
        display: flex;
        justify-content: flex-start;
        margin: 0.1rem 0 0.6rem;
    }
    .chat-bubble-user {
        background: linear-gradient(135deg, rgba(0,90,210,0.45), rgba(0,140,255,0.25));
        border: 1px solid rgba(60,160,255,0.35);
        border-radius: 18px 4px 18px 18px;
        padding: 0.65rem 1.05rem;
        max-width: 72%;
        color: #cce4ff;
        font-size: 0.92rem;
        line-height: 1.55;
        word-break: break-word;
    }
    .chat-bubble-assistant {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(200,220,255,0.12);
        border-radius: 4px 18px 18px 18px;
        padding: 0.65rem 1.05rem;
        max-width: 72%;
        color: #d8eaff;
        font-size: 0.92rem;
        line-height: 1.55;
        word-break: break-word;
    }

    /* 채팅 입력창 텍스트 색상 → Streamlit 순정 테마 엔진에 위임 (커스텀 CSS 없음) */

    /* ── 상태 배지 ── */
    .badge {
        display: inline-block;
        padding: 0.2rem 0.7rem;
        border-radius: 99px;
        font-size: 0.73rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .badge-blocked { background: rgba(255,60,80,0.2); color:#ff7088; border:1px solid rgba(255,60,80,0.3); }
    .badge-masked  { background: rgba(240,180,41,0.2); color:#f0c050; border:1px solid rgba(240,180,41,0.3); }
    .badge-allowed { background: rgba(34,214,165,0.2); color:#22d6a5; border:1px solid rgba(34,214,165,0.3); }

    /* ── 버튼 ── */
    .stButton > button {
        background: linear-gradient(90deg, #0066ff 0%, #00b4ff 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.55rem 1.5rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.3px;
        transition: opacity 0.2s;
    }
    .stButton > button:hover { opacity: 0.85; }

    /* ── 입력 필드 ── */
    .stTextInput input, .stTextInput input:focus {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(0,180,255,0.25) !important;
        border-radius: 10px !important;
        color: #d8eaff !important;
    }
    label { color: #7a9cc0 !important; font-size: 0.84rem !important; }

    /* ── 데이터 프레임 ── */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(0,180,255,0.12);
        border-radius: 12px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
#  [제약사항 1] 세션 상태 초기화 — 필수 Key 5개
# ══════════════════════════════════════════════════════════════════════════
def init_session_state() -> None:
    """
    Streamlit 리렌더링 시 데이터 유실 방지.
    최상단에서 호출하여 필수 Key가 항상 존재하도록 보장.
    """
    _defaults: dict = {
        "logged_in":    False,   # 로그인 여부 (bool)
        "role":         "",      # 권한: 'user' | 'admin'
        "employee_num": "",      # 사번
        "name":         "",      # 임직원 이름
        "messages":     [],      # 채팅 히스토리 [{"role": ..., "content": ...}]
        "token":        "",      # JWT Bearer 토큰
        "current_page": "chat",  # Admin 전용 페이지 라우팅
    }
    for key, value in _defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ══════════════════════════════════════════════════════════════════════════
#  API 통신 함수 (타입 힌트 강제)
# ══════════════════════════════════════════════════════════════════════════

def api_login(employee_num: str, password: str) -> Optional[dict]:
    """
    POST /login 호출.
    """
    target_url = f"{API_URL}/login"
    try:
        resp = requests.post(
            target_url,
            data={"username": employee_num, "password": password},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json()
        
        # 디버깅 로그 노출 (핵심 방어)
        st.error(f"서버 응답 오류 [{resp.status_code}]: {resp.text}")
        return None
    except requests.exceptions.ConnectionError as e:
        st.error(f"서버 연결 실패! 시도한 주소: {target_url} | 에러 내용: {e}")
        return None
    except requests.exceptions.Timeout as e:
        st.error(f"서버 응답 초과! 시도한 주소: {target_url} | 에러 내용: {e}")
        return None


def api_chat(prompt: str, token: str) -> dict:
    """
    POST /chat 호출. 403 Forbidden(보안 차단) 포함 예외 처리.

    Returns:
        dict:
            성공: {"ok": True,  "response": str}
            차단: {"ok": False, "blocked": True,  "detail": str}
            오류: {"ok": False, "blocked": False, "detail": str}
    """
    try:
        target_url = f"{API_URL}/chat"
        resp = requests.post(
            target_url,
            json={"prompt": prompt},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if resp.status_code == 200:
            return {"ok": True, "response": resp.json()["response"]}
        elif resp.status_code == 403:
            detail = resp.json().get("detail", "보안 정책 위반")
            return {"ok": False, "blocked": True, "detail": detail}
        elif resp.status_code == 401:
            return {"ok": False, "blocked": False, "detail": "인증이 만료되었습니다. 다시 로그인해주세요."}
        else:
            return {"ok": False, "blocked": False, "detail": f"서버 오류 (HTTP {resp.status_code})"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "blocked": False, "detail": f"백엔드 서버에 연결할 수 없습니다. ({target_url})"}
    except requests.exceptions.Timeout:
        return {"ok": False, "blocked": False, "detail": "응답 시간이 초과되었습니다."}


def api_admin_logs(token: str) -> list[dict]:
    """
    GET /admin/logs 호출 (관리자 전용).

    Returns:
        list[dict]: 보안 로그 항목 리스트 | [] (실패)
    """
    try:
        target_url = f"{API_URL}/admin/logs"
        resp = requests.get(
            target_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json().get("logs", [])
        return []
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return []


# ══════════════════════════════════════════════════════════════════════════
#  기능 1: 로그인 뷰
# ══════════════════════════════════════════════════════════════════════════
def render_login_view() -> None:
    """사번·비밀번호 로그인 폼 렌더링. 성공 시 세션에 토큰·권한 저장."""

    # 화면 중앙 배치
    col_l, col_c, col_r = st.columns([1, 1.4, 1])
    with col_c:
        st.markdown("""
        <div class="login-card">
            <div class="brand-logo">🛡️ AutoCore</div>
            <div class="brand-sub">AI Security Gateway</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            st.markdown(
                "<p style='color:#7a9cc0;font-size:0.85rem;margin-bottom:1rem;'>"
                "오토코어 임직원 인증 시스템입니다.<br>사번과 비밀번호를 입력하세요.</p>",
                unsafe_allow_html=True,
            )
            employee_num = st.text_input(
                "사번 (Employee Number)",
                placeholder="예) EMP-001 또는 ADMIN-001",
                key="login_emp",
            )
            password = st.text_input(
                "비밀번호",
                type="password",
                placeholder="비밀번호 입력",
                key="login_pw",
            )

            submitted = st.form_submit_button("🔐 로그인", use_container_width=True)

            if submitted:
                if not employee_num or not password:
                    st.error("사번과 비밀번호를 모두 입력해주세요.")
                else:
                    with st.spinner("인증 중..."):
                        result = api_login(employee_num, password)

                    if result:
                        st.session_state.logged_in    = True
                        st.session_state.token         = result["access_token"]
                        st.session_state.role          = result["role"]
                        st.session_state.employee_num  = employee_num
                        st.session_state.name          = result["name"]
                        st.session_state.messages      = []
                        st.rerun()
                    else:
                        st.error("❌ 사번 또는 비밀번호가 올바르지 않습니다.")

        # 테스트 계정 안내
        with st.expander("🔑 테스트 계정 안내", expanded=False):
            st.markdown("""
            | 사번 | 비밀번호 | 권한 |
            |------|----------|------|
            | `EMP-001` | `pass1234` | 일반 임직원 |
            | `EMP-002` | `pass5678` | 일반 임직원 |
            | `ADMIN-001` | `adminpass` | 보안 관리자 |
            """)


# ══════════════════════════════════════════════════════════════════════════
#  기능 2: 사이드바 (내비게이션 라우팅)
# ══════════════════════════════════════════════════════════════════════════
def render_sidebar() -> None:
    """로그인 후 사이드바 렌더링. Admin이면 메뉴 탭 추가."""

    with st.sidebar:
        # 브랜드 헤더
        st.markdown("""
        <div style="padding:1rem 0 0.5rem;">
            <div style="font-size:1.3rem;font-weight:800;
                        background:linear-gradient(90deg,#00b4ff,#0066ff);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                🛡️ AutoCore Gateway
            </div>
            <div style="font-size:0.72rem;color:#334a66;letter-spacing:1.5px;
                        text-transform:uppercase;margin-top:0.1rem;">
                AI Security Platform
            </div>
        </div>
        <hr style="border-color:rgba(0,180,255,0.1);margin:0.8rem 0;">
        """, unsafe_allow_html=True)

        # 사용자 정보 카드
        role_badge_color = "#00b4ff" if st.session_state.role == "admin" else "#22d6a5"
        role_label       = "보안 관리자" if st.session_state.role == "admin" else "임직원"
        st.markdown(f"""
        <div style="background:rgba(0,100,220,0.08);border:1px solid rgba(0,180,255,0.12);
                    border-radius:10px;padding:0.8rem 1rem;margin-bottom:1rem;">
            <div style="font-size:0.95rem;font-weight:700;color:#d0e8ff;">
                👤 {st.session_state.name}
            </div>
            <div style="font-size:0.75rem;color:#507aa0;margin-top:0.2rem;">
                {st.session_state.employee_num}
            </div>
            <div style="margin-top:0.5rem;">
                <span style="background:rgba(0,180,255,0.1);border:1px solid {role_badge_color}33;
                             color:{role_badge_color};border-radius:99px;
                             padding:0.15rem 0.7rem;font-size:0.72rem;font-weight:700;">
                    {role_label}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Admin 전용 메뉴
        if st.session_state.role == "admin":
            st.markdown(
                "<div style='font-size:0.75rem;color:#506070;letter-spacing:1px;"
                "text-transform:uppercase;margin-bottom:0.5rem;'>메뉴</div>",
                unsafe_allow_html=True,
            )
            page = st.radio(
                "페이지 선택",
                options=["chat", "dashboard"],
                format_func=lambda x: "💬 AI 챗봇" if x == "chat" else "🛡️ 보안 대시보드",
                key="page_radio",
                label_visibility="collapsed",
            )
            st.session_state.current_page = page
            st.markdown(
                "<hr style='border-color:rgba(0,180,255,0.1);margin:1rem 0;'>",
                unsafe_allow_html=True,
            )

        # 로그아웃 버튼
        if st.button("🚪 로그아웃", use_container_width=True, key="logout_btn"):
            for key in ["logged_in", "role", "employee_num", "name",
                        "messages", "token", "current_page"]:
                st.session_state[key] = (
                    False if key == "logged_in"
                    else [] if key == "messages"
                    else "chat" if key == "current_page"
                    else ""
                )
            st.rerun()

        # 백엔드 연결 상태 표시
        st.markdown(
            "<hr style='border-color:rgba(0,180,255,0.08);margin:1rem 0 0.5rem;'>",
            unsafe_allow_html=True,
        )
        try:
            r = requests.get(f"{API_URL}/health", timeout=2)
            if r.status_code == 200:
                st.markdown(
                    "<div style='font-size:0.75rem;color:#22d6a5;'>"
                    "● 백엔드 연결됨</div>",
                    unsafe_allow_html=True,
                )
        except Exception:
            st.markdown(
                "<div style='font-size:0.75rem;color:#ff5c7a;'>"
                "● 백엔드 연결 안 됨</div>",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════
#  기능 3: AI 챗봇 뷰
# ══════════════════════════════════════════════════════════════════════════
def render_chat_view() -> None:
    """
    [제약사항 2] st.chat_message() + st.chat_input() 만 사용.
    403 차단 응답은 붉은색 경고 배너로 렌더링.
    """
    # 헤더
    st.markdown("""
    <div class="section-title">💬 AI 어시스턴트</div>
    <p style="color:#506880;font-size:0.85rem;margin-bottom:1.2rem;">
        오토코어 AI 보안 게이트웨이를 통해 안전하게 질문하세요.<br>
        기밀 데이터는 자동으로 보호됩니다.
    </p>
    """, unsafe_allow_html=True)

    # 이전 대화 렌더링 (말풍선 스타일)
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                safe_content = html.escape(msg["content"])
                st.markdown(
                    f'<div class="bubble-row-user">'
                    f'<div class="chat-bubble-user">{safe_content}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        elif msg["role"] == "system_block":
            with st.chat_message("assistant", avatar="🚨"):
                safe_content = html.escape(msg["content"])
                st.markdown(
                    f'<div class="block-banner">🚨 보안 정책에 의해 차단되었습니다: {safe_content}</div>',
                    unsafe_allow_html=True,
                )
        else:
            with st.chat_message("assistant", avatar="🤖"):
                safe_content = html.escape(msg["content"])
                st.markdown(
                    f'<div class="bubble-row-assistant">'
                    f'<div class="chat-bubble-assistant">{safe_content}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # 채팅 입력 (st.chat_input 제약사항 준수)
    if prompt := st.chat_input("질문을 입력하세요... (예: 다음 텍스트를 요약해줘 [대상: EMP-123, 내용: ...])"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            safe_prompt = html.escape(prompt)
            st.markdown(
                f'<div class="bubble-row-user">'
                f'<div class="chat-bubble-user">{safe_prompt}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("AI 보안 게이트웨이 처리 중..."):
                result = api_chat(prompt, st.session_state.token)
            if result["ok"]:
                response_text = result["response"]
                safe_response = html.escape(response_text)
                st.markdown(
                    f'<div class="bubble-row-assistant">'
                    f'<div class="chat-bubble-assistant">{safe_response}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            elif result.get("blocked"):
                detail = result["detail"]
                safe_detail = html.escape(detail)
                st.markdown(
                    f'<div class="block-banner">🚨 보안 정책에 의해 차단되었습니다: {safe_detail}</div>',
                    unsafe_allow_html=True,
                )
                st.session_state.messages.append({"role": "system_block", "content": detail})
            else:
                st.error(f"⚠️ {result['detail']}")


# ══════════════════════════════════════════════════════════════════════════
#  기능 4: 보안 대시보드 뷰 (Admin 전용)
# ══════════════════════════════════════════════════════════════════════════
def render_dashboard_view() -> None:
    """
    관리자 전용. GET /admin/logs 데이터를:
    1. st.dataframe()으로 전체 표 출력
    2. st.bar_chart()로 차단 사유별 통계 시각화
    """
    st.markdown("""
    <div class="section-title">🛡️ 보안 이벤트 대시보드</div>
    <p style="color:#506880;font-size:0.85rem;margin-bottom:1.5rem;">
        AI 보안 게이트웨이에서 탐지된 실시간 보안 이벤트 현황입니다.
    </p>
    """, unsafe_allow_html=True)

    # --- 교체할 안전한 다운로드 버튼 로직 ---
    try:
        # 1. 프론트엔드 서버가 내부망을 통해 백엔드에서 데이터를 먼저 가져옴
        export_res = requests.get(f"{API_URL}/admin/export-csv", timeout=10)
        
        # 2. 성공적으로 가져왔다면 브라우저에 다운로드 버튼 표시
        if export_res.status_code == 200:
            st.download_button(
                label="📥 테스트 데이터 전체 다운로드 (CSV)",
                data=export_res.content,
                file_name="autocore_logs.csv",
                mime="text/csv",
                type="primary"
            )
        else:
            st.warning("CSV 데이터를 불러올 수 없습니다.")
    except Exception as e:
        st.error(f"다운로드 서버 연결 오류: {e}")

    # --- DB 로그 초기화 (테스트용) ---
    with st.expander("⚠️ 위험 구역: DB 초기화 (테스트용)"):
        st.warning("주의: 모든 보안 로그가 영구적으로 삭제됩니다. 반드시 CSV를 먼저 다운로드하세요.")
        if st.button("🚨 모든 로그 삭제", type="primary"):
            try:
                res = requests.delete(
                    f"{API_URL}/admin/clear-logs",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    timeout=10,
                )
                if res.status_code == 200:
                    st.toast("✅ 로그가 성공적으로 초기화되었습니다!", icon="🗑️")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("초기화 실패: 백엔드 서버 오류")
            except Exception as e:
                st.error(f"서버 연결 오류: {e}")

    with st.spinner("보안 로그 불러오는 중..."):
        logs = api_admin_logs(st.session_state.token)

    if not logs:
        st.info("표시할 보안 로그가 없습니다. 채팅을 먼저 사용해 보세요.")
        return

    df = pd.DataFrame(logs)

    # ── 발생 시각 기준 최신순(내림차순) 정렬 ────────────────────────────────
    df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)

    # 원본 데이터를 보존하면서 깔끔한 필터용 컬럼(threat_category) 생성
    if not df.empty and 'detected_threat' in df.columns:
        df['threat_category'] = df['detected_threat'].apply(
            lambda x: str(x).split(' (')[0].strip() if pd.notnull(x) and str(x).strip() != "" else x
        )

    # ── 요약 메트릭 카드 ────────────────────────────────────────────────
    total   = len(df)
    blocked = int((df["status"] == "BLOCKED").sum())
    masked  = int((df["status"] == "MASKED").sum())
    allowed = int((df["status"] == "ALLOWED").sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value metric-total">{total}</div>
            <div class="metric-label">전체 이벤트</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value metric-blocked">{blocked}</div>
            <div class="metric-label">🚫 차단</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value metric-masked">{masked}</div>
            <div class="metric-label">🔒 마스킹</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value metric-allowed">{allowed}</div>
            <div class="metric-label">✅ 허용</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── multiselect 필터 ───────────────────────────────────────────────────────
    with st.expander("🔍 필터 옵션", expanded=True):
        fcol1, fcol2 = st.columns(2)
        with fcol1:
            selected_actions = st.multiselect(
                "행위 유형 (action)",
                options=sorted(df["action"].dropna().unique().tolist()),
                default=[],
                placeholder="전체 표시",
                key="filter_action",
            )
        with fcol2:
            selected_threats = st.multiselect(
                "탐지 위협 (카테고리)",
                options=sorted(df["threat_category"].dropna().unique().tolist()),
                default=[],
                placeholder="전체 표시",
                key="filter_threat",
            )

    # 필터 적용
    filtered_logs = logs
    if selected_actions:
        filtered_logs = [l for l in filtered_logs if l.get("action") in selected_actions]
    if selected_threats:
        filtered_logs = [l for l in filtered_logs if str(l.get("detected_threat", "")).split(' (')[0].strip() in selected_threats]
    
    # 최신순 정렬
    filtered_logs = sorted(filtered_logs, key=lambda x: x.get("timestamp", ""), reverse=True)
    f_total = len(filtered_logs)

    if selected_actions or selected_threats:
        st.markdown(
            f"<p style='color:#7090b0;font-size:0.82rem;margin-bottom:0;'>"
            f" 필터 적용: {total}건 → <b>{f_total}건</b> 표시</p>",
            unsafe_allow_html=True,
        )

    # ══════════════════════════════════════════════════════════════════════
    #  [핵심] 순수 문자열 리스트 수작업 생성 — DataFrame/PyArrow 직렬화 에러 원천 차단
    # ══════════════════════════════════════════════════════════════════════
    clean_data = []
    for log in filtered_logs:
        clean_data.append({
            "로그 ID": str(log.get("log_id", "")),
            "발생 시각": str(log.get("timestamp", "")),
            "사번": str(log.get("employee_num", "")),
            "행위 유형": str(log.get("action", "")),
            "탐지 위협": str(log.get("detected_threat", "")),
            "처리 상태": str(log.get("status", ""))
        })

    # ── 탭: 이벤트 로그 / 상세 처리 결과 / 통계 차트 ──────────────────────────────
    tab_log, tab_detail, tab_chart = st.tabs(["📋 이벤트 로그", "🔍 상세 처리 결과", "📊 탐지 통계"])

    with tab_log:
        st.markdown(
            "<p style='color:#506880;font-size:0.82rem;margin-bottom:0.8rem;'>"
            f"필터된 {f_total}건 (모두 최신순 정렬)</p>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            pd.DataFrame(clean_data),
            use_container_width=True,
            hide_index=True,
            column_config={
                "처리 상태": st.column_config.Column(width="small"),
                "발생 시각": st.column_config.Column(width="medium"),
                "탐지 위협": st.column_config.Column(width="large"),
            },
        )

    with tab_detail:
        st.text("각 보안 이벤트의 마스킹 치환 상세 내역입니다. MASKED 이벤트를 펼쳐서 확인하세요.")
        for log in filtered_logs:
            log_id = str(log.get("log_id", ""))
            status_val = str(log.get("status", ""))
            emp = str(log.get("employee_num", ""))
            ts = str(log.get("timestamp", ""))

            icon = "🚫" if status_val == "BLOCKED" else "🔒" if status_val == "MASKED" else "✅"
            label = f"{icon} #{log_id}  |  {emp}  |  {status_val}  |  {ts}"

            with st.expander(label, expanded=False):
                safe_orig = html.escape(str(log.get("original_prompt", "") or ""))
                safe_masked = html.escape(str(log.get("masked_prompt", "") or ""))
                
                if safe_orig:
                    col_orig, col_mask = st.columns(2)
                    with col_orig:
                        st.text("▼ 원본 프롬프트")
                        st.markdown(
                            f"<div style='white-space: pre-wrap; word-break: break-word; background-color: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; font-family: monospace; line-height: 1.5;'>{safe_orig}</div>",
                            unsafe_allow_html=True
                        )
                    with col_mask:
                        st.text("▼ 전송 프롬프트 (마스킹)")
                        safe_masked_display = safe_masked if safe_masked else "(동일 — 기밀 미탐지)"
                        st.markdown(
                            f"<div style='white-space: pre-wrap; word-break: break-word; background-color: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; font-family: monospace; line-height: 1.5;'>{safe_masked_display}</div>",
                            unsafe_allow_html=True
                        )
                
                mapping_raw = log.get("mapping_info", "")
                if isinstance(mapping_raw, dict):
                    import json
                    safe_mapping = json.dumps(mapping_raw, ensure_ascii=False, indent=2)
                elif isinstance(mapping_raw, str) and mapping_raw.strip():
                    import json
                    try:
                        parsed = json.loads(mapping_raw)
                        safe_mapping = json.dumps(parsed, ensure_ascii=False, indent=2)
                    except (json.JSONDecodeError, TypeError):
                        safe_mapping = ""
                else:
                    safe_mapping = ""
                
                if safe_mapping:
                    st.text("🔐 마스킹 토큰 매핑 내역")
                    st.code(safe_mapping, language="json")
                else:
                    if status_val != "BLOCKED":
                        st.text("매핑 정보 없음 (기밀 데이터 미탐지)")

    with tab_chart:
        col_a, col_b = st.columns(2)
        chart_df = pd.DataFrame(clean_data)

        with col_a:
            st.markdown(
                "<p style='color:#7090b0;font-size:0.85rem;font-weight:600;"
                "margin-bottom:0.5rem;'>처리 상태별 건수</p>",
                unsafe_allow_html=True,
            )
            if not chart_df.empty:
                status_counts = chart_df["처리 상태"].value_counts().reset_index()
                status_counts.columns = ["처리 상태", "건수"]
                st.bar_chart(status_counts.set_index("처리 상태"), color="#00b4ff", use_container_width=True)

        with col_b:
            st.markdown(
                "<p style='color:#7090b0;font-size:0.85rem;font-weight:600;"
                "margin-bottom:0.5rem;'>사번별 행위 건수</p>",
                unsafe_allow_html=True,
            )
            if not chart_df.empty:
                emp_counts = chart_df["사번"].value_counts().reset_index()
                emp_counts.columns = ["사번", "건수"]
                st.bar_chart(emp_counts.set_index("사번"), color="#0066ff", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
#  메인 진입점 — 라우팅 제어
# ══════════════════════════════════════════════════════════════════════════
def main() -> None:
    init_session_state()   # [제약사항 1] 세션 최상단 초기화
    inject_css()           # 프리미엄 다크 테마 주입

    if not st.session_state.logged_in:
        # ── 비로그인: 로그인 화면 ────────────────────────────────────────
        # 상단 중앙 브랜드 타이틀
        st.markdown("""
        <div style="text-align:center;padding:2.5rem 0 1rem;">
            <div style="font-size:2.5rem;font-weight:900;
                        background:linear-gradient(90deg,#00b4ff 0%,#0066ff 100%);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                        letter-spacing:-1px;">
                AutoCore AI Security Gateway
            </div>
            <div style="color:#3a5878;font-size:0.88rem;letter-spacing:2px;
                        text-transform:uppercase;margin-top:0.4rem;">
                지능형 차세대 AI DLP 플랫폼
            </div>
        </div>
        """, unsafe_allow_html=True)
        render_login_view()

    else:
        # ── 로그인 완료: 사이드바 + 메인 화면 ──────────────────────────
        render_sidebar()

        if st.session_state.role == "admin":
            # Admin: current_page에 따라 챗봇 / 대시보드 전환
            if st.session_state.current_page == "dashboard":
                render_dashboard_view()
            else:
                render_chat_view()
        else:
            # 일반 User: 챗봇만 노출
            render_chat_view()


if __name__ == "__main__":
    main()
