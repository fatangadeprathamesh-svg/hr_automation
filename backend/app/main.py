from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.seed import init_db_and_seed
from app.auth.security import get_current_actor, ActorIdentity, create_access_token
from app.models.hr import Employee
from app.api.imports import router as imports_router
from app.api.audit import router as audit_router
from app.api.corrections import router as corrections_router
from app.api.notifications import router as notifications_router
from app.api.enrichments import router as enrichments_router
from app.api.submissions import router as submissions_router
from app.api.exports import router as exports_router
from app.api.auth import router as auth_router
from app.api.explainers import router as explainers_router
from app.api.master_uploads import router as master_uploads_router
from app.api.duties import router as duties_router
from app.api.consent import router as consent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize and seed database if necessary
    init_db_and_seed()
    yield


app = FastAPI(
    title="Month-End HR Self-Audit Assistant API",
    version="1.0.0",
    description="Automated deterministic HR self-audit assistant and compliance ledger.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(imports_router)
app.include_router(audit_router)
app.include_router(corrections_router)
app.include_router(notifications_router)
app.include_router(enrichments_router)
app.include_router(submissions_router)
app.include_router(exports_router)
app.include_router(auth_router)
app.include_router(explainers_router, prefix="/api")
app.include_router(explainers_router)
app.include_router(master_uploads_router)
app.include_router(duties_router)
app.include_router(consent_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "hr-self-audit-backend",
        "environment": settings.ENVIRONMENT,
        "organization_id": settings.ORGANIZATION_ID,
    }


@app.get("/auth/me")
def get_current_user_profile(actor: ActorIdentity = Depends(get_current_actor)):
    return {
        "actor_id": actor.actor_id,
        "role": actor.role,
        "organization_id": actor.organization_id,
        "email": actor.email,
        "is_service": actor.is_service,
    }


@app.get("/auth/token/{persona_id}")
def get_persona_jwt_token(persona_id: str, db: Session = Depends(get_db)):
    """Provides a valid signed JWT for test personas."""
    pid = persona_id.upper()
    role_map = {
        "EMP001": "employee",
        "MGR001": "manager",
        "HR001": "hr_admin",
    }
    role = role_map.get(pid, "employee")
    emp = db.query(Employee).filter(Employee.employee_id == pid).first()
    token = create_access_token({
        "sub": pid,
        "role": role,
        "org_id": settings.ORGANIZATION_ID,
        "email": emp.email if emp else f"{pid.lower()}@example.com",
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "persona_id": pid,
        "role": role,
    }
