# ── 베이스 이미지: 경량 Python 3.11 슬림 ──────────────────────────────────
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 먼저 복사 (레이어 캐시 최적화)
COPY requirements.txt .

# 패키지 설치 (캐시 최소화)
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# Streamlit 기본 포트 노출
EXPOSE 8501

# 환경 변수 기본값 (docker-compose에서 오버라이드 가능)
ENV API_URL=http://api:8000

# Streamlit 실행
#   --server.address=0.0.0.0  : 컨테이너 외부에서 접근 허용
#   --server.port=8501         : 포트 고정
#   --server.headless=true     : 브라우저 자동 열기 비활성화 (컨테이너 환경 필수)
CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
