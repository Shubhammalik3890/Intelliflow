import os
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .core import Base, engine, get_db, create_access_token, current_principal, require_role
from .models import (
    AgentExecution, ApprovalRecord, AuditLog, BusinessRequest, Department,
    KnowledgeDocument, ResponseDraft, User, WorkflowExecution,
)
from .schemas import ApprovalAction, RequestCreate, RequestPatch, SettingsPatch
from .agents import AIProviderError, process_request
from .passwords import hash_password, verify_password


Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="IntelliFlow AI",
    description="AI-powered business process automation platform",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


def audit(db: Session, principal: dict, action: str, resource_type: str, resource_id: str, metadata=None):
    db.add(AuditLog(
        organization_id=principal["organization_id"],
        actor=principal["sub"],
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=metadata or {},
    ))


def organization_filter(model, principal):
    return model.organization_id == principal["organization_id"]


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "IntelliFlow AI", "ai_mode": os.getenv("AI_PROVIDER", "mock")}


@app.post("/api/auth/register", status_code=201)
@limiter.limit("10/minute")
def register(payload: AuthPayload, request: Request, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user_count = db.scalar(select(func.count(User.id))) or 0
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role="Admin" if user_count == 0 else "Employee",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from exc
    db.refresh(user)
    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "role": user.role},
    }


@app.post("/api/auth/login")
@limiter.limit("20/minute")
def login(payload: AuthPayload, request: Request, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "role": user.role},
    }


@app.get("/api/auth/me")
def auth_me(principal=Depends(current_principal)):
    return principal


@app.get("/api/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db), principal=Depends(current_principal)):
    org = principal["organization_id"]
    def count_status(status=None, priority=None):
        query = select(func.count(BusinessRequest.id)).where(BusinessRequest.organization_id == org)
        if status:
            query = query.where(BusinessRequest.status == status)
        if priority:
            query = query.where(BusinessRequest.priority == priority)
        return db.scalar(query) or 0
    total = count_status()
    completed = count_status("Completed")
    pending = count_status("Pending") + count_status("Awaiting Approval")
    high = count_status(priority="High") + count_status(priority="Critical")
    completed_rows = db.scalars(select(BusinessRequest).where(
        BusinessRequest.organization_id == org,
        BusinessRequest.status == "Completed",
    )).all()
    resolution_hours = []
    for row in completed_rows:
        elapsed = (row.updated_at - row.created_at).total_seconds() / 3600
        resolution_hours.append(max(elapsed, 0))
    avg_resolution = round(sum(resolution_hours) / len(resolution_hours), 2) if resolution_hours else 0
    successful_workflows = db.scalar(select(func.count(WorkflowExecution.id)).where(
        WorkflowExecution.organization_id == org,
        WorkflowExecution.status == "Completed",
    )) or 0
    workflow_total = db.scalar(select(func.count(WorkflowExecution.id)).where(
        WorkflowExecution.organization_id == org,
    )) or 0
    return {
        "total_requests": total,
        "pending_requests": pending,
        "completed_requests": completed,
        "high_priority_requests": high,
        "average_resolution_hours": avg_resolution,
        "automation_success_rate": round(successful_workflows / workflow_total * 100, 2) if workflow_total else 0,
    }


@app.get("/api/dashboard/analytics")
def dashboard_analytics(db: Session = Depends(get_db), principal=Depends(current_principal)):
    org = principal["organization_id"]
    rows = db.scalars(select(BusinessRequest).where(BusinessRequest.organization_id == org)).all()
    def count_field(field):
        values = {}
        for row in rows:
            key = getattr(row, field)
            values[key] = values.get(key, 0) + 1
        return [{"name": key, "value": value} for key, value in sorted(values.items())]
    return {
        "requests_by_department": count_field("department"),
        "requests_by_priority": count_field("priority"),
        "requests_by_status": count_field("status"),
        "requests_over_time": [],
    }


@app.post("/api/requests", status_code=201)
@limiter.limit("30/minute")
def create_request(payload: RequestCreate, request: Request, db: Session = Depends(get_db), principal=Depends(current_principal)):
    row = BusinessRequest(
        organization_id=principal["organization_id"],
        sender=str(payload.sender),
        subject=payload.subject.strip(),
        message=payload.message.strip(),
        ai_metadata={"attachments": payload.attachments},
    )
    db.add(row)
    db.flush()
    audit(db, principal, "create", "business_request", row.id)
    db.commit()
    db.refresh(row)
    return serialize_request(row)


@app.get("/api/requests")
def list_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    department: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    principal=Depends(current_principal),
):
    query = select(BusinessRequest).where(BusinessRequest.organization_id == principal["organization_id"])
    for column, value in ((BusinessRequest.category, category), (BusinessRequest.department, department),
                          (BusinessRequest.priority, priority), (BusinessRequest.status, status)):
        if value:
            query = query.where(column == value)
    if search:
        pattern = f"%{search}%"
        query = query.where(BusinessRequest.subject.ilike(pattern) | BusinessRequest.sender.ilike(pattern))
    total = len(db.scalars(query).all())
    rows = db.scalars(query.order_by(BusinessRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [serialize_request(row) for row in rows], "total": total, "page": page, "page_size": page_size}


def serialize_request(row):
    return {
        "id": row.id, "sender": row.sender, "subject": row.subject, "message": row.message,
        "category": row.category, "department": row.department, "priority": row.priority,
        "status": row.status, "sentiment": row.sentiment, "ai_metadata": row.ai_metadata,
        "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat(),
    }


@app.get("/api/requests/{request_id}")
def get_request(request_id: str, db: Session = Depends(get_db), principal=Depends(current_principal)):
    row = db.get(BusinessRequest, request_id)
    if not row or not organization_filter(row, principal):
        raise HTTPException(404, "Request not found")
    return serialize_request(row)


@app.patch("/api/requests/{request_id}")
def patch_request(request_id: str, payload: RequestPatch, db: Session = Depends(get_db), principal=Depends(current_principal)):
    row = db.get(BusinessRequest, request_id)
    if not row or not organization_filter(row, principal):
        raise HTTPException(404, "Request not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    audit(db, principal, "update", "business_request", row.id, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(row)
    return serialize_request(row)


@app.delete("/api/requests/{request_id}", status_code=204)
def delete_request(request_id: str, db: Session = Depends(get_db), principal=Depends(require_role("Admin"))):
    row = db.get(BusinessRequest, request_id)
    if not row or not organization_filter(row, principal):
        raise HTTPException(404, "Request not found")
    db.delete(row)
    db.commit()
    return None


@app.post("/api/ai/analyze")
def analyze(payload: RequestCreate, principal=Depends(current_principal)):
    try:
        return process_request(str(payload.sender), payload.subject, payload.message)
    except AIProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/api/ai/process/{request_id}")
def process(request_id: str, db: Session = Depends(get_db), principal=Depends(current_principal)):
    row = db.get(BusinessRequest, request_id)
    if not row or not organization_filter(row, principal):
        raise HTTPException(404, "Request not found")
    workflow = WorkflowExecution(
        organization_id=principal["organization_id"], request_id=request_id, status="Processing", state={}
    )
    db.add(workflow)
    db.flush()
    try:
        result = process_request(row.sender, row.subject, row.message)
        row.category = result["classification"]["intent"]
        row.department = result["routing"]["department"]
        row.priority = result["priority"]["priority"]
        row.sentiment = result["sentiment"]["sentiment"]
        row.status = "Awaiting Approval" if result["supervisor"]["approval_required"] else "Processing"
        row.ai_metadata = result
        workflow.state = result
        workflow.status = "Awaiting Approval" if row.status == "Awaiting Approval" else "Completed"
        db.add(ResponseDraft(
            organization_id=principal["organization_id"], request_id=request_id,
            content=result["response"]["draft"],
        ))
        audit(db, principal, "process_ai", "business_request", request_id, {"workflow_id": workflow.id})
        db.commit()
        db.refresh(workflow)
        return {"workflow_id": workflow.id, "status": workflow.status, "result": result}
    except AIProviderError as exc:
        workflow.status = "Failed"
        workflow.error = str(exc)
        row.status = "Failed"
        db.commit()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        workflow.status = "Failed"
        workflow.error = str(exc)
        row.status = "Failed"
        db.commit()
        raise HTTPException(500, "Workflow execution failed")


@app.get("/api/ai/agents")
def ai_agents(db: Session = Depends(get_db), principal=Depends(current_principal)):
    names = ["Email Intake", "Classification", "Sentiment Analysis", "Priority Assessment",
             "Department Routing", "Response Generation", "Supervisor", "Workflow Orchestrator"]
    return [{"name": name, "status": "Available", "mode": os.getenv("AI_PROVIDER", "mock")}
            for name in names]


@app.get("/api/ai/executions/{request_id}")
def ai_executions(request_id: str, db: Session = Depends(get_db), principal=Depends(current_principal)):
    rows = db.scalars(select(AgentExecution).where(
        AgentExecution.organization_id == principal["organization_id"],
        AgentExecution.request_id == request_id,
    ).order_by(AgentExecution.created_at.desc())).all()
    return [{
        "id": row.id, "agent_name": row.agent_name, "status": row.status,
        "output": row.output_data, "error": row.error, "created_at": row.created_at.isoformat(),
    } for row in rows]


@app.get("/api/approvals")
def approvals(db: Session = Depends(get_db), principal=Depends(current_principal)):
    rows = db.scalars(select(BusinessRequest).where(
        BusinessRequest.organization_id == principal["organization_id"],
        BusinessRequest.status == "Awaiting Approval",
    ).order_by(BusinessRequest.created_at.desc())).all()
    items = []
    for row in rows:
        draft = db.scalar(select(ResponseDraft).where(ResponseDraft.request_id == row.id).order_by(ResponseDraft.created_at.desc()))
        items.append({"request": serialize_request(row), "draft": draft.content if draft else "", "draft_id": draft.id if draft else None})
    return items


@app.post("/api/approvals/{request_id}/approve")
def approve(request_id: str, payload: ApprovalAction, db: Session = Depends(get_db), principal=Depends(current_principal)):
    row = db.get(BusinessRequest, request_id)
    if not row or not organization_filter(row, principal):
        raise HTTPException(404, "Request not found")
    draft = db.scalar(select(ResponseDraft).where(ResponseDraft.request_id == request_id).order_by(ResponseDraft.created_at.desc()))
    if draft:
        draft.content = payload.draft or draft.content
        draft.approved = True
    db.add(ApprovalRecord(
        organization_id=principal["organization_id"], request_id=request_id,
        reviewer=principal["sub"], action="Approved", comments=payload.comments,
        draft_snapshot={"content": draft.content if draft else payload.draft},
    ))
    row.status = "Approved"
    audit(db, principal, "approve", "business_request", request_id, {"comments": payload.comments})
    db.commit()
    return {"status": "Approved"}


@app.post("/api/approvals/{request_id}/reject")
def reject(request_id: str, payload: ApprovalAction, db: Session = Depends(get_db), principal=Depends(current_principal)):
    row = db.get(BusinessRequest, request_id)
    if not row or not organization_filter(row, principal):
        raise HTTPException(404, "Request not found")
    db.add(ApprovalRecord(
        organization_id=principal["organization_id"], request_id=request_id,
        reviewer=principal["sub"], action="Rejected", comments=payload.comments,
        draft_snapshot={"content": payload.draft or ""},
    ))
    row.status = "Rejected"
    audit(db, principal, "reject", "business_request", request_id)
    db.commit()
    return {"status": "Rejected"}


@app.post("/api/knowledge/upload")
def knowledge_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    principal=Depends(current_principal),
):
    allowed = {"application/pdf", "text/plain"}
    if file.content_type not in allowed:
        raise HTTPException(400, "Only PDF and TXT files are supported")
    content = file.file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File exceeds 10 MB limit")
    text = ""
    if file.content_type == "text/plain":
        text = content.decode("utf-8", errors="replace")
    else:
        try:
            from pypdf import PdfReader
            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        except Exception as exc:
            raise HTTPException(400, "Unable to read PDF") from exc
    row = KnowledgeDocument(
        organization_id=principal["organization_id"], filename=file.filename,
        content_type=file.content_type, text_content=text,
    )
    db.add(row)
    audit(db, principal, "upload", "knowledge_document", "", {"filename": file.filename})
    db.commit()
    db.refresh(row)
    return {"id": row.id, "filename": row.filename, "created_at": row.created_at.isoformat()}


@app.get("/api/knowledge/documents")
def knowledge_documents(db: Session = Depends(get_db), principal=Depends(current_principal)):
    rows = db.scalars(select(KnowledgeDocument).where(
        KnowledgeDocument.organization_id == principal["organization_id"],
    ).order_by(KnowledgeDocument.created_at.desc())).all()
    return [{"id": row.id, "filename": row.filename, "content_type": row.content_type,
             "created_at": row.created_at.isoformat()} for row in rows]


@app.delete("/api/knowledge/documents/{document_id}", status_code=204)
def delete_document(document_id: str, db: Session = Depends(get_db), principal=Depends(require_role("Admin", "Manager"))):
    row = db.get(KnowledgeDocument, document_id)
    if not row or not organization_filter(row, principal):
        raise HTTPException(404, "Document not found")
    db.delete(row)
    db.commit()


@app.get("/api/workflows")
def workflows(db: Session = Depends(get_db), principal=Depends(current_principal)):
    rows = db.scalars(select(WorkflowExecution).where(
        WorkflowExecution.organization_id == principal["organization_id"],
    ).order_by(WorkflowExecution.created_at.desc())).all()
    return [{"id": row.id, "request_id": row.request_id, "status": row.status,
             "state": row.state, "error": row.error, "created_at": row.created_at.isoformat()} for row in rows]


@app.get("/api/workflows/{workflow_id}")
def workflow_detail(workflow_id: str, db: Session = Depends(get_db), principal=Depends(current_principal)):
    row = db.get(WorkflowExecution, workflow_id)
    if not row or not organization_filter(row, principal):
        raise HTTPException(404, "Workflow not found")
    return {"id": row.id, "request_id": row.request_id, "status": row.status,
            "state": row.state, "error": row.error, "created_at": row.created_at.isoformat()}


@app.post("/api/workflows/{workflow_id}/retry")
def retry_workflow(workflow_id: str, db: Session = Depends(get_db), principal=Depends(current_principal)):
    workflow = db.get(WorkflowExecution, workflow_id)
    if not workflow or not organization_filter(workflow, principal):
        raise HTTPException(404, "Workflow not found")
    return process_workflow_for_request(workflow.request_id, db, principal)


def process_workflow_for_request(request_id: str, db: Session, principal: dict):
    row = db.get(BusinessRequest, request_id)
    if not row:
        raise HTTPException(404, "Request not found")
    workflow = WorkflowExecution(
        organization_id=principal["organization_id"], request_id=request_id,
        status="Processing", state={},
    )
    db.add(workflow)
    db.flush()
    result = process_request(row.sender, row.subject, row.message)
    row.category = result["classification"]["intent"]
    row.department = result["routing"]["department"]
    row.priority = result["priority"]["priority"]
    row.sentiment = result["sentiment"]["sentiment"]
    row.status = "Awaiting Approval" if result["supervisor"]["approval_required"] else "Processing"
    row.ai_metadata = result
    workflow.status = row.status
    workflow.state = result
    db.commit()
    return {"workflow_id": workflow.id, "status": workflow.status, "result": result}


@app.get("/api/settings")
def get_settings(principal=Depends(current_principal)):
    provider = os.getenv("AI_PROVIDER", "mock").strip().lower()
    return {
        "ai_provider": provider,
        "ai_model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite") if provider == "gemini" else None,
        "gemini_api_key_configured": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "routing_rules": {},
    }


@app.patch("/api/settings")
def patch_settings(payload: SettingsPatch, principal=Depends(require_role("Admin", "Manager"))):
    return payload.model_dump(exclude_unset=True)
