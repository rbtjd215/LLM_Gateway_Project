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
from app.security_core import check_security, unmask_response

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
    **[V3 하이브리드 지능형 보안 파이프라인]**

    1. **Phase 1 — 정규식 마스킹:** 기밀 데이터를 __MASK 토큰으로 초고속 치환
    2. **Phase 2 — Ollama Guard:** llama-guard3 문맥 기반 의도 분류 (safe/unsafe)
    3. **Phase 3 — NER 마스킹:** KoBERT NER 모델 2차 마스킹
    4. **LLM 추론:** 마스킹된 안전한 텍스트만 LLM에 전송
    5. **역치환:** AI 응답의 마스킹 토큰을 원본으로 복원
    """,
)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),  # JWT 인증 의존성
    db: Session = Depends(get_db),                    # DB 세션 (보안 로그 기록용)
):
    """
    V3 하이브리드 보안 파이프라인:
        [1] check_security  → Phase 1(정규식) + Phase 2(Ollama Guard) + Phase 3(NER)
        [2] 차단 시 DB BLOCKED 기록 후 403 반환
        [3] 통과 시 마스킹 결과 DB 기록 + LLM 추론 + 역치환
    """
    # ── [1단계] V3 통합 보안 파이프라인 ────────────────────────────
    try:
        security_result = await check_security(request.prompt)
    except HTTPException as sec_exc:
        if sec_exc.status_code == 403:
            # Ollama Guard 또는 정규식에 의해 차단됨
            _log_security_event(
                db=db,
                employee_num=current_user.employee_num,
                action="CHAT_REQUEST",
                detected_threat=f"PROMPT_INJECTION: {sec_exc.detail}",
                log_status="BLOCKED",
                prompt=request.prompt,
                masked_prompt="",
                mapping_dict=None,
            )
        raise  # 403, 503, 504 등 그대로 전파

    masked_text = security_result["masked_text"]
    mapping = security_result["mapping"]

    # ── [2단계] 마스킹 결과 DB 로그 기록 ────────────────────────────
    if mapping:
        leaked_values = ", ".join(mapping.values())
        
        regex_map = security_result.get("regex_mapping", {})
        llm_map = security_result.get("llm_mapping", {})
        
        # [추가] 터미널 캡처용 실제 서버 로그 형태의 출력 (전반부)
        import time
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [SecurityCore] [INFO] Intercepted incoming prompt (len: {len(request.prompt)})")
        if regex_map:
            print(f"[{ts}] [SecurityCore:Phase1] [WARN] Pattern match: {list(regex_map.values())} -> {list(regex_map.keys())}")
        if llm_map:
            print(f"[{ts}] [SecurityCore:Phase3] [WARN] AI-Context match: {list(llm_map.values())} -> {list(llm_map.keys())}")
        print(f"[{ts}] [AutoCore:Egress] [SECURE] Transmitting masked payload to external LLM:")
        print(f"    PAYLOAD: {masked_text}")

        
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
    try:
        if os.getenv('USE_MOCK_LLM') == 'True':
            ai_response: str = f"[MOCK MODE] Echo response for testing unmasking: {masked_text}"
        else:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="[설정 오류] GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.",
                )
            gemini_response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=masked_text
            )
            ai_response: str = gemini_response.text

    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"[AI error] {exc}")
        raise HTTPException(
            status_code=500,
            detail="AI service error. Please retry.",
        )

    # ── [4단계] Redis 캐싱 ─────────────────────────────────────
    mask_session_id = str(uuid.uuid4())
    if mapping:
        _redis_client.setex(
            f"mask:{mask_session_id}",
            _MASK_MAPPING_TTL,
            json.dumps(mapping, ensure_ascii=False),
        )

    # ── [5단계] 역치환: 공백 변형 허용 유연 복원 ────────────────────
    final_response = unmask_response(ai_response, mapping)

    # [추가] 터미널 캡처용 실제 서버 로그 형태의 출력 (후반부)
    if mapping:
        import time
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [AutoCore:Ingress] [INFO] Received response from external LLM:")
        print(f"    RAW_RESPONSE: {ai_response}")
        print(f"[{ts}] [SecurityCore] [INFO] De-masking complete. Restored {len(mapping)} token(s).")
        print(f"[{ts}] [AutoCore] [SUCCESS] Request successfully fulfilled.")

    # ── [6단계] 응답 반환 ──────────────────────────────────────
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


# ══════════════════════════════════════════════════════════
#  DELETE /admin/clear-logs  — 보안 로그 전체 초기화 (테스트용)
# ══════════════════════════════════════════════════════════

@router.delete("/admin/clear-logs")
def clear_logs(
    current_user: User = Depends(get_admin_user),  # 관리자 권한 의존성
    db: Session = Depends(get_db),
):
    try:
        db.query(SecurityLog).delete()
        db.commit()
        return {"message": "Logs cleared successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
