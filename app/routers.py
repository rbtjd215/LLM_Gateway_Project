"""
routers.py
──────────────────────────────────────────────────────────
AutoCore AI Security Gateway - API 라우터 정의
엔드포인트: POST /login | POST /chat | GET /admin/logs
"""

import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, SecurityLog
from app.schemas import (
    LoginRequest, TokenResponse,
    ChatRequest, ChatResponse,
    LogEntry, LogListResponse,
)
from app.auth import (
    create_access_token,
    get_current_user,
    get_admin_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.security_core import check_intent, mask_data, unmask_data

router = APIRouter()

# ── KST 시간대 상수 (UTC+9) ────────────────────────────────────────────────
_KST = timezone(timedelta(hours=9))


def _log_security_event(
    db: Session,
    employee_num: str,
    action: str,
    detected_threat: str,
    log_status: str,
    prompt: str,
) -> None:
    """
    보안 이벤트를 DB security_logs 테이블에 KST 기준으로 기록.
    log_status: 'BLOCKED' | 'MASKED' | 'ALLOWED'
    """
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    log = SecurityLog(
        employee_num=employee_num,
        action=action,
        detected_threat=detected_threat,
        status=log_status,
        raw_prompt_hash=prompt_hash,
        created_at=datetime.now(_KST),
    )
    db.add(log)
    db.commit()


# ══════════════════════════════════════════════════════════
#  POST /login  — 임직원 인증 및 JWT 발급
# ══════════════════════════════════════════════════════════

@router.post(
    "/login",
    response_model=TokenResponse,
    tags=["인증 (Auth)"],
    summary="임직원 로그인",
    description="사번(employee_num)과 비밀번호를 검증하여 JWT 액세스 토큰을 발급합니다.",
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    # 사번으로 유저 조회
    user = db.query(User).filter(User.employee_num == request.employee_num).first()

    # ※ 초기 테스트용: 비밀번호 단순 문자열 비교
    #   추후 팀원 B 모듈 또는 passlib.bcrypt.verify()로 교체할 것
    if not user or user.password_hash != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사번 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.employee_num, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        name=user.name,
    )


# ══════════════════════════════════════════════════════════
#  POST /chat  — AI 게이트웨이 채팅 (인증 필요)
# ══════════════════════════════════════════════════════════

@router.post(
    "/chat",
    response_model=ChatResponse,
    tags=["채팅 (Chat)"],
    summary="AI 게이트웨이 채팅",
    description="""
    **[보안 파이프라인 - 팀원 B 모듈 통합 완료]**

    1. **1차 보안 — 의도 분석:** `check_intent`로 Prompt Injection 탐지 → 위험 시 403 차단
    2. **2차 보안 — NER 마스킹:** `mask_data`로 기밀 데이터를 `[BLUEPRINT_난수]` 토큰으로 치환
    3. **LLM 추론:** 마스킹된 안전한 텍스트만 LLM에 전송 (현재: Echo 가짜 응답)
    4. **3차 보안 — 역치환:** `unmask_data`로 토큰을 원본 데이터로 복원 후 클라이언트 반환
    """,
)
def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),  # JWT 인증 의존성
    db: Session = Depends(get_db),                    # DB 세션 (보안 로그 기록용)
):
    """
    보안 파이프라인 4단계 처리 + 각 단계별 DB 로그 기록:
        [1] check_intent  → 탐지 시 DB BLOCKED 기록 후 403 반환
        [2] mask_data     → 기밀 있으면 DB MASKED, 없으면 DB ALLOWED 기록
        [3] Echo LLM      → 마스킹된 텍스트로 가짜 응답 (추후 실제 LLM 교체)
        [4] unmask_data   → AI 응답 내 토큰 역치환 후 반환
    """
    # ── [1단계] 의도 분석: 프롬프트 인젝션 탐지 ────────────────────────────
    is_malicious, block_reason = check_intent(request.prompt)
    if is_malicious:
        # 차단 이벤트 → DB 기록 후 403 반환
        _log_security_event(
            db=db,
            employee_num=current_user.employee_num,
            action="CHAT_REQUEST",
            detected_threat=f"PROMPT_INJECTION: {block_reason}",
            log_status="BLOCKED",
            prompt=request.prompt,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"[보안 차단] {block_reason}",
        )

    # ── [2단계] 마스킹: 기밀 데이터 → 동적 난수 토큰 치환 ──────────────────
    masked_text, mapping = mask_data(request.prompt)

    # 마스킹 결과에 따라 MASKED / ALLOWED 분류 후 DB 기록
    if mapping:
        leaked_values = ", ".join(mapping.values())
        _log_security_event(
            db=db,
            employee_num=current_user.employee_num,
            action="CHAT_REQUEST",
            detected_threat=f"CONFIDENTIAL_DATA_LEAK ({leaked_values})",
            log_status="MASKED",
            prompt=request.prompt,
        )
    else:
        _log_security_event(
            db=db,
            employee_num=current_user.employee_num,
            action="CHAT_REQUEST",
            detected_threat="NONE",
            log_status="ALLOWED",
            prompt=request.prompt,
        )

    # ── [3단계] LLM 추론: 마스킹된 텍스트로 가짜 응답 생성 ────────────────
    # TODO: 외부 LLM API 연동 시 아래 한 줄을 교체하면 됨
    #   ai_response = await call_openai(masked_text)
    ai_response: str = f"Echo: {masked_text}"

    # ── [4단계] 역치환: AI 응답 내 토큰 → 원본 기밀 데이터 복원 ────────────
    final_text = unmask_data(ai_response, mapping)

    return ChatResponse(response=final_text)


# ══════════════════════════════════════════════════════════
#  GET /admin/logs  — 보안 이벤트 로그 조회 (관리자 전용)
# ══════════════════════════════════════════════════════════

@router.get(
    "/admin/logs",
    response_model=LogListResponse,
    tags=["관리자 (Admin)"],
    summary="보안 탐지 로그 조회",
    description="**관리자 전용.** AI 게이트웨이에서 탐지된 보안 이벤트 로그를 조회합니다. role이 'admin'이 아니면 403 반환.",
)
def get_admin_logs(
    current_user: User = Depends(get_admin_user),  # 관리자 권한 의존성
    db: Session = Depends(get_db),
):
    """
    security_logs 테이블에서 실제 탐지 이벤트를 최신순(내림차순)으로 조회.
    /chat 호출 시 _log_security_event()가 쌓은 실제 데이터를 반환.
    """
    logs_db = (
        db.query(SecurityLog)
        .order_by(SecurityLog.created_at.desc())
        .all()
    )

    def _to_kst_str(dt: datetime | None) -> str:
        """DB에서 꺼낸 datetime을 KST ISO-8601 문자열로 변환"""
        if dt is None:
            return ""
        # PostgreSQL은 timezone-aware UTC로 반환할 수 있음
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_KST).strftime("%Y-%m-%dT%H:%M:%S+09:00")

    logs = [
        LogEntry(
            log_id=log.log_id,
            employee_num=log.employee_num,
            timestamp=_to_kst_str(log.created_at),
            action=log.action or "CHAT_REQUEST",
            detected_threat=log.detected_threat or "NONE",
            status=log.status,
        )
        for log in logs_db
    ]
    return LogListResponse(total=len(logs), logs=logs)
