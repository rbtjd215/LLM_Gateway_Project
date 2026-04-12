"""
main.py
──────────────────────────────────────────────────────────
AutoCore AI Security Gateway - FastAPI 애플리케이션 진입점
[제약사항 2] CORSMiddleware 전체 출처 허용 (팀원 A Streamlit 연동)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, SessionLocal
from app import models
from app.routers import router


# ── DB 테이블 생성 및 초기 시드 데이터 ────────────────────

def _seed_initial_data():
    """
    서버 최초 기동 시 테스트용 유저 및 부품 데이터 삽입.
    이미 데이터가 존재하면 스킵 (멱등성 보장).
    """
    db = SessionLocal()
    try:
        # 이미 유저가 있으면 스킵
        if db.query(models.User).count() > 0:
            print("[AutoCore] 초기 데이터 이미 존재 → 시드 스킵")
            return

        # ── 테스트 유저 ───────────────────────────────────
        # ※ 현재 password_hash는 평문 (초기 테스트용)
        #   추후 passlib.bcrypt.hash()로 교체 예정
        test_users = [
            models.User(employee_num="EMP-001",   password_hash="pass1234",  role="user",  name="김철수"),
            models.User(employee_num="EMP-002",   password_hash="pass5678",  role="user",  name="이영희"),
            models.User(employee_num="EMP-042",   password_hash="pass0000",  role="user",  name="박설계"),
            models.User(employee_num="ADMIN-001", password_hash="adminpass", role="admin", name="최보안"),
        ]
        db.add_all(test_users)

        # ── 자동차 부품 기밀 데이터 ────────────────────────
        test_parts = [
            models.AutoPart(
                blueprint_num="DWG-2026-X1",
                dimensions="공차 ±0.005mm, 외경 150mm, 내경 120mm",
                material="티타늄 합금 Ti-6Al-4V (Al 6%, V 4%)",
            ),
            models.AutoPart(
                blueprint_num="DWG-2026-X2",
                dimensions="공차 ±0.003mm, 두께 12mm, 폭 85mm",
                material="고강도 알루미늄 7075-T6",
            ),
            models.AutoPart(
                blueprint_num="DWG-2026-X3",
                dimensions="공차 ±0.010mm, 길이 320mm, 직경 45mm",
                material="탄소강 AISI 4340 (Cr 0.8%, Mo 0.25%)",
            ),
        ]
        db.add_all(test_parts)

        db.commit()
        print("[AutoCore] 초기 테스트 데이터 삽입 완료 ✓")
        print("[AutoCore]   유저: EMP-001/pass1234, EMP-002/pass5678, ADMIN-001/adminpass")

    except Exception as e:
        db.rollback()
        print(f"[AutoCore] 초기 데이터 삽입 실패: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 수명주기 관리: 시작 시 DB 초기화 수행"""
    print("[AutoCore] AI Security Gateway 기동 중...")
    # ORM 모델 기반으로 테이블 자동 생성
    models.Base.metadata.create_all(bind=engine)
    # 초기 시드 데이터 삽입
    _seed_initial_data()
    print("[AutoCore] 게이트웨이 준비 완료 ✓  → http://localhost:8000/docs")
    yield
    print("[AutoCore] 게이트웨이 종료")


# ── FastAPI 앱 생성 ────────────────────────────────────────

app = FastAPI(
    title="AutoCore AI Security Gateway",
    description="""
## 오토코어 지능형 AI 보안 게이트웨이 (차세대 AI DLP)

기업 임직원이 외부 AI(ChatGPT 등)를 업무에 활용할 때 발생하는  
**기밀 데이터 유출**과 **프롬프트 인젝션** 위협을 원천 차단하는 하이브리드 보안 시스템.

### 보안 파이프라인
1. **의도 분석** - Prompt Injection 탐지 및 차단
2. **NER 마스킹** - 기밀 데이터 → `[BLUEPRINT_난수]` 토큰 치환 (Redis 저장)
3. **외부 LLM 전송** - 마스킹된 안전한 텍스트만 전달
4. **역치환 복원** - AI 응답의 토큰 → 원본 데이터 복원

### 개발 현황
- **팀원 C (백엔드):** 인프라 및 API 뼈대 ✅ **(현재 단계)**
- **팀원 B (보안):** 마스킹 모듈 개발 중 🔄
- **팀원 A (프론트):** Streamlit UI 개발 중 🔄
    """,
    version="0.1.0",
    lifespan=lifespan,
)


# ── CORS 미들웨어 ─────────────────────────────────────────
# [제약사항 2] 팀원 A의 Streamlit 앱이 어떤 포트에서 실행되더라도 API 호출 가능하도록 전체 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 모든 출처 허용 (팀원 A Streamlit 연동)
    allow_credentials=True,
    allow_methods=["*"],       # GET, POST, PUT, DELETE 등 모두 허용
    allow_headers=["*"],       # Authorization 헤더 포함 모두 허용
)


# ── 라우터 등록 ────────────────────────────────────────────
app.include_router(router)


# ── 헬스체크 엔드포인트 ──────────────────────────────────────

@app.get("/", tags=["헬스체크"], summary="서비스 정보")
def root():
    return {
        "service": "AutoCore AI Security Gateway",
        "version": "0.1.0",
        "status": "running",
        "team": {
            "A_frontend": "Streamlit UI (연동 대기 중)",
            "B_security": "NER 마스킹 모듈 (개발 중)",
            "C_backend":  "FastAPI 인프라 (현재 단계) ✓",
        },
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["헬스체크"], summary="헬스체크")
def health_check():
    return {"status": "healthy", "service": "autocore-ai-gateway"}
