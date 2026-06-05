"""
auth.py
──────────────────────────────────────────────────────────
AutoCore AI Security Gateway - JWT 인증 및 권한 검사 의존성
FastAPI Depends() 패턴으로 라우터에서 재사용
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import TokenData

# ── 환경 변수 ─────────────────────────────────────────
SECRET_KEY                = os.getenv("SECRET_KEY", "autocore-super-secret-key-change-in-production-2026")
ALGORITHM                 = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# OAuth2 스킴: /login 엔드포인트에서 토큰을 발급받는 구조
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


# ── 토큰 발급 ──────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT 액세스 토큰 생성.
    data 딕셔너리에 'sub' (사번), 'role' (권한)을 담아 서명.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ── 토큰 검증 의존성 ────────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    [공통 인증 의존성] Bearer 토큰을 디코딩 → DB에서 유저 조회.
    유효하지 않으면 401 Unauthorized.
    POST /chat 등 로그인 필요 엔드포인트에서 사용.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보를 확인할 수 없습니다. 다시 로그인해주세요.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        employee_num: str = payload.get("sub")
        role: str = payload.get("role")
        if employee_num is None:
            raise credentials_exception
        token_data = TokenData(employee_num=employee_num, role=role)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.employee_num == token_data.employee_num).first()
    if user is None:
        raise credentials_exception
    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    [관리자 전용 의존성] get_current_user를 먼저 통과한 뒤 role 검사.
    role이 'admin'이 아니면 403 Forbidden.
    GET /admin/logs 등 관리자 전용 엔드포인트에서 사용.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다. 접근이 거부되었습니다.",
        )
    return current_user
