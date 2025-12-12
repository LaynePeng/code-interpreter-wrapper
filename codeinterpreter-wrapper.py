import os
import shutil
import tempfile
import httpx
import uvicorn
import time
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# ================= SDK Simulation/Import =================
try:
    from agentcube import CodeInterpreterClient
except ImportError:
    print("Warning: agentcube not found. Using Mock for testing.")
    class CodeInterpreterClient:
        def __init__(self):
            import uuid
            self.id = str(uuid.uuid4())[:8]
        def get_info(self):
            return {"id": self.id, "status": "running", "host": "127.0.0.1"}
        def execute_command(self, cmd): return f"Mock Exec: {cmd}"
        def run_code(self, language, code): return f"Mock Run {language}: {code}"
        def upload_file(self, local, remote): pass
        def write_file(self, content, remote): pass
        def download_file(self, remote, local): 
            with open(local, 'w') as f: f.write("mock data")
        def stop(self): return True

# ================= Configuration =================
PORT = int(os.getenv("PORT", 8000))
HOST_URL = os.getenv("HOST_URL", f"http://localhost:{PORT}")

# Core Storage: sandbox_id -> client_instance
SANDBOX_STORE: Dict[str, CodeInterpreterClient] = {}
# Auxiliary Storage: sandbox_id -> temporary_directory (for file transfer transit)
TEMP_DIRS: Dict[str, str] = {}

app = FastAPI(title="AgentCube Wrapper")

# ================= Request Models =================
class CreateRequest(BaseModel):
    # Dify might send conversation_id for tagging, although the SDK might not strictly use it
    conversation_id: str = Field(default="", description="Optional Dify conversation ID")

class SandboxIdRequest(BaseModel):
    sandbox_id: str = Field(..., description="The ID returned by create_sandbox")

class CommandRequest(BaseModel):
    sandbox_id: str
    command: str

class RunCodeRequest(BaseModel):
    sandbox_id: str
    code: str
    language: str = "py"

class WriteFileRequest(BaseModel):
    sandbox_id: str
    content: str
    remote_path: str

class UploadRequest(BaseModel):
    sandbox_id: str
    file_url: str
    remote_filename: str

class DownloadRequest(BaseModel):
    sandbox_id: str
    remote_path: str

# ================= Helper Functions =================
def get_client_or_404(sandbox_id: str) -> CodeInterpreterClient:
    if sandbox_id not in SANDBOX_STORE:
        raise HTTPException(status_code=404, detail=f"Sandbox {sandbox_id} not found or expired")
    return SANDBOX_STORE[sandbox_id]

# ================= API Routes =================

@app.get("/", summary="Health Check")
async def health_check():
    return {"status": "ok", "message": "AgentCube Wrapper is running"}

@app.post("/create_sandbox", summary="Initialize Sandbox", operation_id="create_sandbox")
async def create_sandbox(req: CreateRequest):
    """
    Corresponds to: code_interpreter = CodeInterpreterClient()
    Returns: sandbox_id and sandbox_info
    """
    try:
        # 1. Initialize SDK
        client = CodeInterpreterClient()
        
        # 2. Store in memory
        SANDBOX_STORE[client.id] = client
        # Create a local temporary directory for this sandbox for file transfer
        TEMP_DIRS[client.id] = tempfile.mkdtemp(prefix=f"sbx_{client.id}_")
        
        # 3. Get info
        info = client.get_info()
        
        print(f"Created sandbox: {client.id}")
        return {
            "sandbox_id": client.id, 
            "info": info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_sandbox_info", summary="Get Sandbox Info", operation_id="get_sandbox_info")
async def get_sandbox_info(req: SandboxIdRequest):
    """
    Corresponds to: sandbox_info = code_interpreter.get_info()
    """
    client = get_client_or_404(req.sandbox_id)
    return client.get_info()

@app.post("/execute_command", summary="Execute Shell Command", operation_id="execute_command")
async def execute_command(req: CommandRequest):
    """
    Corresponds to: code_interpreter.execute_command(cmd)
    """
    client = get_client_or_404(req.sandbox_id)
    try:
        output = client.execute_command(req.command)
        # Some SDKs return objects, others strings; convert to string for API stability
        return {"output": str(output)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run_code", summary="Run Code", operation_id="run_code")
async def run_code(req: RunCodeRequest):
    """
    Corresponds to: code_interpreter.run_code(language="py", code=...)
    """
    client = get_client_or_404(req.sandbox_id)
    try:
        output = client.run_code(language=req.language, code=req.code)
        return {"output": str(output)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/write_file", summary="Write File to Sandbox", operation_id="write_file")
async def write_file(req: WriteFileRequest):
    """
    Corresponds to: code_interpreter.write_file(content, remote_path)
    """
    client = get_client_or_404(req.sandbox_id)
    try:
        client.write_file(req.content, req.remote_path)
        return {"status": "success", "remote_path": req.remote_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload_file", summary="Upload File", operation_id="upload_file")
async def upload_file(req: UploadRequest):
    """
    Corresponds to: code_interpreter.upload_file(local, remote)
    """
    client = get_client_or_404(req.sandbox_id)
    tmp_dir = TEMP_DIRS[req.sandbox_id]
    
    local_path = os.path.join(tmp_dir, req.remote_filename)
    
    try:
        # Download file from Dify (or other source) to local
        async with httpx.AsyncClient() as ac:
            resp = await ac.get(req.file_url)
            with open(local_path, 'wb') as f:
                f.write(resp.content)
        
        # Upload to sandbox
        remote_path = f"/workspace/{req.remote_filename}"
        client.upload_file(local_path, remote_path)
        
        # Cleanup local (optional)
        if os.path.exists(local_path):
            os.remove(local_path)

        return {"status": "success", "remote_path": remote_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/download_file", summary="Download File", operation_id="download_file")
async def download_file(req: DownloadRequest):
    """
    Corresponds to: code_interpreter.download_file(remote, local)
    """
    client = get_client_or_404(req.sandbox_id)
    tmp_dir = TEMP_DIRS[req.sandbox_id]
    
    filename = os.path.basename(req.remote_path)
    local_path = os.path.join(tmp_dir, filename)
    
    try:
        # Download from sandbox to local
        client.download_file(req.remote_path, local_path)
        
        if not os.path.exists(local_path):
            raise HTTPException(status_code=404, detail="File failed to download from sandbox")
            
        # Generate download link
        dl_url = f"{HOST_URL}/files/{req.sandbox_id}/{filename}"
        return {"filename": filename, "download_url": dl_url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop_sandbox", summary="Stop Sandbox", operation_id="stop_sandbox")
async def stop_sandbox(req: SandboxIdRequest):
    """
    Corresponds to: code_interpreter.stop()
    """
    if req.sandbox_id in SANDBOX_STORE:
        client = SANDBOX_STORE.pop(req.sandbox_id)
        # Cleanup temporary directory
        if req.sandbox_id in TEMP_DIRS:
            shutil.rmtree(TEMP_DIRS.pop(req.sandbox_id), ignore_errors=True)
            
        try:
            client.stop()
            return {"status": "stopped"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    return {"status": "not_found"}

# ================= Static File Service =================
@app.get("/files/{sandbox_id}/{filename}")
async def get_file_content(sandbox_id: str, filename: str):
    if sandbox_id not in TEMP_DIRS:
        raise HTTPException(status_code=404, detail="Sandbox not found")
        
    file_path = os.path.join(TEMP_DIRS[sandbox_id], filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)