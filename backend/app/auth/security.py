from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Request, Response, Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app.config import settings
from app.database import get_db
from app.models.hr import Employee


class ActorIdentity:
    """Verified identity derived strictly on the server-side."""
    def __init__(
        self,
        actor_id: str,
        organization_id: str,
        role: str,
        email: Optional[str] = None,
        is_service: bool = False,
    ):
        self.actor_id = actor_id
        self.organization_id = organization_id
        self.role = role  # employee, manager, hr_admin, service
        self.email = email
        self.is_service = is_service

    def __repr__(self) -> str:
        return f"<ActorIdentity {self.actor_id} ({self.role}) org={self.organization_id}>"


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Creates a signed JWT access token containing identity claims."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def set_auth_cookie(response: Response, token: str) -> None:
    """
    Sets a secure httpOnly cookie session.
    Protects against XSS token exfiltration.
    """
    max_age_seconds = settings.JWT_EXPIRATION_MINUTES * 60
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=max_age_seconds,
        expires=max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=False if settings.ENVIRONMENT == "development" else True,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """Clears the httpOnly session cookie on logout."""
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite="lax",
    )


def get_current_actor(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_service_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> ActorIdentity:
    """
    Non-negotiable Design Rule 4:
    Authorization is enforced server-side on every request.
    Derives actor and organization from verified identity, NEVER from request bodies.
    Supports Authorization Bearer header AND httpOnly cookie sessions.
    """
    # 1. Check Service Authentication (e.g. n8n Orchestrator service key)
    if x_service_key:
        if x_service_key == settings.N8N_SERVICE_API_KEY:
            return ActorIdentity(
                actor_id="service:n8n",
                organization_id=settings.ORGANIZATION_ID,
                role="service",
                is_service=True,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service API key.",
        )

    # 2. Extract Token from Authorization Header OR httpOnly Cookie
    token: Optional[str] = None
    auth_header = authorization or request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing Authorization header or session cookie.",
        )

    # Quick check for service bearer token
    if token == settings.N8N_SERVICE_API_KEY:
        return ActorIdentity(
            actor_id="service:n8n",
            organization_id=settings.ORGANIZATION_ID,
            role="service",
            is_service=True,
        )

    # Support development persona tokens (used by frontend in dev mode)
    if settings.ENVIRONMENT == "development" and token.startswith("DEV_TOKEN_"):
        parts = token.split("_")
        if len(parts) >= 4:
            actor_id = parts[2]
            role = "_".join(parts[3:])

            # Prefer canonical 4-digit dataset IDs (EMP0001 > EMP001, EMP0002 > MGR001, etc.)
            target_ids = [actor_id]
            if actor_id in ("EMP001", "EMP1", "EMP0001"):
                target_ids = ["EMP0001", "EMP001"]
            elif actor_id in ("MGR001", "MGR1", "EMP0002"):
                target_ids = ["EMP0002", "MGR001"]
            elif actor_id in ("HR001", "HR1", "EMP0003"):
                target_ids = ["EMP0003", "HR001"]
            elif actor_id in ("IC001", "IC1", "EMP0004"):
                target_ids = ["EMP0004", "IC001"]

            emp = None
            for tid in target_ids:
                emp = db.query(Employee).filter(Employee.employee_id == tid).first()
                if emp:
                    break

            if not emp:
                # Also try matching by persona email
                persona_email = f"{actor_id.lower()}@company.com"
                emp = db.query(Employee).filter(func.lower(Employee.email) == persona_email.lower()).first()

            resolved_id = emp.employee_id if emp else actor_id
            return ActorIdentity(
                actor_id=resolved_id,
                organization_id=settings.ORGANIZATION_ID,
                role=role,
                email=emp.email if emp else f"{actor_id.lower()}@example.com",
                is_service=(role == "service"),
            )

    try:
        payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        actor_id: str = payload.get("sub")
        org_id: str = payload.get("org_id", settings.ORGANIZATION_ID)
        role: str = payload.get("role", "employee")
        email: Optional[str] = payload.get("email")

        if actor_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject identifier.",
            )

        return ActorIdentity(
            actor_id=actor_id,
            organization_id=org_id,
            role=role,
            email=email,
            is_service=False,
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: Token is invalid or expired.",
        )


def require_role(*allowed_roles: str):
    """RBAC dependency ensuring actor has one of the required roles."""
    def role_checker(actor: ActorIdentity = Depends(get_current_actor)) -> ActorIdentity:
        if actor.role not in allowed_roles and actor.role != "service":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role '{actor.role}'. Allowed: {list(allowed_roles)}",
            )
        return actor
    return role_checker
