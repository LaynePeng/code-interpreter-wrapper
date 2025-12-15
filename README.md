# Code Interpreter Wrapper for Dify

This project provides a standard HTTP API wrapper for `agentcube` (or a mock sandbox environment) designed to be integrated into **Dify** workflows using the **HTTP Request** node.

## Features

*   **HTTP API**: Simple REST endpoints for sandbox management.
*   **Sandbox Management**: Create (`/create_sandbox`) and destroy (`/stop_sandbox`) isolated environments.
*   **Execution**: Run Python code (`/run_code`) and Shell commands (`/execute_command`).
*   **File Management**: Upload files (`/upload_file`), write content (`/write_file`), and download files (`/download_file`).

## Prerequisites

*   Python 3.8+
*   `pip`
*   A running [Dify](https://dify.ai/) instance.

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

Instead of importing an OpenAPI schema, you can now use the **HTTP Request** node in your Dify workflows to interact directly with this service.

### Common Endpoints

Base URL: `http://<YOUR_SERVER_IP>:8000`

#### 1. Create Sandbox
**POST** `/create_sandbox`

Creates a new session and returns a `sandbox_id`.

*   **Body (JSON)**:
    ```json
    {
      "conversation_id": "optional-id"
    }
    ```
*   **Response**:
    ```json
    {
      "sandbox_id": "uuid-string",
      "info": { ... }
    }
    ```

#### 2. Run Code
**POST** `/run_code`

Executes Python code in the sandbox.

*   **Body (JSON)**:
    ```json
    {
      "sandbox_id": "<sandbox_id_from_step_1>",
      "code": "print('Hello World')",
      "language": "py"
    }
    ```

#### 3. Execute Command
**POST** `/execute_command`

Executes a shell command.

*   **Body (JSON)**:
    ```json
    {
      "sandbox_id": "<sandbox_id>",
      "command": "ls -la"
    }
    ```

#### 4. Upload File
**POST** `/upload_file`

Uploads a file from a URL (e.g., a file uploaded by the user in Dify) to the sandbox.

*   **Body (JSON)**:
    ```json
    {
      "sandbox_id": "<sandbox_id>",
      "file_url": "http://example.com/file.csv",
      "remote_filename": "data.csv"
    }
    ```

#### 5. Stop Sandbox
**POST** `/stop_sandbox`

Cleans up the environment.

*   **Body (JSON)**:
    ```json
    {
      "sandbox_id": "<sandbox_id>"
    }
    ```

## Development

*   **Mock Mode**: If `agentcube` is not installed, the service automatically falls back to a Mock implementation (prints to console, simulates execution).
*   **Docs**: Interactive API documentation is available at `http://localhost:8000/docs` to help you test payloads.
