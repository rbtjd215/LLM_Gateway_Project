"""
models.py
──────────────────────────────────────────────────────────
AutoCore AI Security Gateway - SQLAlchemy ORM 데이터베이스 스키마
[제약사항 4] 날것의 SQL 금지, SQLAlchemy 모델로만 스키마 정의
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.database import Base


class User(Base):
    """
    users 테이블 - 오토코어 임직원 계정 정보
    role: 'user' (일반 임직원) | 'admin' (보안 관리자)
    """
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_num = Column(String(50),  unique=True, nullable=False, index=True, comment="사번")
    password_hash= Column(String(255), nullable=False,                          comment="비밀번호 (초기: 평문, 추후 bcrypt)")
    role         = Column(String(10),  nullable=False, default="user",          comment="권한: user | admin")
    name         = Column(String(100), nullable=False,                          comment="임직원 이름")
    created_at   = Column(DateTime(timezone=True), server_default=func.now(),   comment="계정 생성일시")


class AutoPart(Base):
    """
    auto_parts 테이블 - 오토코어 자동차 부품 설계 정보 (핵심 기밀 데이터)
    B 모듈의 NER 마스킹 대상: blueprint_num, dimensions, material
    """
    __tablename__ = "auto_parts"

    part_id       = Column(Integer, primary_key=True, index=True, autoincrement=True)
    blueprint_num = Column(String(100), unique=True, nullable=False, index=True, comment="설계 도면 번호 (예: DWG-2026-X1)")
    dimensions    = Column(Text,        nullable=True,                           comment="정밀 치수 세팅값 (예: 공차 ±0.005mm)")
    material      = Column(String(255), nullable=True,                           comment="신소재 배합 비율 및 소재명")
    created_at    = Column(DateTime(timezone=True), server_default=func.now(),   comment="등록일시")


class SecurityLog(Base):
    """
    security_logs 테이블 - AI 게이트웨이 보안 탐지 이벤트 로그
    B 모듈 통합 후 실제 탐지 이벤트를 여기에 기록할 예정.
    현재 /admin/logs는 더미 데이터 반환.
    """
    __tablename__ = "security_logs"

    log_id         = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_num   = Column(String(50),  nullable=False, index=True, comment="행위자 사번")
    action         = Column(String(50),  nullable=False,             comment="행위 유형 (예: CHAT_REQUEST)")
    detected_threat= Column(String(255), nullable=True,              comment="탐지된 위협 유형")
    status         = Column(String(20),  nullable=False,             comment="처리 결과: BLOCKED | MASKED | ALLOWED")
    raw_prompt_hash= Column(String(255), nullable=True,              comment="원본 프롬프트 SHA-256 해시 (감사용)")
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), comment="탐지 일시")
