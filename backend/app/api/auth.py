from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.auth import UserAuth, OTPVerification
from app.models.hr import Employee
from app.auth.security import (
    create_access_token,
    set_auth_cookie,
    clear_auth_cookie,
    get_current_actor,
    ActorIdentity,
)
from app.auth.service import (
    hash_password,
    verify_password,
    auth_rate_limiter,
    AuthService,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication & Identity"])

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    role: Optional[str] = "employee"


class LoginRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN)
    password: str


class VerifyOtpRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN)
    code: str = Field(..., min_length=6, max_length=6)


class ResendOtpRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN)


class GoogleAuthRequest(BaseModel):
    credential: str = Field(..., description="Google ID Token from Google Identity Services")


def check_rate_limit(request: Request, key: str):
    """Enforces per-client rate limit on authentication endpoints."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_key = f"{client_ip}:{key.lower()}"
    allowed, retry_after = auth_rate_limiter.is_allowed(rate_key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please wait {retry_after} second(s) before trying again.",
            headers={"Retry-After": str(retry_after)},
        )


def resolve_auth_email(db: Session, email: str) -> str:
    """Resolves demo email variations between @company.com and @example.com cleanly."""
    clean = email.strip().lower()
    # If there is already an OTP or UserAuth or Employee for this exact email, use it directly
    if db.query(OTPVerification).filter(OTPVerification.email == clean).first():
        return clean
    if db.query(UserAuth).filter(UserAuth.email == clean).first():
        return clean
    if db.query(Employee).filter(Employee.email == clean).first():
        return clean

    # Otherwise check known alias
    alias = None
    if "@company.com" in clean:
        prefix = clean.split("@")[0]
        if prefix in ("bob", "bob.manager"):
            alias = "bob.manager@example.com"
        elif prefix in ("carol", "carol.hr"):
            alias = "carol.hr@example.com"
        else:
            alias = f"{prefix}@example.com"
    elif "@example.com" in clean:
        prefix = clean.split("@")[0].replace(".manager", "").replace(".hr", "")
        alias = f"{prefix}@company.com"

    if alias and (
        db.query(OTPVerification).filter(OTPVerification.email == alias).first()
        or db.query(UserAuth).filter(UserAuth.email == alias).first()
        or db.query(Employee).filter(Employee.email == alias).first()
    ):
        return alias

    return clean


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """
    Registers a new employee account with hashed password and triggers email OTP verification.
    """
    check_rate_limit(request, req.email)
    clean_email = req.email.strip().lower()

    # Check existing user
    existing = db.query(UserAuth).filter(UserAuth.email == clean_email).first()
    if existing and existing.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{clean_email}' already exists. Please sign in.",
        )

    # Link to existing employee record or create provisional employee
    emp = db.query(Employee).filter(Employee.email == clean_email).first()
    if not emp:
        import uuid
        emp_id = f"EMP-{uuid.uuid4().hex[:6].upper()}"
        emp = Employee(
            employee_id=emp_id,
            organization_id=settings.ORGANIZATION_ID,
            email=clean_email,
            full_name=req.full_name.strip(),
            is_active=True,
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)

    # Hash password with bcrypt
    hashed = hash_password(req.password)
    if existing:
        existing.password_hash = hashed
        existing.role = req.role or existing.role
        user = existing
    else:
        user = UserAuth(
            employee_id=emp.employee_id,
            organization_id=settings.ORGANIZATION_ID,
            email=clean_email,
            password_hash=hashed,
            role=req.role or "employee",
            is_verified=False,
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    # Send 10-minute OTP
    otp, code = AuthService.create_or_refresh_otp(db, clean_email)

    resp_data = {
        "success": True,
        "message": "Account created. A 6-digit verification code has been sent to your email.",
        "email": clean_email,
    }
    if settings.ENVIRONMENT == "development":
        resp_data["dev_code"] = code

    return resp_data


@router.post("/login", status_code=status.HTTP_200_OK)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Validates email/password credentials and issues a 10-minute 6-digit verification OTP.
    """
    check_rate_limit(request, req.email)
    auth_email = resolve_auth_email(db, req.email)

    # Look up user or linked employee
    user = db.query(UserAuth).filter(UserAuth.email == auth_email).first()
    emp = db.query(Employee).filter(Employee.email == auth_email).first()

    if not user and not emp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # If user has a stored password hash, verify with bcrypt
    if user and user.password_hash:
        if not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
    else:
        # For initial development seed accounts without password hash, allow default demo password
        if req.password not in ("Password123!", "password", "demo123"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

    # Issue 10-minute verification OTP on the resolved email
    otp, code = AuthService.create_or_refresh_otp(db, auth_email)

    resp_data = {
        "success": True,
        "message": "Credentials verified. One-time passcode sent to your email.",
        "email": req.email.strip().lower(),
    }
    if settings.ENVIRONMENT == "development":
        resp_data["dev_code"] = code

    return resp_data


@router.post("/verify-otp", status_code=status.HTTP_200_OK)
def verify_otp(
    req: VerifyOtpRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Verifies 6-digit OTP code against 10-minute expiry and 5 attempt limit.
    Issues signed JWT and sets secure httpOnly session cookie.
    """
    check_rate_limit(request, req.email)
    auth_email = resolve_auth_email(db, req.email)

    user = AuthService.verify_otp(db, auth_email, req.code)

    # Match user's email to employee profile
    emp = db.query(Employee).filter(
        or_(
            Employee.email == user.email,
            Employee.email == user.email.replace("@example.com", "@company.com"),
            Employee.email == user.email.replace("@company.com", "@example.com"),
        )
    ).first()
    if emp and user.employee_id != emp.employee_id:
        user.employee_id = emp.employee_id
        db.commit()

    # Generate JWT token
    token_claims = {
        "sub": user.employee_id,
        "role": user.role,
        "org_id": user.organization_id,
        "email": user.email,
    }
    token = create_access_token(token_claims)

    # Set secure httpOnly cookie session
    set_auth_cookie(response, token)

    emp = db.query(Employee).filter(Employee.employee_id == user.employee_id).first()
    persona_data = {
        "id": user.employee_id,
        "name": emp.full_name if emp else user.email.split("@")[0].capitalize(),
        "role": user.role,
        "email": user.email,
        "department": "Engineering" if user.role == "employee" else ("Management" if user.role == "manager" else "Human Resources"),
    }

    return {
        "success": True,
        "token": token,
        "role": user.role,
        "persona": persona_data,
        "email": user.email,
        "message": "Identity verified successfully. Session established.",
    }


@router.post("/resend-otp", status_code=status.HTTP_200_OK)
def resend_otp(req: ResendOtpRequest, request: Request, db: Session = Depends(get_db)):
    """
    Resends OTP code respecting the 60-second cooldown timer.
    """
    check_rate_limit(request, req.email)
    auth_email = resolve_auth_email(db, req.email)

    otp, code = AuthService.create_or_refresh_otp(db, auth_email)

    resp_data = {
        "success": True,
        "message": "A new verification code has been sent to your email.",
        "email": req.email.strip().lower(),
    }
    if settings.ENVIRONMENT == "development":
        resp_data["dev_code"] = code

    return resp_data
    if settings.ENVIRONMENT == "development":
        resp_data["dev_code"] = code

    return resp_data


@router.post("/google", status_code=status.HTTP_200_OK)
def google_auth(
    req: GoogleAuthRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Sign in with Google (Identity Services).
    Verifies ID token server-side, derives employee role, and establishes httpOnly session.
    """
    check_rate_limit(request, "google_auth")
    google_payload = AuthService.verify_google_id_token(req.credential)
    email = google_payload["email"].strip().lower()
    google_sub = google_payload["sub"]
    name = google_payload.get("name", email.split("@")[0].capitalize())

    # Find or link employee record
    user = db.query(UserAuth).filter(UserAuth.email == email).first()
    emp = db.query(Employee).filter(Employee.email == email).first()

    if not emp:
        import uuid
        emp_id = f"EMP-{uuid.uuid4().hex[:6].upper()}"
        emp = Employee(
            employee_id=emp_id,
            organization_id=settings.ORGANIZATION_ID,
            email=email,
            full_name=name,
            is_active=True,
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)

    if not user:
        role = "manager" if "manager" in email or emp.employee_id.startswith("MGR") else (
            "hr_admin" if "hr" in email or emp.employee_id.startswith("HR") else "employee"
        )
        user = UserAuth(
            employee_id=emp.employee_id,
            organization_id=settings.ORGANIZATION_ID,
            email=email,
            role=role,
            google_sub=google_sub,
            is_verified=True,
        )
        db.add(user)
    else:
        user.google_sub = google_sub
        user.is_verified = True

    db.commit()
    db.refresh(user)

    # Issue signed JWT token
    token_claims = {
        "sub": user.employee_id,
        "role": user.role,
        "org_id": user.organization_id,
        "email": user.email,
    }
    token = create_access_token(token_claims)

    # Set httpOnly cookie session
    set_auth_cookie(response, token)

    persona_data = {
        "id": user.employee_id,
        "name": emp.full_name,
        "role": user.role,
        "email": user.email,
        "department": "Engineering" if user.role == "employee" else ("Management" if user.role == "manager" else "Human Resources"),
    }

    return {
        "success": True,
        "token": token,
        "role": user.role,
        "persona": persona_data,
        "email": user.email,
        "message": "Signed in with Google successfully.",
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(response: Response):
    """
    Clears the httpOnly session cookie.
    """
    clear_auth_cookie(response)
    return {"success": True, "message": "Logged out successfully."}


@router.get("/me", status_code=status.HTTP_200_OK)
def get_current_user_info(
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Derives identity strictly on the server-side from httpOnly cookie or verified token.
    """
    emp = db.query(Employee).filter(Employee.employee_id == actor.actor_id).first()
    return {
        "actor_id": actor.actor_id,
        "email": actor.email or (emp.email if emp else f"{actor.actor_id.lower()}@example.com"),
        "full_name": emp.full_name if emp else actor.actor_id,
        "role": actor.role,
        "organization_id": actor.organization_id,
        "is_service": actor.is_service,
    }
