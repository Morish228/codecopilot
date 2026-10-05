<div align="center">

# 🤖 CodeCopilot

### AI-Powered Coding Assistant — Think, Plan, Execute

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestrated-FF6B35?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)

**CodeCopilot is an intelligent agentic coding assistant that understands your codebase, plans multi-step actions, runs tools safely, and helps you ship software faster — powered by the LLM of your choice.**

[📖 Docs](docs/) · [⚡ Quick Start](#-step-by-step-local-setup-guide) · [🐛 Report Bug](https://github.com/Morish228/codecopilot/issues)

</div>

---

## ✨ Features

| Feature | Description |
| :--- | :--- |
| 🧠 **Agentic Reasoning** | LangGraph-powered agent loop that thinks step-by-step before acting (Plan $\to$ Act $\to$ Observe) |
| 🔍 **Codebase Understanding** | Full AST symbol indexing (Tree-sitter) & semantic retrieval using `pgvector` embeddings |
| 🛠️ **Autonomous Tools** | File reading, deterministic patch editing (`apply_patch`), regex grep, and linting |
| 🧪 **Self-Testing** | Automatically executes test suites and self-heals code if tests fail |
| 🔄 **Multi-Model Support** | Works with Google Gemini, OpenAI GPT-4, and Anthropic Claude via LiteLLM |
| 🎯 **Smart Model Routing** | Automatically assigns the right model tier for planning, coding, or summarization |
| ✅ **Approval Workflows** | Critical operations require human confirmation before execution |
| 🌐 **Interactive Web UI** | Modern browser chat interface with live workspace switching |

---

## 🥊 How CodeCopilot Differs From Other AI Tools

Unlike passive chat interfaces that only process copy-pasted text, **CodeCopilot is an autonomous software engineering agent** that operates directly on your local workspace:

| Capability | Standard AI Chatbots (ChatGPT / Claude Web) | Basic Copilot Plugins | 🤖 CodeCopilot Agent |
| :--- | :--- | :--- | :--- |
| **Codebase Awareness** | ❌ Manual copy-pasting (1–2 files at a time) | ⚠️ Limited to active editor tab | ✅ **Full Codebase Indexing** (AST Tree-sitter & `pgvector` semantic search) |
| **Autonomous Tool Execution** | ❌ None (Text-only output) | ❌ Cannot execute external tools | ✅ **Multi-Tool Agent Loop** (File read, patch writing, grep, linting) |
| **Automated Code Editing** | ❌ User must manually copy & paste code | ⚠️ Inline autocomplete only | ✅ **Deterministic Multi-File Patching** (`apply_patch` directly modifies files) |
| **Self-Verification & Testing** | ❌ Cannot verify if code works | ❌ Cannot run tests | ✅ **Automated Test Execution & Self-Healing** (Runs `pytest` & auto-fixes errors) |
| **Model Flexibility & Routing** | ❌ Locked to one provider | ❌ Locked to vendor model | ✅ **Smart Multi-Model Routing** (Routes tasks dynamically between Gemini, GPT-4, Claude) |
| **Security & Human-in-the-Loop** | ❌ No safety controls | ❌ No approval gating | ✅ **Configurable Approval Workflows** for critical write operations |
| **Privacy & Self-Hosting** | ❌ Cloud-only proprietary SaaS | ❌ Proprietary SaaS | ✅ **100% Self-Hosted & Open Source** (Your code stays on your machine) |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│               User (Browser Web UI / CLI)           │
└────────────────────────┬────────────────────────────┘
                         │  HTTP / SSE
┌────────────────────────▼────────────────────────────┐
│              FastAPI Control Plane API               │
│         /v1/runs  /v1/tools  /health  /metrics      │
└──────────┬────────────────────────────┬─────────────┘
           │                            │
┌──────────▼──────────┐    ┌────────────▼────────────┐
│   LangGraph Agent   │    │    PostgreSQL + pgvector  │
│  (Plan → Act → Obs) │    │   (Run history + index)  │
└──────────┬──────────┘    └─────────────────────────┘
           │
┌──────────▼──────────┐    ┌─────────────────────────┐
│   LiteLLM Router    │    │         Redis            │
│  Gemini / GPT-4 /   │    │   (Session cache &       │
│      Claude         │    │    in-memory fallback)   │
└──────────┬──────────┘    └─────────────────────────┘
           │
┌──────────▼──────────┐
│   Tool Sandbox      │
│  (Docker / Local)   │
└─────────────────────┘
```

---

## ⚡ Step-by-Step Local Setup Guide

Follow this guide to run CodeCopilot locally on your computer and connect it to any project on your machine.

### 📋 Prerequisites
- **Python 3.12+** installed on your system ([Download Python](https://www.python.org/downloads/))
- **Astral `uv`** (Recommended for ultra-fast setup):
  - Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - Mac/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **PostgreSQL Database** (Local via Docker OR a free cloud database from [Render](https://render.com) / [Neon](https://neon.tech) / [Supabase](https://supabase.com))
- An **LLM API Key** (e.g. Free [Google Gemini API Key](https://aistudio.google.com/apikey) or OpenAI/Anthropic key)

---

### Step 1: Download / Clone the Repository

**Option A: Using Git (Recommended)**
```bash
git clone https://github.com/Morish228/codecopilot.git
cd CodeCopilot
```

**Option B: Download ZIP**
1. Click the green **Code** button at the top of the GitHub repository.
2. Select **Download ZIP**.
3. Extract the ZIP folder on your computer and open terminal in the `CodeCopilot` folder:
   ```bash
   cd CodeCopilot
   ```

---

### Step 2: Install Dependencies

Using `uv` (Recommended):
```bash
uv pip install -e ".[dev]"
```

*Or using standard pip:*
```bash
pip install -e ".[dev]"
```

---

### Step 3: Configure Environment Variables (`.env`)

Create your `.env` file by copying the example:

```bash
# Windows PowerShell:
Copy-Item .env.example .env

# Mac / Linux:
cp .env.example .env
```

Open `.env` in your code editor and configure:

```env
# 1. Database Connection (Use local Postgres OR free cloud Postgres like Render/Neon/Supabase)
DATABASE_URL=postgresql+asyncpg://user:password@hostname:5432/dbname

# 2. LLM API Key (Add your API Key)
GEMINI_API_KEY=AIzaSy...
# Or for OpenAI:
# OPENAI_API_KEY=sk-...

# 3. Model Configuration (Default is Gemini)
ROUTING_CONFIG_PATH=routing.config.gemini.json
ROUTING_DEFAULT_MODEL=gemini/gemini-3.1-flash-lite

# 4. Sandbox Backend (Set to 'local' for running without Docker)
SANDBOX_BACKEND=local
```

---

### Step 4: Start the CodeCopilot Server

Run the server command:

```bash
uv run coding-assistant serve
```
*(or `python -m coding_assistant serve`)*

You will see the startup confirmation:
```text
🚀 Starting CodeCopilot server at http://127.0.0.1:8000
📖 API documentation at http://127.0.0.1:8000/docs
INFO: Application startup complete.
```

---

### Step 5: Open Web UI & Point to Any Project

1. Open your browser and go to:
   👉 **`http://localhost:8000`**

2. In the left sidebar under **`WORKSPACE`**, enter the full folder path of the project you want the AI to work on:
   - **Windows Example**: `C:\Users\username\Projects\MyAwesomeApp`
   - **Mac/Linux Example**: `/home/username/projects/MyAwesomeApp`

3. Click the **`Set Workspace`** button.

---

## 🎯 Usage & Example Prompts

Once your workspace is connected, you can ask CodeCopilot anything about your project:

### 1. 🔍 Codebase Exploration & Architecture
> *"Explain this repo, its file structure, and its main entry points."*
> *"List all API routes and authentication middleware in this project."*

### 2. 🐛 Bug Finding & Security Audit
> *"Scan this project for potential memory leaks, unhandled exceptions, and security vulnerabilities."*
> *"Why is the user login session expiring prematurely in auth.py?"*

### 3. ✍️ Autonomous Code Implementation
> *"Add a new payment webhook handler in routes/payments.py to process Stripe events."*
> *"Refactor the database queries in services/user_service.py to use async SQLAlchemy."*

### 4. 🧪 Automated Testing & Fixing
> *"Generate comprehensive pytest unit tests for the functions in utils/parser.py."*

---

## 💻 Terminal CLI Chat (Alternative)

You can also use CodeCopilot directly from your terminal:

```bash
uv run coding-assistant chat --workspace "C:\path\to\your\project"
```

Available slash commands in CLI:
- `/workspace <path>` — Switch project folder on the fly
- `/status` — View active models, tokens, and database status
- `/help` — List all commands
- `/exit` — Exit CLI

---

## 🔑 LLM Provider Options

| Provider | Environment Variable | Model Example | Get Key |
| :--- | :--- | :--- | :--- |
| **Google Gemini** | `GEMINI_API_KEY` | `gemini/gemini-3.1-flash-lite`, `gemini/gemini-3.5-flash` | [Google AI Studio](https://aistudio.google.com/apikey) |
| **OpenAI** | `OPENAI_API_KEY` | `gpt-4o`, `gpt-4o-mini` | [OpenAI Console](https://platform.openai.com/api-keys) |
| **Anthropic** | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet` | [Anthropic Console](https://console.anthropic.com/) |

---

## 📁 Project Structure

```
CodeCopilot/
├── src/coding_assistant/
│   ├── api/            # FastAPI REST & SSE endpoints
│   ├── intelligence/   # LangGraph agent orchestration & planning
│   ├── tools/          # Autonomous tool handlers (grep, AST search, patch)
│   ├── sandbox/        # Sandbox execution engine (Docker & Local)
│   ├── routing/        # LiteLLM capability-aware model router
│   ├── db/             # SQLAlchemy asyncpg models & session management
│   ├── services/       # In-memory & Redis cache, run worker
│   └── observability/  # OpenTelemetry tracing & Prometheus metrics
├── web/                # Clean browser chat interface (HTML/CSS/JS)
├── docs/               # Complete phase documentation
├── tests/              # Pytest test suite (64+ tests)
├── Dockerfile          # Production container image
└── pyproject.toml      # Project manifest & dependencies
```

---

## 📄 License

This project is open source under the MIT License. See [LICENSE](LICENSE) for details.

<div align="center">

Built with ❤️ using **FastAPI**, **LangGraph**, and **LiteLLM**

⭐ **Star on GitHub**: [Morish228/codecopilot](https://github.com/Morish228/codecopilot)

</div>

