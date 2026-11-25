from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any


class RequestCreate(BaseModel):
    sender: EmailStr
    subject: str = Field(min_length=1, max_length=300)
    message: str = Field(min_length=1, max_length=50000)
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class RequestPatch(BaseModel):
    subject: Optional[str] = None
    message: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class ApprovalAction(BaseModel):
    comments: str = Field(default="", max_length=5000)
    draft: Optional[str] = None


class SettingsPatch(BaseModel):
    ai_provider: Optional[str] = None
    routing_rules: Optional[dict[str, list[str]]] = None

