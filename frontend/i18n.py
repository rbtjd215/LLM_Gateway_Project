"""
frontend/i18n.py
────────────────────────────────────────────────────────────────────────────
UI 다국어 지원용 텍스트 사전.
app.py에서 T(key) 함수로 호출하여 현재 언어에 맞는 문자열을 반환한다.
────────────────────────────────────────────────────────────────────────────
"""

TEXTS = {
    # ── 로그인 화면 ──────────────────────────────────────────────────────
    "login_subtitle": {
        "ko": "지능형 차세대 AI DLP 플랫폼",
        "en": "Intelligent Next-Gen AI DLP Platform",
    },
    "login_description": {
        "ko": "오토코어 임직원 인증 시스템입니다.<br>사번과 비밀번호를 입력하세요.",
        "en": "AutoCore Employee Authentication System.<br>Please enter your Employee ID and password.",
    },
    "login_emp_label": {
        "ko": "사번 (Employee Number)",
        "en": "Employee ID",
    },
    "login_emp_placeholder": {
        "ko": "예) EMP-001 또는 ADMIN-001",
        "en": "e.g. EMP-001 or ADMIN-001",
    },
    "login_pw_label": {
        "ko": "비밀번호",
        "en": "Password",
    },
    "login_pw_placeholder": {
        "ko": "비밀번호 입력",
        "en": "Enter password",
    },
    "login_button": {
        "ko": "🔐 로그인",
        "en": "🔐 Sign In",
    },
    "login_empty_error": {
        "ko": "사번과 비밀번호를 모두 입력해주세요.",
        "en": "Please enter both Employee ID and password.",
    },
    "login_spinner": {
        "ko": "인증 중...",
        "en": "Authenticating...",
    },
    "login_fail": {
        "ko": "❌ 사번 또는 비밀번호가 올바르지 않습니다.",
        "en": "❌ Invalid Employee ID or password.",
    },
    "login_test_title": {
        "ko": "🔑 테스트 계정 안내",
        "en": "🔑 Test Account Info",
    },
    "login_test_table": {
        "ko": """
            | 사번 | 비밀번호 | 권한 |
            |------|----------|------|
            | `EMP-001` | `pass1234` | 일반 임직원 |
            | `EMP-002` | `pass5678` | 일반 임직원 |
            | `ADMIN-001` | `adminpass` | 보안 관리자 |
            """,
        "en": """
            | Employee ID | Password | Role |
            |-------------|----------|------|
            | `EMP-001` | `pass1234` | User |
            | `EMP-002` | `pass5678` | User |
            | `ADMIN-001` | `adminpass` | Security Admin |
            """,
    },

    # ── 사이드바 ─────────────────────────────────────────────────────────
    "sidebar_role_admin": {
        "ko": "보안 관리자",
        "en": "Security Admin",
    },
    "sidebar_role_user": {
        "ko": "임직원",
        "en": "Employee",
    },
    "sidebar_menu_label": {
        "ko": "메뉴",
        "en": "MENU",
    },
    "sidebar_page_chat": {
        "ko": "💬 AI 챗봇",
        "en": "💬 AI Chatbot",
    },
    "sidebar_page_dashboard": {
        "ko": "🛡️ 보안 대시보드",
        "en": "🛡️ Security Dashboard",
    },
    "sidebar_logout": {
        "ko": "🚪 로그아웃",
        "en": "🚪 Sign Out",
    },
    "sidebar_backend_connected": {
        "ko": "● 백엔드 연결됨",
        "en": "● Backend Connected",
    },
    "sidebar_backend_disconnected": {
        "ko": "● 백엔드 연결 안 됨",
        "en": "● Backend Disconnected",
    },

    # ── 챗봇 화면 ────────────────────────────────────────────────────────
    "chat_title": {
        "ko": "💬 AI 어시스턴트",
        "en": "💬 AI Assistant",
    },
    "chat_description": {
        "ko": "오토코어 AI 보안 게이트웨이를 통해 안전하게 질문하세요.<br>기밀 데이터는 자동으로 보호됩니다.",
        "en": "Ask questions safely through the AutoCore AI Security Gateway.<br>Confidential data is automatically protected.",
    },
    "chat_input_placeholder": {
        "ko": "질문을 입력하세요... (예: 다음 텍스트를 요약해줘 [대상: EMP-123, 내용: ...])",
        "en": "Type your question... (e.g., Summarize the following text [Target: EMP-123, Content: ...])",
    },
    "chat_spinner": {
        "ko": "AI 보안 게이트웨이 처리 중...",
        "en": "Processing through AI Security Gateway...",
    },
    "chat_blocked_banner": {
        "ko": "🚨 보안 정책에 의해 차단되었습니다:",
        "en": "🚨 Blocked by security policy:",
    },

    # ── 대시보드 화면 ────────────────────────────────────────────────────
    "dash_title": {
        "ko": "🛡️ 보안 이벤트 대시보드",
        "en": "🛡️ Security Event Dashboard",
    },
    "dash_description": {
        "ko": "AI 보안 게이트웨이에서 탐지된 실시간 보안 이벤트 현황입니다.",
        "en": "Real-time security events detected by the AI Security Gateway.",
    },
    "dash_download_btn": {
        "ko": "📥 테스트 데이터 전체 다운로드 (CSV)",
        "en": "📥 Download All Test Data (CSV)",
    },
    "dash_download_fail": {
        "ko": "CSV 데이터를 불러올 수 없습니다.",
        "en": "Failed to load CSV data.",
    },
    "dash_download_error": {
        "ko": "다운로드 서버 연결 오류:",
        "en": "Download server connection error:",
    },
    "dash_danger_zone": {
        "ko": "⚠️ 위험 구역: DB 초기화 (테스트용)",
        "en": "⚠️ Danger Zone: Reset DB (For Testing)",
    },
    "dash_danger_warning": {
        "ko": "주의: 모든 보안 로그가 영구적으로 삭제됩니다. 반드시 CSV를 먼저 다운로드하세요.",
        "en": "Warning: All security logs will be permanently deleted. Please download CSV first.",
    },
    "dash_delete_btn": {
        "ko": "🚨 모든 로그 삭제",
        "en": "🚨 Delete All Logs",
    },
    "dash_delete_success": {
        "ko": "✅ 로그가 성공적으로 초기화되었습니다!",
        "en": "✅ Logs have been successfully cleared!",
    },
    "dash_delete_fail": {
        "ko": "초기화 실패: 백엔드 서버 오류",
        "en": "Reset failed: Backend server error",
    },
    "dash_loading": {
        "ko": "보안 로그 불러오는 중...",
        "en": "Loading security logs...",
    },
    "dash_no_logs": {
        "ko": "표시할 보안 로그가 없습니다. 채팅을 먼저 사용해 보세요.",
        "en": "No security logs to display. Try using the chatbot first.",
    },
    "dash_metric_total": {
        "ko": "전체 이벤트",
        "en": "TOTAL EVENTS",
    },
    "dash_metric_blocked": {
        "ko": "🚫 차단",
        "en": "🚫 BLOCKED",
    },
    "dash_metric_masked": {
        "ko": "🔒 마스킹",
        "en": "🔒 MASKED",
    },
    "dash_metric_allowed": {
        "ko": "✅ 허용",
        "en": "✅ ALLOWED",
    },
    "dash_filter_title": {
        "ko": "🔍 필터 옵션",
        "en": "🔍 Filter Options",
    },
    "dash_filter_action": {
        "ko": "행위 유형 (action)",
        "en": "Action Type",
    },
    "dash_filter_threat": {
        "ko": "탐지 위협 (카테고리)",
        "en": "Detected Threat (Category)",
    },
    "dash_filter_placeholder": {
        "ko": "전체 표시",
        "en": "Show All",
    },
    "dash_filter_applied": {
        "ko": "필터 적용:",
        "en": "Filter applied:",
    },
    "dash_filter_shown": {
        "ko": "건 표시",
        "en": "shown",
    },

    # ── 대시보드 테이블 헤더 ─────────────────────────────────────────────
    "col_log_id": {
        "ko": "로그 ID",
        "en": "Log ID",
    },
    "col_timestamp": {
        "ko": "발생 시각",
        "en": "Timestamp",
    },
    "col_employee": {
        "ko": "사번",
        "en": "Employee ID",
    },
    "col_action": {
        "ko": "행위 유형",
        "en": "Action Type",
    },
    "col_threat": {
        "ko": "탐지 위협",
        "en": "Detected Threat",
    },
    "col_status": {
        "ko": "처리 상태",
        "en": "Status",
    },

    # ── 대시보드 탭 ──────────────────────────────────────────────────────
    "tab_event_log": {
        "ko": "📋 이벤트 로그",
        "en": "📋 Event Log",
    },
    "tab_detail": {
        "ko": "🔍 상세 처리 결과",
        "en": "🔍 Detailed Results",
    },
    "tab_chart": {
        "ko": "📊 탐지 통계",
        "en": "📊 Detection Statistics",
    },
    "detail_description": {
        "ko": "각 보안 이벤트의 마스킹 치환 상세 내역입니다. MASKED 이벤트를 펼쳐서 확인하세요.",
        "en": "Detailed masking/substitution info for each security event. Expand MASKED events to view.",
    },
    "detail_original": {
        "ko": "▼ 원본 프롬프트",
        "en": "▼ Original Prompt",
    },
    "detail_masked": {
        "ko": "▼ 전송 프롬프트 (마스킹)",
        "en": "▼ Sent Prompt (Masked)",
    },
    "detail_same": {
        "ko": "(동일 — 기밀 미탐지)",
        "en": "(Same — No confidential data detected)",
    },
    "detail_mapping": {
        "ko": "🔐 마스킹 토큰 매핑 내역",
        "en": "🔐 Masking Token Mapping",
    },
    "detail_no_mapping": {
        "ko": "매핑 정보 없음 (기밀 데이터 미탐지)",
        "en": "No mapping info (No confidential data detected)",
    },
    "chart_status_count": {
        "ko": "처리 상태별 건수",
        "en": "Events by Status",
    },
    "chart_emp_count": {
        "ko": "사번별 행위 건수",
        "en": "Events by Employee",
    },

    # ── API 에러 메시지 ──────────────────────────────────────────────────
    "api_server_error": {
        "ko": "서버 응답 오류",
        "en": "Server response error",
    },
    "api_connection_fail": {
        "ko": "서버 연결 실패! 시도한 주소:",
        "en": "Server connection failed! Attempted URL:",
    },
    "api_timeout": {
        "ko": "서버 응답 초과! 시도한 주소:",
        "en": "Server response timeout! Attempted URL:",
    },
    "api_security_violation": {
        "ko": "보안 정책 위반",
        "en": "Security policy violation",
    },
    "api_auth_expired": {
        "ko": "인증이 만료되었습니다. 다시 로그인해주세요.",
        "en": "Authentication expired. Please sign in again.",
    },
    "api_server_http_error": {
        "ko": "서버 오류",
        "en": "Server error",
    },
    "api_backend_unreachable": {
        "ko": "백엔드 서버에 연결할 수 없습니다.",
        "en": "Cannot connect to backend server.",
    },
    "api_response_timeout": {
        "ko": "응답 시간이 초과되었습니다.",
        "en": "Response timed out.",
    },
    "api_server_conn_error": {
        "ko": "서버 연결 오류:",
        "en": "Server connection error:",
    },
}
