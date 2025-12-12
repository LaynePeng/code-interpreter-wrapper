# Code Interpreter Wrapper for Dify

This project provides a standard API wrapper for `agentcube` (or a mock sandbox environment) designed to be integrated into **Dify** as a Custom Tool (API-based). It allows your Dify agents to create sandboxes, execute Python code/shell commands, and manage files.

## Features

*   **Dify Compatible**: Comes with a ready-to-use OpenAPI schema (`external-codeinterpreter.json`).
*   **Sandbox Management**: Create (`/create_sandbox`) and destroy (`/stop_sandbox`) isolated environments.
*   **Execution**: Run Python code (`/run_code`) and Shell commands (`/execute_command`).
*   **File Management**: Upload files from URLs (`/upload_file`), write content directly to files (`/write_file`), and download generated files (`/download_file`).

## Prerequisites

*   Python 3.8+
*   `pip`
*   A running [Dify](https://dify.ai/) instance (Cloud or Self-hosted)

## Quick Start

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone <repository_url>
cd openai-tool--codeinterpreter-wrapper
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the API Service

Start the server. By default, it runs on port `8000`.

```bash
# Using Python
python codeinterpreter-wrapper.py

# OR using uvicorn directly
uvicorn codeinterpreter-wrapper:app --host 0.0.0.0 --port 8000
```

Ensure this service is accessible from your Dify instance (e.g., via a public IP, or internal network if self-hosted).

## Integration with Dify

This is the main purpose of this project. Follow these steps to register this tool in Dify.

1.  **Locate the Schema**: Open the file `external-codeinterpreter.json` in this repository.
2.  **Go to Dify**:
    *   Navigate to **Tools** > **Custom**.
    *   Click **Create Custom Tool**.
3.  **Configure Tool**:
    *   **Name**: `CodeInterpreter` (or any name you prefer).
    *   **Schema Type**: Select `OpenAPI / Swagger`.
    *   **Schema**: Paste the *entire content* of `external-codeinterpreter.json` into the text area.
    *   **Endpoint URL**:
        *   If you paste the JSON, Dify might auto-fill the server URL from the `servers` field.
        *   **Crucial**: Update the `url` to your actual server address (e.g., `http://<YOUR_PUBLIC_IP>:8000` or `https://api.yourdomain.com`).
4.  **Save**: Click **Save**.

## Agent Workflow in Dify

Once added, you can enable this tool in your Dify Agent/Workflow. A typical interaction flow for the LLM is:

1.  **Init**: Call `create_sandbox` to get a `sandbox_id`.
2.  **Work**:
    *   Call `run_code` with the `sandbox_id` and Python code to execute calculations or data processing.
    *   Call `upload_file` if the user provides a file (Dify passes a URL).
    *   Call `download_file` to retrieve result files.
3.  **Cleanup** (Optional but recommended): Call `stop_sandbox` with the `sandbox_id` when the task is done.

## API Reference

You can view the interactive API documentation locally at:
*   `http://localhost:8000/docs`
*   `http://localhost:8000/redoc`

## Development

*   **Mock Mode**: If `agentcube` is not installed, the service automatically falls back to a Mock implementation (prints to console, simulates execution), making it easy to test the Dify integration flow without a real sandbox backend.