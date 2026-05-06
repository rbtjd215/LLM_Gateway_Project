"""
routers.py
──────────────────────────────────────────────────────────
AutoCore AI Security Gateway - API 라우터 정의
엔드포인트: POST /login | POST /chat | GET /admin/logs
"""

import csv
import hashlib
import io
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from google import genai
from dotenv import load_dotenv

# 환경변수 로딩 (.env 파일 파싱)
load_dotenv()

# 최신 google-genai 클라이언트 초기화 (앱 시작 시 1회 실행)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

import redis
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

from passlib.context import CryptContext

from app.database import get_db
from app.models import User, SecurityLog
from app.schemas import (
    TokenResponse,
    ChatRequest, ChatResponse,
    LogEntry, LogListResponse,
)
from app.auth import (
    create_access_token,
    get_current_user,
    get_admin_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.security_core import check_intent, mask_sensitive_data, unmask_data

# ── 비밀번호 해시 컨텍스트 (bcrypt) ───────────────────────────────────────────
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()

# ── Redis 클라이언트 (마스킹 매핑 임시 저장용) ───────────────────────────────
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
_redis_client = redis.from_url(_REDIS_URL, decode_responses=True)
_MASK_MAPPING_TTL = 300  # 마스킹 매핑 TTL: 300초 (5분)

# ── KST 시간대 상수 (UTC+9) ────────────────────────────────────────────────
_KST = timezone(timedelta(hours=9))


def _log_security_event(
    db: Session,
    employee_num: str,
    action: str,
    detected_threat: str,
    log_status: str,
    prompt: str,
    masked_prompt: str = "",
    mapping_dict: dict | None = None,
) -> None:
    """
    보안 이벤트를 DB security_logs 테이블에 KST 기준으로 기록.
    log_status: 'BLOCKED' | 'MASKED' | 'ALLOWED'
    """
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    mapping_json = json.dumps(mapping_dict, ensure_ascii=False) if mapping_dict else ""
    log = SecurityLog(
        employee_num=employee_num,
        action=action,
        detected_threat=detected_threat,
        status=log_status,
        raw_prompt_hash=prompt_hash,
        original_prompt=prompt,
        masked_prompt=masked_prompt,
        mapping_dict=mapping_json,
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
    description="""
    Swagger UI의 **Authorize** 버튼 또는 form-data POST로 로그인합니다.  
    - **username** 필드에 사번(예: `EMP-001`, `ADMIN-001`)을 입력하세요.  
    - **password** 필드에 비밀번호를 입력하세요.
    """,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),  # Swagger Authorize 폼과 호환
    db: Session = Depends(get_db),
):
    """
    OAuth2 Password Flow — Swagger UI Authorize 버튼과 완전 호환.
    form_data.username → DB의 employee_num 필드와 매핑하여 bcrypt 검증.
    """
    # form_data.username → employee_num 으로 매핑
    user = db.query(User).filter(User.employee_num == form_data.username).first()

    # bcrypt로 비밀번호 검증 (DB에 bcrypt 해시가 저장된 경우)
    if not user or not _pwd_ctx.verify(form_data.password, user.password_hash):
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
    2. **2차 보안 — NER 마스킹:** `mask_sensitive_data`로 기밀 데이터를 `[MASKED_EMP_난수]` 토큰으로 치환
    3. **Redis 캐싱:** 매핑 딕셔너리를 UUID 키로 Redis에 TTL 300초 저장
    4. **LLM 추론:** 마스킹된 안전한 텍스트만 LLM에 전송
    5. **응답:** AI 응답 + X-Mask-Session-Id 헤더 반환
    """,
)
def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),  # JWT 인증 의존성
    db: Session = Depends(get_db),                    # DB 세션 (보안 로그 기록용)
):
    """
    보안 파이프라인 처리 + 각 단계별 DB 로그 기록:
        [1] check_intent        → 탐지 시 DB BLOCKED 기록 후 403 반환
        [2] mask_sensitive_data  → 기밀 탐지 시 [MASKED_*] 토큰 치환 + DB 기록
        [3] Redis 캐싱           → mapping_dict를 UUID 키로 Redis에 TTL 300초 저장
        [4] Gemini LLM           → 마스킹된 텍스트로 실제 추론 요청
        [5] 응답 반환             → AI 응답 + X-Mask-Session-Id 헤더
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
            masked_prompt="",
            mapping_dict=None,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"[보안 차단] {block_reason}",
        )

    # ── [2단계] 마스킹: 기밀 데이터 → 동적 난수 토큰 치환 ──────────────────
    # mask_sensitive_data: EMP-\d{3}(사원번호), DWG-\d{4}-[A-Z]\d(도면번호) 등
    # re 모듈 기반 NER 패턴을 일괄 탐지하여 [TOKEN_난수]로 비식별화
    masked_text, mapping = mask_sensitive_data(request.prompt)

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
            masked_prompt=masked_text,
            mapping_dict=mapping,
        )
    else:
        _log_security_event(
            db=db,
            employee_num=current_user.employee_num,
            action="CHAT_REQUEST",
            detected_threat="NONE",
            log_status="ALLOWED",
            prompt=request.prompt,
            masked_prompt=masked_text,
            mapping_dict=None,
        )

    # ── [3단계] LLM 추론: Gemini로 실제 AI 응답 생성 ──────────────────
    #    마스킹된 안전한 텍스트(masked_text)만 외부 LLM에 전송
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="[설정 오류] GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.",
            )

        # V2 SDK 최신 문법으로 추론 요청 (gemini-3-flash-preview 모델 사용)
        gemini_response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=masked_text
        )
        ai_response: str = gemini_response.text

    except HTTPException:
        # HTTPException은 그대로 re-raise (위의 API 키 누락 에러)
        raise
    except Exception as exc:  # noqa: BLE001
        # 네트워크 오류, 할당량 초과, 잘못된 응답 등 API 관련 예외
        print(f"[AI 추론 오류 발생] 상세 내역: {exc}")  # 서버 터미널에만 출력
        raise HTTPException(
            status_code=500,
            detail="AI 서비스 일시 장애. 잠시 후 다시 시도해주세요.",
        )

    # ── [4단계] Redis 캐싱: 매핑 딕셔너리를 임시 저장 ─────────────────
    #    추후 unmask_data 역치환 시 이 매핑을 Redis에서 조회하여 사용
    mask_session_id = str(uuid.uuid4())
    if mapping:
        _redis_client.setex(
            f"mask:{mask_session_id}",
            _MASK_MAPPING_TTL,
            json.dumps(mapping, ensure_ascii=False),
        )

    # ── [5단계] 역치환: AI 응답 내 마스킹 토큰 → 원본 기밀 데이터 복원 ────
    #    mapping_dict에 저장된 {토큰: 원본} 쌍을 순회하며 replace 처리
    final_response = ai_response
    for mask_token, original_text in mapping.items():
        final_response = final_response.replace(mask_token, original_text)

    # ── [6단계] 응답 반환: 역치환 완료된 텍스트 + X-Mask-Session-Id 헤더 ──
    return JSONResponse(
        content={"response": final_response},
        headers={"X-Mask-Session-Id": mask_session_id},
    )


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
            original_prompt=log.original_prompt or "",
            masked_prompt=log.masked_prompt or "",
            mapping_info=log.mapping_dict or "",
        )
        for log in logs_db
    ]
    return LogListResponse(total=len(logs), logs=logs)


# ══════════════════════════════════════════════════════════
#  GET /admin/export-csv  — 보안 로그 CSV 다운로드
# ══════════════════════════════════════════════════════════

@router.get("/admin/export-csv")
def export_csv(db: Session = Depends(get_db)):
    logs = db.query(SecurityLog).all()
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["log_id", "employee_num", "action", "detected_threat", "status", "timestamp", "original_prompt", "masked_prompt"])
    for log in logs:
        writer.writerow([log.log_id, log.employee_num, log.action, log.detected_threat, log.status, log.created_at, log.original_prompt, log.masked_prompt])
    stream.seek(0)
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=autocore_logs.csv"})
