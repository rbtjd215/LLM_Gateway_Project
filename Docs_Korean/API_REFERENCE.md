# LLM Security Gateway API 명세서

본 문서는 프론트엔드 애플리케이션 및 외부 클라이언트가 LLM Gateway Backend(FastAPI)와 통신하기 위한 RESTful API 규격을 정의한다.

> **Base URL:** `http://localhost:8000` (Docker 환경: `http://api:8000`)  
> **Swagger UI:** `http://localhost:8000/docs` (자동 생성 문서)

---

## 인증 방식 (Authentication)

모든 보호된 엔드포인트(`/chat`, `/admin/*`)는 **JWT (JSON Web Token)** 기반의 **Bearer Token** 인증을 사용한다.
요청 헤더에 다음과 같이 토큰을 포함해야 한다.
```http
Authorization: Bearer <발급받은_JWT_토큰>
```

---

## 1. Auth API

### 1.1 임직원 로그인 및 토큰 발급
사번과 비밀번호로 인증하고 JWT Access Token을 발급받는다.

* **Endpoint:** `POST /login`
* **Content-Type:** `application/x-www-form-urlencoded`
* **Request Parameters (Form Data):**

| 필드명 | 타입 | 필수 여부 | 설명 | 예시 |
|---|---|:---:|---|---|
| `username` | string | Y | 사번 (`employee_num`) | `EMP-001`, `ADMIN-001` |
| `password` | string | Y | 비밀번호 | `pass1234`, `adminpass` |

* **Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5...",
  "token_type": "bearer",
  "role": "user",
  "name": "홍길동"
}
```

* **Error Responses:**
  * `401 Unauthorized`: 사번 또는 비밀번호 불일치

---

## 2. 챗봇 API (Chat)

### 2.1 AI 보안 게이트웨이 채팅 요청
사용자의 원본 프롬프트를 입력받아 **3단계 보안 파이프라인(Phase 1~3)**을 거친 후, 마스킹된 프롬프트를 외부 AI로 전송하고, 역치환된 최종 안전한 응답을 반환한다.

* **Endpoint:** `POST /chat`
* **Auth:** Required (Bearer Token)
* **Content-Type:** `application/json`
* **Request Body (JSON):**

```json
{
  "prompt": "DWG-2026-X1 도면의 공차 기준을 알려주세요."
}
```

* **Response (200 OK):** (정상 처리 및 마스킹/역치환 성공 시)
```json
{
  "response": "해당 도면(DWG-2026-X1)의 공차 기준은 ±0.005mm 입니다. 더 필요하신 정보가 있습니까?"
}
```
*(참고: 응답 헤더에 `X-Mask-Session-Id`가 포함되며, 이는 Redis 세션 트래킹용으로 사용된다.)*

* **Error & Security Block Responses:**
  * `403 Forbidden`: 보안 정책 위반(프롬프트 인젝션 등)으로 게이트웨이에서 자체 차단됨
  * `401 Unauthorized`: 토큰 만료 또는 유효하지 않음
  * `503 Service Unavailable`: 로컬 Ollama 모델 연결 실패 또는 외부 AI 서버 에러
  * `504 Gateway Timeout`: 로컬 LLM 추론 시간 초과 (기본 60초)

---

## 3. 관리자 전용 API (Admin Only)

토큰의 `role`이 **`admin`**인 경우에만 접근 가능한 API이다. 일반 `user` 토큰으로 접근 시 `403 Forbidden` 에러를 반환한다.

### 3.1 보안 이벤트 로그 조회
AI 게이트웨이가 탐지한 모든 통과, 마스킹, 차단 내역을 시간순으로 조회한다.

* **Endpoint:** `GET /admin/logs`
* **Auth:** Required (Bearer Token, Admin Only)
* **Response (200 OK):**

```json
{
  "total": 1,
  "logs": [
    {
      "log_id": 1,
      "employee_num": "EMP-001",
      "timestamp": "2026-06-05T15:30:45+09:00",
      "action": "CHAT_REQUEST",
      "detected_threat": "CONFIDENTIAL_DATA_LEAK (DWG-2026-X1)",
      "status": "MASKED",
      "original_prompt": "DWG-2026-X1 도면 검토해줘",
      "masked_prompt": "__MASK_DWG_a1b2c3d4__ 도면 검토해줘",
      "mapping_info": "{\"__MASK_DWG_a1b2c3d4__\": \"DWG-2026-X1\"}"
    }
  ]
}
```

### 3.2 보안 로그 CSV 다운로드
기록된 전체 보안 로그를 CSV 파일 형태로 다운로드한다.

* **Endpoint:** `GET /admin/export-csv`
* **Auth:** Required (브라우저 다운로드 특성상 프론트엔드에서 파라미터나 쿠키로 토큰 처리 필요)
* **Response (200 OK):**
  * `Content-Type: text/csv`
  * 파일 다운로드 응답 (`gateway_logs.csv`)

### 3.3 보안 로그 데이터 초기화 (테스트용)
`security_logs` 테이블의 모든 데이터를 삭제한다. 시연 및 테스트 환경을 위해 제공된다.

* **Endpoint:** `DELETE /admin/clear-logs`
* **Auth:** Required (Bearer Token, Admin Only)
* **Response (200 OK):**
```json
{
  "message": "Logs cleared successfully"
}
```

---

## 에러 코드 요약 정리

API 연동 시 프론트엔드 애플리케이션에서 반드시 처리해야 하는 주요 HTTP 상태 코드이다.

| HTTP 상태 코드 | 의미 | 프론트엔드 처리 권장사항 |
|---|---|---|
| `200 OK` | 정상 처리 | 응답 텍스트를 정상적으로 말풍선에 출력 |
| `401 Unauthorized` | 인증 실패 / 토큰 만료 | 강제 로그아웃 처리 후 로그인 페이지로 리다이렉트 |
| `403 Forbidden` | 보안 차단 / 권한 없음 | 사용자에게 '보안 차단' 알림을 붉은색 배너 등으로 눈에 띄게 안내 |
| `500 Internal Error` | 서버 내부 로직 에러 | 잠시 후 다시 시도해달라는 안내 메시지 출력 |
| `503 / 504` | AI 서버/Ollama 통신 실패 또는 지연 | "AI 엔진 준비 중" 또는 "관리자 문의" 메시지 출력 |

---

### 📚 전체 문서 목차
1. [**메인 페이지 (README)**](../README_KO.md)
2. [**시스템 아키텍처**](./ARCHITECTURE.md)
3. [**설치 및 실행 가이드**](./SETUP_GUIDE.md)
4. [**보안 테스트 가이드**](./SECURITY_TESTING.md)
5. [**API 명세서**](./API_REFERENCE.md) 📍 *현재 페이지*
