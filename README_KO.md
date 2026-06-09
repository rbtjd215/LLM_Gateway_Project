# LLM-based Hybrid AI Security Gateway

-> **[Read in English](README.md)**
> **프롬프트 인젝션 방어와 기밀 데이터 비식별화를 위한 PoC(Proof of Concept)**

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

## 1. 연구 배경 및 문제 정의

생성형 AI의 기업 도입이 확산됨에 따라, 임직원의 **비의도적 기밀 유출**과 악의적인 **프롬프트 인젝션**이 핵심 보안 위협으로 대두되었다.

* **기밀 데이터 유출 심화:** Cyberhaven(2024) 보고서에 따르면 AI 도구에 입력된 데이터 중 27.4%가 기밀 정보이다.
* **기존 보안의 한계:** 기존 DLP(Data Loss Prevention) 솔루션은 정해진 패턴(주민번호 등)만 탐지할 뿐, 문맥 속에 숨겨진 비정형 기밀(예: 신소재 배합 비율)을 파악하지 못한다.
* **섀도우 AI (Shadow AI) 문제:** 보안을 이유로 사내망에서 AI 접근을 전면 차단하면, 임직원들이 개인 기기나 네트워크로 우회하여 접속하는 '섀도우 AI' 현상이 발생한다. 이는 회사의 통제 영역을 벗어나 유출 감사조차 불가능하게 만드는 역설적인 결과를 낳는다.

**핵심 연구 질문:**  
*"기밀은 보호하되, AI 사용은 안전하게 허용하는 중간 지점의 보안 아키텍처는 없는가?"*

---

## 2. 아키텍처 및 4대 설계 원칙

본 프로젝트는 기업(가상의 제조 기업 '오토코어') 사내망에 배치되어 외부 AI와 통신하는 **AI 보안 게이트웨이 프록시**를 제안하고 직접 구현했다.

### 설계 원칙
1. **완전한 로컬 처리**: 모든 보안 검열(마스킹, 의도 파악)은 사내 로컬 LLM에서 처리되어 데이터 주권을 보장한다.
2. **계층적 심층 방어 (Defense-in-Depth)**: 패턴 필터 → 의도 분류 → 생성형 마스킹의 3겹 방어망을 구축했다.
3. **동적 마스킹 및 역치환**: 차단이 아닌 '난수 치환'을 통해 안전한 데이터만 AI로 전송하고, 응답 시 원본으로 복원하여 사용자 경험을 보존한다.
4. **AI 고유 공격 대응**: LLM-as-a-Judge 기법을 적용하여 프롬프트 인젝션 등의 문맥적 위협을 판단한다.
5. **글로벌 접근성 (i18n)**: 한국어/영어 UI 토글을 완벽하게 지원하여, 해외 개발자 및 심사관들도 즉각적이고 직관적으로 시스템을 평가할 수 있다.

---

## 3. 3단계 하이브리드 보안 파이프라인

게이트웨이의 핵심 엔진은 **정규식과 LLM을 결합한 하이브리드 아키텍처**이다. 

```mermaid
graph TD
    A[사용자 입력] --> B[Phase 1: 정규식 고속 필터]
    B -->|정형 기밀 마스킹| C{비동기 병렬 처리}
    C --> D[Phase 2: LLM 의도 분류]
    C --> E[Phase 3: 생성형 마스킹]
    D -->|Fail-Closed 차단| F[관리자 로깅]
    E -->|비정형 기밀 마스킹| G[마스킹된 최종 텍스트]
    G --> H[외부 상용 AI 추론]
    H --> I[Phase 4: 역치환 복원]
    I --> J[사용자 응답 반환]
```

* **Phase 1 (정규식 고속 필터):** 사번, 도면 번호 등 정형화된 기밀 데이터를 초고속으로 `__MASK_TYPE_HEX__` 형태의 난수 토큰으로 치환한다.
* **Phase 2 (LLM-as-a-Judge):** 로컬 LLM(Qwen 2.5 7B)이 문맥을 분석하여 프롬프트 인젝션, 시스템 탈옥 시도를 탐지하고 즉시 차단(Fail-Closed)한다.
* **Phase 3 (Generative DLP):** 동일한 로컬 LLM이 문맥을 읽어 '공차', '배합비' 등 정규식이 잡지 못하는 비정형 기밀을 찾아내어 마스킹한다. (Phase 2와 `asyncio`로 병렬 처리하여 지연 시간 단축)

---

## 4. 핵심 기능 시연 (Core Features)

### 1) 정상 질의 및 동적 마스킹 (UX 보존)
사용자가 기밀 데이터를 포함해 질문하면, 게이트웨이가 이를 무작위 토큰으로 마스킹하여 외부 AI에 전달합니다. 수신된 답변은 다시 완벽하게 원본 상태로 역치환(De-masking)되어 사용자에게 제공됩니다.

> ![채팅 화면](assets/captures/chat_ko.png)
> *[UI] Streamlit 기반의 다크 테마 채팅 인터페이스*

### 2) 프롬프트 인젝션 방어 (Prompt Injection Defense)
이전 지시를 무시하거나 관리자 권한을 요구하는 등의 악의적인 컨텍스트는 즉시 차단됩니다.

> ![차단 화면](assets/captures/blocked_ko.png)
> *[방어] LLM-as-a-Judge에 의해 악의적 의도가 차단됨 (붉은색 경고 배너)*

### 3) 관리자 보안 대시보드 (Admin Security Dashboard)
게이트웨이를 통과하는 모든 이벤트(허용, 마스킹, 차단)를 실시간으로 기록하고 모니터링하며, 원본 프롬프트와 마스킹된 프롬프트를 비교 감사할 수 있습니다.

> ![대시보드](assets/captures/dashboard_ko.png)
> *[로깅] 토큰화된 데이터와 원본 텍스트 매핑을 감사하기 위한 관리자 패널*

---

## 5. 시스템 성능 및 평가 (1,200건 벤치마크)

본 연구팀은 가혹 조건의 1,200건 자동화 테스트셋을 통해 성능을 입증했다.

| 평가 지표 | V1 (정규식 전용) | V4 (CPU 단독) | V4 (GPU 가속) |
|---|:---:|:---:|:---:|
| **종합 방어율 (Recall)** | 26.7% | 78.33% | 77.60% |
| **정밀도 (Precision)** | ~100% | 99.86% | 99.70% |
| **인젝션 차단율** | ~15% | 91.67% | 91.60% |
| **오탐률 (FPR)** | 0.0% | 0.14% | 0.30% |
| **처리 지연 (Warm State)** | 0.1s | 1~3초대 (최대 9.7초) | **평균 1.36초** |

> * **※ 용어 설명 및 분석:** 
>   * **방어율(Recall):** 실제 존재하는 기밀/공격 중 시스템이 놓치지 않고 찾아낸 비율 (보안성 지표).
>   * **정밀도(Precision):** 시스템이 차단한 것 중 실제 기밀/공격이 맞았던 비율. 100%에 가까울수록 정상 업무를 억울하게 차단하는 오탐(FPR)이 없음을 의미함 (가용성 지표).
>   * **수치 변동 원인:** V4(CPU)와 V4(GPU) 간의 0.x% 수치 변동은 동일한 7B 모델을 사용할 때 발생하는 생성형 AI 특유의 난수 기반 무작위성(통계적 오차) 범위 내이며, 두 환경에서의 보안 지능 수준은 수학적으로 동일함.

**결론 및 확장성 증명 (Scalability):**  
소형 로컬 모델(7B)의 한계로 인해 방어율(Recall)은 약 78% 수준을 기록하고 있으나, 정밀도 99.86%를 달성하여 아키텍처 자체의 견고함을 증명했다. 특히, 기존 CPU 환경에서 관찰되었던 처리 속도(Latency) 한계는 GPU 환경 추가 테스트 결과 단 1초대(평균 1.36초)로 단축됨이 확인되었다. 이는 예상한 대로 **인프라 자원(GPU)을 투입하는 만큼 성능이 비약적으로 향상될 수 있다는 것을 증명**하며, 향후 70B 이상의 대형 모델(엔진)로 교체할 경우 방어율 역시 즉각적으로 상승할 수 있는 확장성 높은 구조이다.

---

## 6. 기술 스택 (Tech Stack)

| 구분 | 사용 기술 |
|---|---|
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Frontend** | Streamlit |
| **Database** | PostgreSQL 15, SQLAlchemy ORM |
| **Cache/KV** | Redis 7 |
| **AI / Security** | 로컬 Ollama (Qwen2.5:7b), Google Gemini API |
| **Infrastructure** | Docker, Docker Compose |

---

## 7. 빠른 시작 가이드 (Quick Start)

### 사전 요구사항
* Docker 및 Docker Compose
* 로컬에 [Ollama](https://ollama.com/) 설치 및 `qwen2.5:7b` 모델 풀링 (`ollama run qwen2.5:7b`)
* Google Gemini API Key

### 실행 방법

1. **저장소 클론 및 환경변수 설정**
   ```bash
   git clone https://github.com/your-repo/LLM_Gateway_Project.git
   cd LLM_Gateway_Project
   cp .env.example .env
   # .env 파일을 열고 GEMINI_API_KEY 등 환경변수 입력
   ```

2. **Docker Compose 실행**
   ```bash
   docker-compose up --build -d
   ```

3. **서비스 접속**
   * **프론트엔드 (UI)**: `http://localhost:8501`
   * **백엔드 (API Docs)**: `http://localhost:8000/docs`
   * **테스트 계정**: `EMP-001` / `pass1234` (사용자), `ADMIN-001` / `adminpass` (관리자)

---

## 8. 보안 테스트 실행 가이드
본 프로젝트는 `pytest` 기반의 자동화된 보안 테스트 스크립트를 제공한다. 테스트 코드 실행 및 벤치마크 결과 확인은 [보안 테스트 결과 보고서](Docs_Korean/SECURITY_TESTING.md)를 참고한다.

---

## 9. License

이 프로젝트는 [MIT License](LICENSE)에 따라 배포된다. 자유롭게 참고하고, 연구 및 학습 목적으로 활용할 수 있다.

---

## 전체 문서 목차
1. [**메인 페이지 (README)**](./README_KO.md) 🔴 *현재 페이지*
2. [**시스템 아키텍처**](./Docs_Korean/ARCHITECTURE.md)
3. [**설치 및 실행 가이드**](./Docs_Korean/SETUP_GUIDE.md)
4. [**보안 테스트 가이드**](./Docs_Korean/SECURITY_TESTING.md)
5. [**API 명세서**](./Docs_Korean/API_REFERENCE.md)
