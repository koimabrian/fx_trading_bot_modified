"""
Flask Security Configuration

Sets up security headers, CORS, and HTTPS enforcement for the Flask application.

Author: FX Trading Bot Team
Date: February 1, 2026
"""

import os
from flask import Flask
from flask_cors import CORS
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def configure_flask_security(app: Flask) -> Flask:
    """
    Configure all security features for Flask application

    Args:
        app: Flask application instance

    Returns:
        Configured Flask application
    """

    # ==================== HTTPS/TLS ====================
    # Force HTTPS in production
    Talisman(
        app,
        force_https=os.getenv("FLASK_ENV") == "production",
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,  # 1 year
        strict_transport_security_include_subdomains=True,
        content_security_policy={
            "default-src": "'self'",
            "script-src": ["'self'", "'unsafe-inline'"],
            "style-src": ["'self'", "'unsafe-inline'"],
        },
        content_security_policy_nonce_in=["script-src"],
    )

    # ==================== CORS Configuration ====================
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5000").split(",")

    CORS(
        app,
        origins=allowed_origins,
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
        expose_headers=["X-Total-Count", "X-Page-Number"],
        supports_credentials=True,
        max_age=3600,  # 1 hour
    )

    # ==================== Rate Limiting ====================
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",  # Use Redis for production
    )

    # ==================== Security Headers ====================
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # Remove server information
        response.headers.pop("Server", None)
        response.headers["Server"] = "FXBot/1.0"

        return response

    # ==================== Error Handling ====================
    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad requests"""
        return {
            "error": "Bad Request",
            "message": "Invalid request parameters",
            "status": 400,
        }, 400

    @app.errorhandler(403)
    def forbidden(error):
        """Handle forbidden requests"""
        return {"error": "Forbidden", "message": "Access denied", "status": 403}, 403

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle rate limit exceeded"""
        return {
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Try again later.",
            "status": 429,
            "retry_after": 60,
        }, 429

    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors"""
        return {
            "error": "Internal Server Error",
            "message": "An error occurred processing your request",
            "status": 500,
        }, 500

    return app, limiter


def configure_session_security(app: Flask) -> None:
    """
    Configure Flask session security.

    Args:
        app: Flask application instance.

    Returns:
        None.
    """
    # Session configuration
    app.config.update(
        SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV") == "production",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
        SESSION_REFRESH_EACH_REQUEST=True,
    )


def configure_database_security(app: Flask) -> None:
    """
    Configure database security settings.

    Args:
        app: Flask application instance.

    Returns:
        None.
    """
    # Use parameterized queries (handled by ORM)
    app.config.update(
        SQLALCHEMY_ECHO=os.getenv("FLASK_ENV") != "production",
        SQLALCHEMY_RECORD_QUERIES=True,
    )


def setup_secrets_management() -> dict:
    """
    Setup secrets management

    Returns:
        Dictionary of required secrets
    """
    required_secrets = {
        "SECRET_KEY": os.getenv("SECRET_KEY"),
        "DATABASE_URL": os.getenv("DATABASE_URL"),
        "API_KEY": os.getenv("API_KEY"),
        "ENCRYPTION_KEY": os.getenv("ENCRYPTION_KEY"),
    }

    # Validate all secrets are set
    missing_secrets = [k for k, v in required_secrets.items() if not v]
    if missing_secrets:
        raise ValueError(f"Missing required secrets: {', '.join(missing_secrets)}")

    return required_secrets
