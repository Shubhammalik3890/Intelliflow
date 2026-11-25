import uuid
from datetime import datetime, timezone
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .core import Base


def utcnow():
    return datetime.now(timezone.utc)


def uuid_text():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "app_users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_text)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="Employee")
    organization_id: Mapped[str] = mapped_column(String, index=True, default="default")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(String, index=True, default="default")
    name: Mapped[str] = mapped_column(String, unique=True)
    routing_keywords: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class BusinessRequest(Base):
    __tablename__ = "business_requests"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(String, index=True, default="default")
    sender: Mapped[str] = mapped_column(String)
    subject: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String, default="General Inquiry")
    department: Mapped[str] = mapped_column(String, default="General")
    priority: Mapped[str] = mapped_column(String, default="Medium")
    status: Mapped[str] = mapped_column(String, default="Pending", index=True)
    sentiment: Mapped[str] = mapped_column(String, default="Neutral")
    ai_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AgentExecution(Base):
    __tablename__ = "agent_executions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(String, index=True)
    request_id: Mapped[str] = mapped_column(String, ForeignKey("business_requests.id"), index=True)
    agent_name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    output_data: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(String, index=True)
    request_id: Mapped[str] = mapped_column(String, ForeignKey("business_requests.id"), index=True)
    status: Mapped[str] = mapped_column(String, default="Processing")
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ApprovalRecord(Base):
    __tablename__ = "approval_records"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(String, index=True)
    request_id: Mapped[str] = mapped_column(String, ForeignKey("business_requests.id"), index=True)
    reviewer: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String)
    comments: Mapped[str] = mapped_column(Text, default="")
    draft_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ResponseDraft(Base):
    __tablename__ = "response_drafts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(String, index=True)
    request_id: Mapped[str] = mapped_column(String, ForeignKey("business_requests.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(String, index=True)
    filename: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)
    text_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(String, index=True)
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    resource_type: Mapped[str] = mapped_column(String)
    resource_id: Mapped[str] = mapped_column(String)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
