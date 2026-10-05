# Getting Started with CodeCopilot

A step-by-step guide to set up and use the intelligent coding assistant.

## Table of Contents
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [Using the Chat Interface](#using-the-chat-interface)
- [Using the HTTP API](#using-the-http-api)
- [Troubleshooting](#troubleshooting)

## System Requirements

- **Python:** 3.12 or higher
- **Docker:** For running PostgreSQL and Redis services
- **Disk Space:** ~500MB for dependencies + space for your codebase
- **Network:** Internet access for LLM API calls
- **API Keys:** At least one of OpenAI, Anthropic, or Google Gemini

## Installation

### Step 1: Clone & Navigate
```bash
cd /path/to/CodeCopilot
```

### Step 2: Start Infrastructure Services

Start PostgreSQL and Redis using Docker Compose:

```bash
docker compose up -d
```

Verify services are running:
```bash
docker compose ps
# Should show postgres and redis as "Up"
```

Build the sandbox image:
```bash
docker compose build sandbox-image
```

### Step 3: Configure Environment

Copy the example configuration:
```bash
cp .env.example .env
```

Edit `.env` and add your API credentials. At minimum, choose one:

**For OpenAI:**
```
OPENAI_API_KEY=sk-...
```

**For Anthropic Claude:**
```
ANTHROPIC_API_KEY=sk-ant-...
```

**For Google Gemini:**
```
GEMINI_API_KEY=...
```

Other useful settings:
```
# Default model to use (claude-3-5-sonnet, gpt-4, gemini-2.0-flash, etc.)
DEFAULT_MODEL=claude-3-5-sonnet

# Enable features
ENABLE_SANDBOX=true
ENABLE_APPROVAL=true

# Security
AUTH_REQUIRED=false  # Set true for production
LOG_LEVEL=INFO
```

### Step 4: Install Python Dependencies

```bash
pip install -e ".[dev]"
```

This installs CodeCopilot in editable mode with development dependencies.

## Running the Server

### Terminal 1: Start the API Server

```bash
coding-assistant serve
```

Output should show:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

The API is now available at **http://127.0.0.1:8000/docs** (Swagger UI)

## Using the Chat Interface

### Terminal 2: Start Interactive Chat

```bash
coding-assistant chat --workspace /path/to/your/project
```

You should see:
```
Connected to http://127.0.0.1:8000
Workspace: /path/to/your/project
Type messages or slash commands (type /help for list)

You: 
```

### Chat Examples

**Example 1: Understand your codebase**
```
You: What are the main entry points in this project?
Assistant: [Analyzes code and responds...]
```

**Example 2: Find specific files**
```
You: Show me all test files
Assistant: [Lists test files with paths...]
```

**Example 3: Get explanations**
```
You: Explain the architecture of the API layer
Assistant: [Provides detailed explanation...]
```

### Slash Commands

| Command | Usage | Example |
|---------|-------|---------|
| `/workspace` | Change project directory | `/workspace /path/to/other/repo` |
| `/status` | Show current configuration | `/status` |
| `/help` | List available commands | `/help` |
| `/exit`, `/quit` | Exit the chat | `/exit` |

### Chat Options

```bash
# Use specific API server
coding-assistant chat --api-url http://192.168.1.100:8000

# Add authentication token
coding-assistant chat --token your_bearer_token

# Set timeout for operations
coding-assistant chat --timeout 60

# Disable colored output
coding-assistant chat --no-color
```

## Using the HTTP API

### Basic Request

Create a new agent run via HTTP:

```bash
curl -X POST http://127.0.0.1:8000/v1/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "workspace_root": "/path/to/repo",
    "message": "List Python files in the src directory"
  }'
```

### Python Example

```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/v1/runs",
    json={
        "workspace_root": "/path/to/repo",
        "message": "What are the dependencies?"
    }
)

run_data = response.json()
print(f"Run ID: {run_data['id']}")
print(f"Status: {run_data['status']}")
print(f"Response: {run_data.get('response', 'Processing...')}")
```

### Fetch Results

```bash
curl http://127.0.0.1:8000/v1/runs/{run_id}
```

### API Documentation

Full API documentation with interactive examples:
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

## Troubleshooting

### Docker Services Not Starting

```bash
# Check if Docker daemon is running
docker ps

# View logs
docker compose logs postgres
docker compose logs redis

# Rebuild
docker compose down
docker compose up -d --build
```

### "Connection refused" Error

Ensure the server is running:
```bash
# Terminal 1 should show "Application startup complete"
ps aux | grep "coding-assistant serve"
```

### API Key Issues

- Verify `.env` file has correct keys without extra spaces
- Check API quota and account status with your provider
- Test key validity: `echo $OPENAI_API_KEY` (should show key, not error)

### Python Version Mismatch

```bash
# Check current Python version
python --version

# Use Python 3.12+ explicitly
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### "Module not found" Error

Reinstall dependencies:
```bash
pip install -e ".[dev]" --force-reinstall
```

### Workspace Not Found

Ensure workspace path exists and is readable:
```bash
# Verify path
ls -la /path/to/your/repo

# Use absolute path (not relative)
coding-assistant chat --workspace $(pwd)/my-project
```

## What's Next?

- Review [Architecture Overview](docs/phase-1-core-runtime.md)
- Explore [Tool System Documentation](docs/phase-3-tool-system.md)
- Check [Approval Workflows](docs/phase-6-approval-workflow.md)
- Read full [Documentation](docs/)

## Need Help?

- Check logs: `tail -f /tmp/coding_assistant.log`
- View API status: `curl http://127.0.0.1:8000/health`
- Enable debug logging: Add `LOG_LEVEL=DEBUG` to `.env`
