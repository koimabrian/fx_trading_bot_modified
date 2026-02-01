"""
Security Hardening Module for FX Trading Bot

Implements security best practices including:
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF token management
- Rate limiting
- Data encryption
- Security headers
- Secrets management

Author: FX Trading Bot Team
Date: February 1, 2026
"""

import os
import re
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from flask import request, abort, session
import bleach
from werkzeug.security import generate_password_hash, check_password_hash


class InputValidator:
    """Validates and sanitizes user inputs"""

    # Regex patterns for validation
    PATTERNS = {
        "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "username": r"^[a-zA-Z0-9_-]{3,20}$",
        "symbol": r"^[A-Z]{6}$",  # EURUSD format
        "url": r"^https?://[^\s/$.?#].[^\s]*$",
        "numeric": r"^-?\d+(\.\d+)?$",
        "integer": r"^-?\d+$",
    }

    # Allowed HTML tags for rich text
    ALLOWED_TAGS = ["b", "i", "em", "strong", "a", "p", "br", "code", "pre"]
    ALLOWED_ATTRIBUTES = {"a": ["href", "title"]}

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not isinstance(email, str) or len(email) > 254:
            return False
        return bool(re.match(InputValidator.PATTERNS["email"], email))

    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        if not isinstance(username, str):
            return False
        return bool(re.match(InputValidator.PATTERNS["username"], username))

    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """Validate trading symbol (e.g., EURUSD)"""
        if not isinstance(symbol, str):
            return False
        return bool(re.match(InputValidator.PATTERNS["symbol"], symbol.upper()))

    @staticmethod
    def validate_numeric(
        value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None
    ) -> bool:
        """Validate numeric value with optional bounds"""
        try:
            num = float(value)
            if min_val is not None and num < min_val:
                return False
            if max_val is not None and num > max_val:
                return False
            return True
        except (TypeError, ValueError):
            return False

    @staticmethod
    def sanitize_input(value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return ""

        # Limit length
        value = value[:max_length]

        # Remove null bytes
        value = value.replace("\x00", "")

        # Remove control characters
        value = "".join(char for char in value if ord(char) >= 32 or char in "\t\n\r")

        return value.strip()

    @staticmethod
    def sanitize_html(html: str) -> str:
        """Sanitize HTML to prevent XSS"""
        return bleach.clean(
            html,
            tags=InputValidator.ALLOWED_TAGS,
            attributes=InputValidator.ALLOWED_ATTRIBUTES,
            strip=True,
        )

    @staticmethod
    def prevent_sql_injection(user_input: str) -> str:
        """Basic SQL injection prevention (use parameterized queries instead)"""
        dangerous_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)",
            r"(--|#|;)",  # SQL comments and statements
            r"('|\"|\*|=|\/)",  # Quote and operator escaping
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                raise ValueError(f"Potentially dangerous input detected: {user_input}")

        return user_input


class CSRFProtection:
    """CSRF token management and verification"""

    TOKEN_LENGTH = 32
    TOKEN_EXPIRY_HOURS = 24

    @staticmethod
    def generate_csrf_token() -> str:
        """Generate a new CSRF token"""
        return secrets.token_hex(CSRFProtection.TOKEN_LENGTH)

    @staticmethod
    def get_csrf_token(session_obj: Dict) -> str:
        """Get or create CSRF token in session"""
        if "csrf_token" not in session_obj:
            session_obj["csrf_token"] = CSRFProtection.generate_csrf_token()
            session_obj["csrf_token_time"] = datetime.utcnow().isoformat()
        return session_obj["csrf_token"]

    @staticmethod
    def verify_csrf_token(session_obj: Dict, token: str) -> bool:
        """Verify CSRF token"""
        stored_token = session_obj.get("csrf_token")
        token_time = session_obj.get("csrf_token_time")

        if not stored_token or not token_time:
            return False

        # Verify token matches
        if not hmac.compare_digest(stored_token, token):
            return False

        # Verify token hasn't expired
        try:
            token_created = datetime.fromisoformat(token_time)
            if datetime.utcnow() - token_created > timedelta(
                hours=CSRFProtection.TOKEN_EXPIRY_HOURS
            ):
                return False
        except (ValueError, TypeError):
            return False

        return True

    @staticmethod
    def rotate_csrf_token(session_obj: Dict) -> str:
        """Rotate CSRF token after sensitive operations"""
        session_obj["csrf_token"] = CSRFProtection.generate_csrf_token()
        session_obj["csrf_token_time"] = datetime.utcnow().isoformat()
        return session_obj["csrf_token"]


class RateLimiter:
    """Rate limiting implementation"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[datetime]] = {}

    def get_client_id(self) -> str:
        """Get unique client identifier"""
        if request.remote_user:
            return f"user:{request.remote_user}"
        return f"ip:{request.remote_addr}"

    def is_rate_limited(self, client_id: Optional[str] = None) -> bool:
        """Check if client is rate limited"""
        if client_id is None:
            client_id = self.get_client_id()

        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        # Initialize or clean up requests list
        if client_id not in self.requests:
            self.requests[client_id] = []

        # Remove old requests outside window
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id] if req_time > window_start
        ]

        # Check if rate limited
        if len(self.requests[client_id]) >= self.max_requests:
            return True

        # Record new request
        self.requests[client_id].append(now)
        return False

    def get_remaining_requests(self, client_id: Optional[str] = None) -> int:
        """Get remaining requests for client"""
        if client_id is None:
            client_id = self.get_client_id()

        if client_id not in self.requests:
            return self.max_requests

        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        count = len(
            [
                req_time
                for req_time in self.requests[client_id]
                if req_time > window_start
            ]
        )

        return max(0, self.max_requests - count)


class EncryptionManager:
    """Data encryption at rest"""

    @staticmethod
    def hash_password(password: str, method: str = "pbkdf2:sha256") -> str:
        """Hash password for storage"""
        return generate_password_hash(password, method=method)

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return check_password_hash(password_hash, password)

    @staticmethod
    def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
        """Hash sensitive data like API keys"""
        if salt is None:
            salt = secrets.token_hex(16)

        hash_obj = hashlib.pbkdf2_hmac(
            "sha256",
            data.encode("utf-8"),
            salt.encode("utf-8") if isinstance(salt, str) else salt,
            100000,
        )

        return f"{salt}${hash_obj.hex()}"

    @staticmethod
    def verify_sensitive_data(data: str, data_hash: str) -> bool:
        """Verify sensitive data against hash"""
        try:
            salt, hash_hex = data_hash.split("$")
            new_hash = EncryptionManager.hash_sensitive_data(data, salt)
            return hmac.compare_digest(data_hash, new_hash)
        except (ValueError, TypeError):
            return False


class SecurityHeaders:
    """Security header configuration"""

    HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get all security headers"""
        return SecurityHeaders.HEADERS.copy()

    @staticmethod
    def add_security_headers(response):
        """Add security headers to Flask response"""
        for header, value in SecurityHeaders.HEADERS.items():
            response.headers[header] = value
        return response


def require_https(f: Callable) -> Callable:
    """Decorator to require HTTPS"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_secure and os.getenv("FLASK_ENV") == "production":
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


def require_csrf_token(f: Callable) -> Callable:
    """Decorator to verify CSRF token on POST/PUT/DELETE"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ["POST", "PUT", "DELETE"]:
            token = request.form.get("csrf_token") or request.headers.get(
                "X-CSRF-Token"
            )
            if not token or not CSRFProtection.verify_csrf_token(session, token):
                abort(403)
        return f(*args, **kwargs)

    return decorated_function


def rate_limit(limiter: RateLimiter):
    """Decorator for rate limiting"""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if limiter.is_rate_limited():
                abort(429)  # Too Many Requests
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def validate_input(param_name: str, validator: Callable):
    """Decorator to validate request parameters"""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            value = request.args.get(param_name) or request.form.get(param_name)
            if value and not validator(value):
                abort(400)  # Bad Request
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=100, window_seconds=3600)
