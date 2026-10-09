from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ==========================================
# AUTH & USER SCHEMAS
# ==========================================
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    role: str = "student"  # student, instructor, org_admin


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    role: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    organization_id: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# NOTEBOOK & PROJECT SCHEMAS
# ==========================================
class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class NotebookCreate(BaseModel):
    title: str
    project_id: Optional[str] = None
    kernel_name: str = "python3"
    initial_content: Optional[Dict[str, Any]] = None


class NotebookUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[Dict[str, Any]] = None  # Notebook JSON (v4)


class NotebookResponse(BaseModel):
    id: str
    user_id: str
    project_id: Optional[str]
    title: str
    kernel_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotebookDetailResponse(NotebookResponse):
    content: Dict[str, Any]


# ==========================================
# EXECUTION SCHEMAS
# ==========================================
class CodeExecutionRequest(BaseModel):
    session_id: str
    code: str
    timeout: Optional[float] = 60.0


class CodeExecutionResponse(BaseModel):
    session_id: str
    msg_id: str
    status: str
    execution_count: Optional[int] = None
    outputs: List[Dict[str, Any]] = []
    error: Optional[Dict[str, Any]] = None
    execution_time: float


class KernelControlRequest(BaseModel):
    session_id: str
    action: str  # "restart", "interrupt", "shutdown"


# ==========================================
# FILE SCHEMAS
# ==========================================
class FileItemResponse(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int
    modified_at: float


class FileWriteRequest(BaseModel):
    path: str
    content: str


class FileRenameRequest(BaseModel):
    old_path: str
    new_path: str


class FolderCreateRequest(BaseModel):
    path: str



# ==========================================
# CLASSROOM SCHEMAS
# ==========================================
class ClassroomCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ClassroomResponse(BaseModel):
    id: str
    instructor_id: str
    name: str
    description: Optional[str]
    join_code: str
    created_at: datetime

    class Config:
        from_attributes = True


class AssignmentCreate(BaseModel):
    classroom_id: str
    title: str
    description: Optional[str] = None
    template_notebook: Dict[str, Any]
    due_date: Optional[datetime] = None


class AssignmentResponse(BaseModel):
    id: str
    classroom_id: str
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class SubmissionCreate(BaseModel):
    assignment_id: str
    notebook_content: Dict[str, Any]


class SubmissionResponse(BaseModel):
    id: str
    assignment_id: str
    student_id: str
    status: str
    grade: Optional[float]
    feedback: Optional[str]
    submitted_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# SYSTEM & HEALTH SCHEMAS
# ==========================================
class SystemHealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    active_kernels: int
    python_version: str
    timestamp: datetime

