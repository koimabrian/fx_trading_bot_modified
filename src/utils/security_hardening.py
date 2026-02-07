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
from typing import Any, Callable, Dict, List, Optional

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
        """Validate email format.

        Args:
            email: Email address to validate.

        Returns:
            True if valid email format, False otherwise.
        """
        if not isinstance(email, str) or len(email) > 254:
            return False
        return bool(re.match(InputValidator.PATTERNS["email"], email))

    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format.

        Args:
            username: Username to validate.

        Returns:
            True if valid username format, False otherwise.
        """
        if not isinstance(username, str):
            return False
        return bool(re.match(InputValidator.PATTERNS["username"], username))

    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """Validate trading symbol (e.g., EURUSD).

        Args:
            symbol: Trading symbol to validate.

        Returns:
            True if valid symbol format, False otherwise.
        """
        if not isinstance(symbol, str):
            return False
        return bool(re.match(InputValidator.PATTERNS["symbol"], symbol.upper()))

    @staticmethod
    def validate_numeric(
        value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None
    ) -> bool:
        """Validate numeric value with optional bounds.

        Args:
            value: Value to validate.
            min_val: Optional minimum allowed value.
            max_val: Optional maximum allowed value.

        Returns:
            True if value is numeric and within bounds, False otherwise.
        """
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
        """Sanitize string input.

        Args:
            value: String to sanitize.
            max_length: Maximum allowed length.

        Returns:
            Sanitized string with null bytes and control characters removed.
        """
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
        """Sanitize HTML to prevent XSS.

        Args:
            html: HTML string to sanitize.

        Returns:
            Sanitized HTML with only allowed tags and attributes.
        """
        return bleach.clean(
            html,
            tags=InputValidator.ALLOWED_TAGS,
            attributes=InputValidator.ALLOWED_ATTRIBUTES,
            strip=True,
        )

    @staticmethod
    def prevent_sql_injection(user_input: str) -> str:
        """Basic SQL injection prevention (use parameterized queries instead).

        Args:
            user_input: User-provided input to check.

        Returns:
            Original input if safe.

        Raises:
            ValueError: If potentially dangerous SQL patterns detected.
        """
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
        """Generate a new CSRF token.

        Returns:
            Hex-encoded random token string.
        """
        return secrets.token_hex(CSRFProtection.TOKEN_LENGTH)

    @staticmethod
    def get_csrf_token(session_obj: Dict) -> str:
        """Get or create CSRF token in session.

        Args:
            session_obj: Session dictionary to store token in.

        Returns:
            CSRF token string.
        """
        if "csrf_token" not in session_obj:
            session_obj["csrf_token"] = CSRFProtection.generate_csrf_token()
            session_obj["csrf_token_time"] = datetime.utcnow().isoformat()
        return session_obj["csrf_token"]

    @staticmethod
    def verify_csrf_token(session_obj: Dict, token: str) -> bool:
        """Verify CSRF token.

        Args:
            session_obj: Session dictionary containing stored token.
            token: Token to verify.

        Returns:
            True if token is valid and not expired, False otherwise.
        """
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
        """Rotate CSRF token after sensitive operations.

        Args:
            session_obj: Session dictionary to update.

        Returns:
            New CSRF token string.
        """
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
        """Get unique client identifier.

        Returns:
            Client identifier string based on user or IP.
        """
        if request.remote_user:
            return f"user:{request.remote_user}"
        return f"ip:{request.remote_addr}"

    def is_rate_limited(self, client_id: Optional[str] = None) -> bool:
        """Check if client is rate limited.

        Args:
            client_id: Optional client identifier to check.

        Returns:
            True if client has exceeded rate limit, False otherwise.
        """
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
        """Get remaining requests for client.

        Args:
            client_id: Optional client identifier to check.

        Returns:
            Number of requests remaining in current window.
        """
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
        """Hash password for storage.

        Args:
            password: Plain text password.
            method: Hashing method to use.

        Returns:
            Hashed password string.
        """
        return generate_password_hash(password, method=method)

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash.

        Args:
            password: Plain text password to verify.
            password_hash: Stored password hash.

        Returns:
            True if password matches hash, False otherwise.
        """
        return check_password_hash(password_hash, password)

    @staticmethod
    def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
        """Hash sensitive data like API keys.

        Args:
            data: Sensitive data to hash.
            salt: Optional salt value.

        Returns:
            Salted hash string in format 'salt$hash'.
        """
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
        """Verify sensitive data against hash.

        Args:
            data: Data to verify.
            data_hash: Stored hash to verify against.

        Returns:
            True if data matches hash, False otherwise.
        """
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
        """Get all security headers.

        Returns:
            Dictionary of security header names and values.
        """
        return SecurityHeaders.HEADERS.copy()

    @staticmethod
    def add_security_headers(response):
        """Add security headers to Flask response.

        Args:
            response: Flask response object.

        Returns:
            Response with security headers added.
        """
        for header, value in SecurityHeaders.HEADERS.items():
            response.headers[header] = value
        return response


def require_https(f: Callable) -> Callable:
    """Decorator to require HTTPS.

    Args:
        f: Function to decorate.

    Returns:
        Decorated function that aborts with 403 if not HTTPS in production.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_secure and os.getenv("FLASK_ENV") == "production":
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


def require_csrf_token(f: Callable) -> Callable:
    """Decorator to verify CSRF token on POST/PUT/DELETE.

    Args:
        f: Function to decorate.

    Returns:
        Decorated function that verifies CSRF token for mutating requests.
    """

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
    """Decorator for rate limiting.

    Args:
        limiter: RateLimiter instance to use.

    Returns:
        Decorator function that applies rate limiting.
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if limiter.is_rate_limited():
                abort(429)  # Too Many Requests
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def validate_input(param_name: str, validator: Callable):
    """Decorator to validate request parameters.

    Args:
        param_name: Name of parameter to validate.
        validator: Validation function returning True if valid.

    Returns:
        Decorator function that validates the specified parameter.
    """

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
