# AutoCore AI Security Gateway API Reference

This document defines the RESTful API specifications for frontend applications and external clients to communicate with the AutoCore Gateway Backend (FastAPI).

> **Base URL:** `http://localhost:8000` (Docker Environment: `http://api:8000`)  
> **Swagger UI:** `http://localhost:8000/docs` (Auto-generated documentation)

---

## Authentication

All protected endpoints (`/chat`, `/admin/*`) use **JWT (JSON Web Token)**-based **Bearer Token** authentication.
You must include the token in the request header as follows:
```http
Authorization: Bearer <YOUR_ISSUED_JWT_TOKEN>
```

---

## 1. Auth API

### 1.1 Employee Login & Token Issuance
Authenticates using the employee ID and password, and issues a JWT Access Token.

* **Endpoint:** `POST /login`
* **Content-Type:** `application/x-www-form-urlencoded`
* **Request Parameters (Form Data):**

| Field | Type | Required | Description | Example |
|---|---|:---:|---|---|
| `username` | string | Y | Employee ID (`employee_num`) | `EMP-001`, `ADMIN-001` |
| `password` | string | Y | Password | `pass1234`, `adminpass` |

* **Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5...",
  "token_type": "bearer",
  "role": "user",
  "name": "John Doe"
}
```

* **Error Responses:**
  * `401 Unauthorized`: Incorrect Employee ID or password.

---

## 2. Chatbot (Chat) API

### 2.1 AI Security Gateway Chat Request
When the user's original prompt is submitted, the backend passes it through the **3-Phase Security Pipeline (Phase 1~3)**, forwards the masked prompt to the external AI, and returns the final safe, de-masked response.

* **Endpoint:** `POST /chat`
* **Auth:** Required (Bearer Token)
* **Content-Type:** `application/json`
* **Request Body (JSON):**

```json
{
  "prompt": "Please explain the tolerance standard for the DWG-2026-X1 blueprint."
}
```

* **Response (200 OK):** (Upon successful processing and masking/de-masking)
```json
{
  "response": "The tolerance standard for the specified blueprint (DWG-2026-X1) is ±0.005mm. Do you have any further questions?"
}
```
*(Note: The response header includes `X-Mask-Session-Id`, which is used for Redis session tracking.)*

* **Error & Security Block Responses:**
  * `403 Forbidden`: Blocked by the gateway due to a security policy violation (e.g., Prompt Injection).
  * `401 Unauthorized`: Token expired or invalid.
  * `503 Service Unavailable`: Failed to connect to the local Ollama model or external AI server error.
  * `504 Gateway Timeout`: Local LLM inference timeout (default 60 seconds).

---

## 3. Admin-Only API

The following APIs are accessible only if the token's `role` is **`admin`**. Accessing them with a standard `user` token will return a `403 Forbidden` error.

### 3.1 Retrieve Security Event Logs
Fetches a chronological history of all events (Allowed, Masked, Blocked) detected by the AI gateway.

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
      "original_prompt": "Please review the DWG-2026-X1 blueprint",
      "masked_prompt": "Please review the __MASK_DWG_a1b2c3d4__ blueprint",
      "mapping_info": "{\"__MASK_DWG_a1b2c3d4__\": \"DWG-2026-X1\"}"
    }
  ]
}
```

### 3.2 Export Security Logs to CSV
Downloads all recorded security logs as a CSV file.

* **Endpoint:** `GET /admin/export-csv`
* **Auth:** Required (Handled by the frontend due to browser download characteristics)
* **Response (200 OK):**
  * `Content-Type: text/csv`
  * File download response (`autocore_logs.csv`)

### 3.3 Clear Security Logs (For Testing)
Deletes all data in the `security_logs` table. Intended for demonstration and testing purposes only.

* **Endpoint:** `DELETE /admin/clear-logs`
* **Auth:** Required (Bearer Token, Admin Only)
* **Response (200 OK):**
```json
{
  "message": "Logs cleared successfully"
}
```

---

## Error Code Summary

Key HTTP status codes that must be handled by the frontend application during API integration.

| HTTP Status Code | Meaning | Frontend Handling Recommendation |
|---|---|---|
| `200 OK` | Success | Process normally and output the result |
| `401 Unauthorized` | Auth Failed / Token Expired | Force logout and redirect to the login page |
| `403 Forbidden` | Security Block / No Permission | Display a prominent red warning banner notifying the user of the 'Security Block' |
| `500 Internal Error` | Server Internal Logic Error | Advise the user to try again later |
| `503 / 504` | AI Server/Ollama Connection Failure or Delay | Display "Preparing AI Engine" or "Contact Administrator" |
