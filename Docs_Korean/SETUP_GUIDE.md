# LLM Security Gateway 설치 및 실행 가이드

본 문서는 사용자의 로컬 PC 환경에 LLM 게이트웨이(PoC) 환경을 구축하고 실행하는 방법을 안내한다.

---

## 1. 사전 요구사항

시스템을 실행하기 전, PC에 아래 소프트웨어들이 설치되어 있어야 한다.

* **[Docker Desktop](https://www.docker.com/products/docker-desktop/)**: 컨테이너 오케스트레이션 구동용 (버전 20.10 이상 권장)
* **[Ollama](https://ollama.com/)**: 로컬 LLM 구동용 엔진
* **Google Gemini API Key**: [Google AI Studio](https://aistudio.google.com/)에서 무료로 발급 가능
* **Git**: 프로젝트 다운로드용

---

## 2. Ollama 및 로컬 모델 준비

보안 파이프라인(Phase 2, 3)을 처리할 로컬 모델을 다운로드해야 한다. (최초 1회만 수행)

1. PC에서 Ollama 프로그램을 실행한다. (Mac/Windows: 앱 실행, Linux: `systemctl start ollama`)
2. 터미널(CMD/PowerShell 등)을 열고 아래 명령어를 입력하여 `qwen2.5:7b` 모델을 풀링(다운로드)한다.
   ```bash
   ollama run qwen2.5:7b
   ```
   *다운로드가 완료되고 터미널에 `>>>` 프롬프트가 뜨면 준비가 완료된 것이다. `Ctrl+D`를 눌러 종료한다.*

---

## 3. 프로젝트 다운로드 및 환경 변수 설정

1. **저장소 클론 (Clone)**
   ```bash
   git clone https://github.com/your-repo/LLM_Gateway_Project.git
   cd LLM_Gateway_Project
   ```

2. **환경 변수 파일 생성**
   루트 디렉토리에 있는 `.env.example` 파일을 복사하여 `.env` 파일을 생성한다.
   ```bash
   cp .env.example .env
   ```

3. **`.env` 파일 수정**
   편집기로 `.env` 파일을 열고, 자신의 환경에 맞게 값을 수정한다.
   ```env
   # [필수] Google Gemini API Key 입력
   GEMINI_API_KEY=AIzaSy...자신의키입력...

   # [선택] 보안 엔진 모드 (기본값: HF_PIPELINE)
   # HF_PIPELINE : 정규식+LLM V4 하이브리드 파이프라인 (권장)
   # REGEX       : V1 정규식 고속 모드 (Ollama 끄고 테스트할 때 유용)
   ENGINE_MODE=HF_PIPELINE

   # [선택] 로컬 Ollama 주소 (Docker 사용 시 host.docker.internal 유지)
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   ```

---

## 4. Docker Compose로 전체 서비스 실행

루트 디렉토리에서 아래 명령어를 실행하여 4개의 컨테이너(API, Frontend, DB, Redis)를 모두 띄운다.

```bash
docker-compose up --build -d
```
* `-d`: 터미널을 점유하지 않고 백그라운드에서 실행한다.
* `--build`: Dockerfile에 변경사항이 있을 경우 이미지를 새로 빌드한다.

정상적으로 실행되었는지 확인하려면 아래 명령어로 API 로그를 확인한다.
```bash
docker-compose logs -f api
```
*(로그에 `[System] Gateway Ready ✓` 메시지가 보이면 성공이다.)*

---

## 5. 서비스 접속 및 테스트 계정 안내

컨테이너가 정상적으로 실행되었다면, 웹 브라우저를 열고 다음 주소로 접속한다.

* **웹 UI (Streamlit)**: [http://localhost:8501](http://localhost:8501)
* **API 문서 (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 기본 제공 테스트 계정

시스템 최초 부팅 시, 테스트를 위한 시드(Seed) 데이터가 DB에 자동으로 주입된다.

| 권한 | 사번 (ID) | 비밀번호 | 용도 |
|---|---|---|---|
| 일반 임직원 | `EMP-001` | `pass1234` | 채팅 테스트 및 동적 마스킹 검증 |
| 일반 임직원 | `EMP-002` | `pass5678` | 계정 격리 테스트용 |
| 보안 관리자 | `ADMIN-001` | `adminpass` | 보안 이벤트 로그 모니터링 (대시보드) |

---

## 6. 종료 및 데이터 초기화

* **서버 종료 (데이터 유지):**
  ```bash
  docker-compose down
  ```

* **서버 종료 및 DB 완전 삭제 (공장 초기화):**
  DB와 Redis 볼륨 데이터까지 완전히 날리고 싶을 때 사용한다.
  ```bash
  docker-compose down -v
  ```

---

## 7. 트러블슈팅 (FAQ)

### Q. 채팅을 보내면 `503 Service Unavailable (Ollama 연결 실패)` 에러가 뜬다.
> **A.** 도커 컨테이너 내부에서 호스트 PC의 Ollama에 접속하지 못해 발생하는 현상이다.
> 1. 호스트 PC에서 Ollama 프로그램이 켜져 있는지(트레이 아이콘) 확인한다.
> 2. 브라우저에서 `http://localhost:11434`에 접속했을 때 `Ollama is running` 문구가 뜨는지 확인한다.
> 3. Windows 환경일 경우, 시스템 환경 변수에 `OLLAMA_HOST` 값을 `0.0.0.0`으로 추가하고 Ollama를 재시작해 본다.

### Q. 코드(FastAPI)를 수정했는데 바로 반영이 안 된다.
> **A.** `docker-compose.yml`에 핫 리로드(`--reload`)가 설정되어 있지만, Windows 등 일부 OS 환경에서는 파일 변경 감지가 컨테이너로 전달되지 않을 수 있다. 이 경우 API 서버만 재시작하면 된다.
> ```bash
> docker-compose restart api
> ```

### Q. "GEMINI_API_KEY is not set" 에러가 발생하며 서버가 켜지지 않는다.
> **A.** `.env` 파일이 생성되지 않았거나 파일명에 오타가 있는 경우이다. `.env.example` 파일을 복사하여 정확히 `.env` 라는 이름의 파일을 만들었는지 확인한다.

---

### 📚 전체 문서 목차
1. [**메인 페이지 (README)**](../README_KO.md)
2. [**시스템 아키텍처**](./ARCHITECTURE.md)
3. [**설치 및 실행 가이드**](./SETUP_GUIDE.md) 📍 *현재 페이지*
4. [**보안 테스트 가이드**](./SECURITY_TESTING.md)
5. [**API 명세서**](./API_REFERENCE.md)
