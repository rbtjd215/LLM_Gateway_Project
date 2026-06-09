# LLM Security Gateway Setup & Execution Guide

This guide provides instructions on how to set up and run the LLM Gateway (PoC) environment on your local machine.

---

## 1. Prerequisites

Before running the system, ensure the following software is installed on your machine:

* **[Docker Desktop](https://www.docker.com/products/docker-desktop/)**: For container orchestration (Version 20.10 or higher recommended).
* **[Ollama](https://ollama.com/)**: Engine for running the local LLM.
* **Google Gemini API Key**: Can be issued for free at [Google AI Studio](https://aistudio.google.com/).
* **Git**: To clone the repository.

---

## 2. Preparing Ollama and the Local Model

You need to download the local model that will process the security pipeline (Phase 2 & 3). (This is a one-time setup).

1. Launch Ollama. (Mac/Windows: Run the application, Linux: `systemctl start ollama`).
2. Open a terminal and pull the `qwen2.5:7b` model using the following command:
   ```bash
   ollama run qwen2.5:7b
   ```
   *The download is complete when the `>>>` prompt appears in your terminal. Press `Ctrl+D` to exit the prompt.*

---

## 3. Cloning the Repository & Setting Environment Variables

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-repo/LLM_Gateway_Project.git
   cd LLM_Gateway_Project
   ```

2. **Create the Environment Variables File**
   Copy the `.env.example` file located in the root directory to create your `.env` file.
   ```bash
   cp .env.example .env
   ```

3. **Modify the `.env` File**
   Open the `.env` file in an editor and adjust the values according to your environment.
   ```env
   # [Required] Google Gemini API Key
   GEMINI_API_KEY=AIzaSy...insert_your_key_here...

   # [Optional] Security Engine Mode (Default: HF_PIPELINE)
   # HF_PIPELINE : V4 Hybrid Pipeline with Regex + LLM (Recommended)
   # REGEX       : V1 High-speed Regex-only mode (Useful for testing when Ollama is off)
   ENGINE_MODE=HF_PIPELINE

   # [Optional] Local Ollama Address (Keep host.docker.internal when using Docker)
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   ```

---

## 4. Running the Full Service via Docker Compose

Run the following command in the root directory to spin up all 4 containers (API, Frontend, DB, Redis).

```bash
docker-compose up --build -d
```
* `-d`: Runs the containers in the background (detached mode).
* `--build`: Rebuilds the images if there are changes in the Dockerfile.

To verify that the system is running correctly, check the logs with the following command:
```bash
docker-compose logs -f api
```
*(If you see the message `[System] Gateway Ready ✓` in the logs, it was successful.)*

---

## 5. Accessing Services & Test Accounts

Once the containers are running, open your web browser and navigate to the following addresses:

* **Web UI (Streamlit)**: [http://localhost:8501](http://localhost:8501)
* **API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Default Test Accounts

When the system boots for the first time, seed data is automatically inserted into the database.

| Role | Employee ID | Password | Purpose |
|---|---|---|---|
| Standard Employee | `EMP-001` | `pass1234` | Chat testing and dynamic masking verification |
| Standard Employee | `EMP-002` | `pass5678` | Account isolation testing |
| Security Admin | `ADMIN-001` | `adminpass` | Security event log monitoring (Dashboard) |

---

## 6. Shutdown & Data Reset

* **Shutdown Servers (Keep Data):**
  ```bash
  docker-compose down
  ```

* **Shutdown Servers & Completely Delete DB (Factory Reset):**
  Use this when you want to completely erase the DB and Redis volume data.
  ```bash
  docker-compose down -v
  ```

---

## 7. Troubleshooting (FAQ)

### Q. I get a `503 Service Unavailable (Ollama connection failed)` error when sending a chat.
> **A.** This occurs when the Docker container cannot access Ollama on your host PC.
> 1. Ensure Ollama is running on your host PC (check your system tray icon).
> 2. Open your terminal and run `curl http://localhost:11434`. Ensure it returns `Ollama is running`.
> 3. If you are on Windows, try setting the system environment variable `OLLAMA_HOST` to `0.0.0.0` and restart Ollama.

### Q. I modified the code (FastAPI), but it doesn't apply immediately.
> **A.** Although hot-reloading (`--reload`) is enabled in `docker-compose.yml`, file change detection may not pass into the container on certain OS environments (like Windows). In this case, simply restart the API server:
> ```bash
> docker-compose restart api
> ```

### Q. I see an error saying "GEMINI_API_KEY is not set".
> **A.** This means you haven't created the `.env` file, or there is a typo inside it. Make sure you copied `.env.example` to `.env`.

---

### Project Documentation
1. [**Main README**](../README.md)
2. [**System Architecture**](./ARCHITECTURE_EN.md)
3. [**Setup & Execution Guide**](./SETUP_GUIDE_EN.md) 🔴 *You are here*
4. [**Security Testing Guide**](./SECURITY_TESTING_EN.md)
5. [**API Reference**](./API_REFERENCE_EN.md)
