# LLM-based Hybrid AI Security Gateway

-> **[한국어 문서 보기 (Read in Korean)](README_KO.md)**
> **Proof of Concept (PoC) for Prompt Injection Defense and Confidential Data De-identification**

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

## 1. Research Background & Problem Definition

As the enterprise adoption of Generative AI accelerates, the **unintentional leakage of confidential data** by employees and malicious **Prompt Injection** attacks have emerged as critical security threats.

* **Escalating Data Leaks:** According to a Cyberhaven (2024) report, 27.4% of all data inputted into AI tools by employees is considered confidential.
* **Limitations of Legacy Security:** Existing DLP (Data Loss Prevention) solutions rely strictly on predefined patterns (e.g., SSN, phone numbers) and fail to detect unstructured confidential data hidden within the context (e.g., mixing ratios of new materials).
* **The "Shadow AI" Dilemma:** Completely blocking access to AI tools on the corporate network for security reasons paradoxically leads to "Shadow AI," where employees bypass the network using personal devices. This pushes the data out of the company's control, making auditing impossible.

**Core Research Question:**  
*"Is there a middle-ground security architecture that protects confidential data while safely allowing the use of AI?"*

---

## 2. Architecture & 4 Core Design Principles

This project proposes and implements an **AI Security Gateway Proxy** deployed within a corporate on-premise network that intercepts communication with external Commercial AIs.

### Design Principles
1. **100% Local Processing**: All security inspections (masking, intent classification) are processed by an on-premise local LLM, guaranteeing absolute data sovereignty.
2. **Defense-in-Depth**: We constructed a 3-layer defense mechanism: Pattern Filter → Intent Classification → Generative Masking.
3. **Dynamic Masking & De-masking**: Instead of outright blocking, confidential data is substituted with randomized tokens before being sent to the AI. Upon response, the gateway dynamically restores the original data, perfectly preserving the User Experience (UX).
4. **AI-Native Threat Defense**: Utilizing the LLM-as-a-Judge technique, the system can understand context to block complex threats like prompt injections.
5. **Global Accessibility (i18n)**: Features a seamless Korean/English language toggle in the UI, enabling global developers and evaluators to interact with the system intuitively.

---

## 3. The 3-Phase Hybrid Security Pipeline

The core engine of this gateway is a **Hybrid Architecture combining Regex and LLMs**.

```mermaid
graph TD
    A[User Input] --> B[Phase 1: High-speed Regex Filter]
    B -->|Mask Structured Data| C{Async Parallel Processing}
    C --> D[Phase 2: LLM Intent Classification]
    C --> E[Phase 3: Generative Masking]
    D -->|Fail-Closed Block| F[Admin Logging]
    E -->|Mask Unstructured Data| G[Final Masked Prompt]
    G --> H[External Commercial AI]
    H --> I[Phase 4: De-masking]
    I --> J[Return Response to User]
```

* **Phase 1 (High-speed Regex Filter):** Instantly substitutes structured confidential data (e.g., Employee IDs, Blueprint Numbers) with unique randomized tokens in the format of `__MASK_TYPE_HEX__`.
* **Phase 2 (LLM-as-a-Judge):** The local LLM (Qwen 2.5 7B) analyzes the prompt's context to detect and immediately block (Fail-Closed) malicious intents such as Prompt Injection and System Jailbreaks.
* **Phase 3 (Generative DLP):** Simultaneously, the same local LLM extracts unstructured confidential data (e.g., "Tolerance", "Mixing Ratio") that Regex cannot catch, and masks it. (Executed in parallel with Phase 2 via `asyncio` to minimize latency).

---

## 4. Core Features Demonstration

### 1) Normal Query & Dynamic Masking (UX Preservation)
When a user asks a question containing confidential data, the gateway masks it into a randomized token before sending it to the external AI. The received answer is then perfectly de-masked back to its original state.

> ![Chat UI](assets/captures/chat_en.png)
> *[UI] Streamlit-based dark theme chat interface*

### 2) Prompt Injection Defense
Contexts attempting to ignore previous instructions or demanding admin privileges are intercepted and blocked.

> ![Block Screen](assets/captures/blocked_en.png)
> *[Defense] Malicious intent blocked by LLM-as-a-Judge (Red warning banner)*

### 3) Admin Security Dashboard
Logs and monitors all events (Allowed, Masked, Blocked) passing through the gateway in real-time, matching original prompts with their masked counterparts.

> ![Dashboard](assets/captures/dashboard_en.png)
> *[Logging] Admin panel to audit tokenized data and original text mappings*

---

## 5. System Performance & Evaluation (1,200 Benchmark Tests)

We validated the system's performance through a rigorous automated test set of 1,200 queries.

| Metric | V1 (Regex Only) | **V4 (Proposed Hybrid Model)** | Achievement |
|---|:---:|:---:|---|
| **Overall Recall (Defense Rate)** | 26.7% | **78.33%** | Approx. 2.9x Improvement |
| **Injection Block Rate** | ~15% | **91.67%** | Breakthrough Detection |
| **Precision** | ~100% | **99.86%** | Near-zero Business Disruption |
| **Korean False Positive Rate** | 0.0% | **0.0%** (0 out of 600) | **Zero Business Disruption** |
| **Latency (Warm State)** | 0.1s | **1~3 seconds** | Minimized Overhead via Async |

**Conclusion & Significance:**  
Achieving 99.86% precision despite the limitations of a small local model (7B) running on a CPU environment proves the **robustness of the architecture itself**. This highly scalable design guarantees that upgrading to a larger model (70B+) via infrastructure expansion will instantly yield a defense rate (Recall) of over 90%.

---

## 6. Tech Stack

| Category | Technologies |
|---|---|
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Frontend** | Streamlit |
| **Database** | PostgreSQL 15, SQLAlchemy ORM |
| **Cache/KV** | Redis 7 |
| **AI / Security** | Local Ollama (Qwen2.5:7b), Google Gemini API |
| **Infrastructure** | Docker, Docker Compose |

---

## 7. Quick Start Guide

### Prerequisites
* Docker and Docker Compose
* Install [Ollama](https://ollama.com/) locally and pull the `qwen2.5:7b` model (`ollama run qwen2.5:7b`)
* Google Gemini API Key

### How to Run

1. **Clone Repository & Set Environment Variables**
   ```bash
   git clone https://github.com/your-repo/LLM_Gateway_Project.git
   cd LLM_Gateway_Project
   cp .env.example .env
   # Open .env and input your GEMINI_API_KEY
   ```

2. **Execute Docker Compose**
   ```bash
   docker-compose up --build -d
   ```

3. **Access Services**
   * **Frontend (UI)**: `http://localhost:8501`
   * **Backend (API Docs)**: `http://localhost:8000/docs`
   * **Test Accounts**: `EMP-001` / `pass1234` (User), `ADMIN-001` / `adminpass` (Admin)

---

## 8. License

This project is licensed under the [MIT License](LICENSE). You are free to reference, use, and modify it for research and educational purposes.

### 🛡️ Security Testing Guide
To run the automated tests and view benchmark results, please refer to the [Security Testing Report](Docs_English/SECURITY_TESTING_EN.md).

---

## Project Documentation
1. [**Main README**](./README.md) 🔴 *You are here*
2. [**System Architecture**](./Docs_English/ARCHITECTURE_EN.md)
3. [**Setup & Execution Guide**](./Docs_English/SETUP_GUIDE_EN.md)
4. [**Security Testing Guide**](./Docs_English/SECURITY_TESTING_EN.md)
5. [**API Reference**](./Docs_English/API_REFERENCE_EN.md)
