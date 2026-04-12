# AutoCore AI Security Gateway - FastAPI 서버 이미지
FROM python:3.11-slim

WORKDIR /app

# 의존성 파일 먼저 복사 → Docker 레이어 캐시 최적화
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

EXPOSE 8000

# docker-compose의 command로 override됨 (--reload 포함)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
