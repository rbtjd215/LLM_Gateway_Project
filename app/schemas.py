"""
schemas.py
──────────────────────────────────────────────────────────
AutoCore AI Security Gateway - Pydantic 요청/응답 스키마 정의
API 계약서 역할: 팀원 A(프론트), 팀원 B(보안 모듈) 연동 시 이 스키마 기준
"""

from pydantic import BaseModel
from typing import Optional, List


# ── 인증 (Auth) ────────────────────────────────────────

class LoginRequest(BaseModel):
    """POST /login 요청 바디"""
    employee_num: str   # 사번 (예: EMP-001, ADMIN-001)
    password: str       # 비밀번호

    model_config = {"json_schema_extra": {"example": {"employee_num": "EMP-001", "password": "pass1234"}}}


class TokenResponse(BaseModel):
    """POST /login 성공 응답"""
    access_token: str   # JWT Bearer 토큰
    token_type: str     # "bearer"
    role: str           # "user" | "admin"
    name: str           # 임직원 이름 (UI 환영 메시지용)


class TokenData(BaseModel):
    """JWT 페이로드 내부 구조 (auth.py 내부 사용)"""
    employee_num: Optional[str] = None
    role: Optional[str] = None


# ── 채팅 (Chat) ────────────────────────────────────────

class ChatRequest(BaseModel):
    """POST /chat 요청 바디"""
    prompt: str         # 사용자가 입력한 원본 프롬프트

    model_config = {"json_schema_extra": {"example": {"prompt": "DWG-2026-X1 도면의 공차 기준을 설명해줘."}}}


class ChatResponse(BaseModel):
    """POST /chat 응답 바디"""
    response: str       # AI 게이트웨이를 거친 최종 응답


# ── 관리자 로그 (Admin Logs) ──────────────────────────

class LogEntry(BaseModel):
    """GET /admin/logs 단일 로그 항목"""
    log_id: int
    employee_num: str
    timestamp: str
    action: str
    detected_threat: str
    status: str         # "BLOCKED" | "MASKED" | "ALLOWED"
    original_prompt: Optional[str] = ""
    masked_prompt: Optional[str] = ""
    mapping_info: Optional[str] = ""  # JSON 문자열로 직렬화된 매핑 딕셔너리


class LogListResponse(BaseModel):
    """GET /admin/logs 전체 응답"""
    total: int
    logs: List[LogEntry]
