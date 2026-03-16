"""
models/schemas.py – Pydantic request/response models shared across the API.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════
#  Chat / AI
# ══════════════════════════════════════════════════════════════════

class ChatMessage(BaseModel):
    role: str = Field(..., examples=["user", "assistant", "system"])
    content: str


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None           # override the default model
    history: List[ChatMessage] = []        # conversation history
    stream: bool = True


class ChatResponse(BaseModel):
    response: str
    model: str
    done: bool = True


class CodeGenerationRequest(BaseModel):
    prompt: str
    language: Optional[str] = "python"
    context: Optional[str] = None          # surrounding code for context
    model: Optional[str] = None
    stream: bool = True


class CodeGenerationResponse(BaseModel):
    code: str
    language: str
    explanation: Optional[str] = None


# ══════════════════════════════════════════════════════════════════
#  File System
# ══════════════════════════════════════════════════════════════════

class FileReadRequest(BaseModel):
    path: str


class FileWriteRequest(BaseModel):
    path: str
    content: str


class FileCreateRequest(BaseModel):
    path: str
    content: str = ""


class FileDeleteRequest(BaseModel):
    path: str


class FileRenameRequest(BaseModel):
    old_path: str
    new_path: str


class DirectoryListRequest(BaseModel):
    path: str
    recursive: bool = False


class FileInfo(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: Optional[int] = None
    extension: Optional[str] = None


class DirectoryListResponse(BaseModel):
    path: str
    items: List[FileInfo]


# ══════════════════════════════════════════════════════════════════
#  Terminal
# ══════════════════════════════════════════════════════════════════

class TerminalRequest(BaseModel):
    command: str
    cwd: Optional[str] = None             # working directory
    timeout: int = 30                     # seconds


class TerminalResponse(BaseModel):
    stdout: str
    stderr: str
    return_code: int
    command: str


# ══════════════════════════════════════════════════════════════════
#  AI Agent
# ══════════════════════════════════════════════════════════════════

class AgentTask(BaseModel):
    task: str
    context: Optional[str] = None
    workspace_path: Optional[str] = None
    model: Optional[str] = None


class AgentStep(BaseModel):
    step: int
    action: str
    result: str
    success: bool


class AgentResponse(BaseModel):
    task: str
    steps: List[AgentStep]
    final_result: str
    success: bool


# ══════════════════════════════════════════════════════════════════
#  Workspace
# ══════════════════════════════════════════════════════════════════

class WorkspaceOpenRequest(BaseModel):
    path: str


class WorkspaceInfo(BaseModel):
    path: str
    name: str
    file_count: int
    languages: List[str]


# ══════════════════════════════════════════════════════════════════
#  Generic responses
# ══════════════════════════════════════════════════════════════════

class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
