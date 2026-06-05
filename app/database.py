"""
database.py
──────────────────────────────────────────────────────────
AutoCore AI Security Gateway - 데이터베이스 연결 및 세션 관리
[제약사항 4] SQLAlchemy ORM 기반으로만 DB 접근
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 환경 변수에서 DB URL 가져오기 (docker-compose에서 주입)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://autocore_user:autocore_pass@localhost:5432/autocore_db",
)

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # 연결 유효성 자동 확인
    pool_size=10,             # 커넥션 풀 크기
    max_overflow=20,          # 풀 초과 시 최대 추가 연결 수
)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 모델의 베이스 클래스
Base = declarative_base()


def get_db():
    """
    FastAPI Depends() 의존성 함수.
    요청마다 DB 세션을 열고, 응답 후 반드시 닫는다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
