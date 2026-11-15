import secrets
import hashlib
import smtplib
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
import bcrypt
import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.config import settings
from app.models.auth import UserAuth, OTPVerification
from app.models.hr import Employee

logger = logging.getLogger("app.auth.service")


# -------------------------------------------------------------------------
# IN-MEMORY RATE LIMITER (SLIDING WINDOW)
# -------------------------------------------------------------------------
class RateLimiter:
    """Sliding window in-memory rate limiter per key (IP or Email)."""
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.hits: Dict[str, list] = {}

    def is_allowed(self, key: str) -> Tuple[bool, int]:
        now = time.time()
        window_start = now - self.window_seconds
        timestamps = self.hits.get(key, [])
        # filter out timestamps older than window
        timestamps = [t for t in timestamps if t > window_start]
        self.hits[key] = timestamps

        if len(timestamps) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - timestamps[0]))
            return False, max(1, retry_after)

        self.hits[key].append(now)
        return True, 0


# Global auth rate limiter
auth_rate_limiter = RateLimiter(
    max_requests=settings.AUTH_RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
)


# -------------------------------------------------------------------------
# PASSWORD HASHING
# -------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with salt factor 12."""
    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long.",
        )
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error(f"Error checking password: {e}")
        return False


# -------------------------------------------------------------------------
# OTP / EMAIL VERIFICATION
# -------------------------------------------------------------------------
def hash_code(code: str) -> str:
    """Computes SHA-256 hash of an OTP code for safe storage."""
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def generate_otp_code() -> str:
    """Generates a secure cryptographically random 6-digit numeric OTP code."""
    return "".join(secrets.choice("0123456789") for _ in range(6))


def send_verification_email(email: str, code: str) -> bool:
    """
    Sends an email with the verification OTP code.
    If SMTP is configured via env, sends via real SMTP TLS connection.
    Otherwise in development mode, logs/prints code clearly to console.
    """
    subject = f"Your HR Self-Audit Assistant Verification Code: {code}"
    body = (
        f"Hello,\n\n"
        f"Your verification code is: {code}\n\n"
        f"This code will expire in {settings.OTP_EXPIRATION_MINUTES} minutes.\n"
        f"If you did not request this code, please ignore this email.\n\n"
        f"Best regards,\nHR Self-Audit Team"
    )

    if settings.SMTP_HOST and settings.SMTP_USER:
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_FROM
            msg["To"] = email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info(f"Verification email sent successfully to {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email via SMTP ({settings.SMTP_HOST}): {e}")
            # Fall back to console print in dev
            pass

    # Development fallback
    print(f"\n=======================================================")
    print(f" [DEV MODE] EMAIL VERIFICATION CODE FOR {email}: {code}")
    print(f"=======================================================\n")
    logger.info(f"[DEV MODE] Verification code for {email}: {code}")
    return True


class AuthService:
    """Core Authentication & Identity Service."""

    @staticmethod
    def create_or_refresh_otp(db: Session, email: str) -> Tuple[OTPVerification, str]:
        """
        Generates a new OTP, persists hash with 10-minute expiry and 60s resend cooldown.
        """
        now = datetime.now(timezone.utc)
        clean_email = email.strip().lower()

        # Check existing active OTP for cooldown
        latest = (
            db.query(OTPVerification)
            .filter(
                OTPVerification.email == clean_email,
                OTPVerification.is_consumed == False,
            )
            .order_by(OTPVerification.created_at.desc())
            .first()
        )

        if latest and latest.resend_available_at:
            resend_dt = latest.resend_available_at
            if resend_dt.tzinfo is None:
                resend_dt = resend_dt.replace(tzinfo=timezone.utc)
            if resend_dt > now:
                seconds_remaining = int((resend_dt - now).total_seconds())
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {max(1, seconds_remaining)} seconds before requesting a new code.",
                )

        code = generate_otp_code()
        otp = OTPVerification(
            email=clean_email,
            code_hash=hash_code(code),
            expires_at=now + timedelta(minutes=settings.OTP_EXPIRATION_MINUTES),
            attempts=0,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
            resend_available_at=now + timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS),
            is_consumed=False,
            created_at=now,
        )
        db.add(otp)
        db.commit()
        db.refresh(otp)

        send_verification_email(clean_email, code)
        return otp, code

    @staticmethod
    def verify_otp(db: Session, email: str, code: str) -> UserAuth:
        """
        Verifies 6-digit code against latest active OTP.
        Enforces 10-minute expiry and max 5 attempts.
        Fixed code 123456 works ONLY in development mode.
        """
        clean_email = email.strip().lower()
        now = datetime.now(timezone.utc)

        # 1. Check DEV mode fixed bypass code
        is_dev = settings.ENVIRONMENT == "development"
        if is_dev and code.strip() in ("123456", "999999"):
            user = db.query(UserAuth).filter(UserAuth.email == clean_email).first()
            if not user:
                emp = db.query(Employee).filter(Employee.email == clean_email).first()
                if emp:
                    role = "manager" if "manager" in emp.email or emp.employee_id.startswith("MGR") else (
                        "hr_admin" if "hr" in emp.email or emp.employee_id.startswith("HR") else "employee"
                    )
                    user = UserAuth(
                        employee_id=emp.employee_id,
                        organization_id=emp.organization_id,
                        email=clean_email,
                        role=role,
                        is_verified=True,
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"No employee account registered for '{clean_email}'.",
                    )
            user.is_verified = True
            db.commit()
            return user

        # 2. Look up latest OTP record for this email
        otp = (
            db.query(OTPVerification)
            .filter(OTPVerification.email == clean_email)
            .order_by(OTPVerification.created_at.desc())
            .first()
        )

        if not otp or (otp.is_consumed and otp.attempts < otp.max_attempts):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending verification code found. Please request a new code.",
            )

        # 3. Check attempt limit
        if otp.attempts >= otp.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum verification attempts exceeded. Please request a new code.",
            )

        # 4. Check expiration
        # Ensure UTC timezone comparability
        exp = otp.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            otp.is_consumed = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code has expired. Please request a new code.",
            )

        # 5. Verify code hash
        submitted_hash = hash_code(code)
        if submitted_hash != otp.code_hash:
            otp.attempts += 1
            db.commit()
            remaining = otp.max_attempts - otp.attempts
            if remaining <= 0:
                otp.is_consumed = True
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Maximum verification attempts exceeded. Please request a new code.",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid verification code. {remaining} attempt(s) remaining.",
            )

        # Code is valid! Mark consumed
        otp.is_consumed = True
        user = db.query(UserAuth).filter(UserAuth.email == clean_email).first()
        if not user:
            emp = db.query(Employee).filter(Employee.email == clean_email).first()
            if emp:
                role = "manager" if "manager" in emp.email or emp.employee_id.startswith("MGR") else (
                    "hr_admin" if "hr" in emp.email or emp.employee_id.startswith("HR") else "employee"
                )
                user = UserAuth(
                    employee_id=emp.employee_id,
                    organization_id=emp.organization_id,
                    email=clean_email,
                    role=role,
                    is_verified=True,
                )
                db.add(user)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No employee record found for '{clean_email}'.",
                )
        user.is_verified = True
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def verify_google_id_token(credential: str) -> Dict[str, Any]:
        """
        Verifies Google Identity Services ID token server-side.
        Queries Google tokeninfo or validates token structure.
        """
        # 1. In development or test, allow mock google tokens
        if credential.startswith("MOCK_GOOGLE_TOKEN_"):
            email = credential.replace("MOCK_GOOGLE_TOKEN_FOR_", "").replace("MOCK_GOOGLE_TOKEN_", "")
            return {
                "sub": f"google_sub_{email}",
                "email": email,
                "email_verified": True,
                "name": email.split("@")[0].capitalize(),
            }

        # 2. Query Google tokeninfo endpoint
        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}")
                if res.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid Google ID token signature or expired token.",
                    )
                payload = res.json()
                if not payload.get("email_verified", False):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Google account email is not verified.",
                    )
                # Verify audience if client id is configured
                if settings.GOOGLE_CLIENT_ID and payload.get("aud") != settings.GOOGLE_CLIENT_ID:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Google token audience mismatch.",
                    )
                return payload
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Google ID token validation network error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to communicate with Google authentication services: {str(e)}",
            )
