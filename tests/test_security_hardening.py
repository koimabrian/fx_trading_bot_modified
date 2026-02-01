"""
Security Hardening Tests

Tests for input validation, CSRF protection, rate limiting, and encryption.

Author: FX Trading Bot Team
Date: February 1, 2026
"""

import pytest
from src.utils.security_hardening import (
    InputValidator,
    CSRFProtection,
    RateLimiter,
    EncryptionManager,
    SecurityHeaders,
)


class TestInputValidator:
    """Test input validation and sanitization"""

    def test_validate_email_valid(self):
        """Test valid email validation"""
        assert InputValidator.validate_email("user@example.com")
        assert InputValidator.validate_email("test.user+tag@sub.example.org")

    def test_validate_email_invalid(self):
        """Test invalid email validation"""
        assert not InputValidator.validate_email("invalid.email")
        assert not InputValidator.validate_email("user@")
        assert not InputValidator.validate_email("@example.com")
        assert not InputValidator.validate_email(123)

    def test_validate_username(self):
        """Test username validation"""
        assert InputValidator.validate_username("valid_user-123")
        assert not InputValidator.validate_username("ab")  # Too short
        assert not InputValidator.validate_username("a" * 21)  # Too long
        assert not InputValidator.validate_username("invalid@user")

    def test_validate_symbol(self):
        """Test trading symbol validation"""
        assert InputValidator.validate_symbol("EURUSD")
        assert InputValidator.validate_symbol("eurusd")
        assert not InputValidator.validate_symbol("EUR")  # Too short
        assert not InputValidator.validate_symbol("EUR_USD")  # Invalid format

    def test_validate_numeric(self):
        """Test numeric validation"""
        assert InputValidator.validate_numeric("123.45")
        assert InputValidator.validate_numeric("-50")
        assert InputValidator.validate_numeric("0")
        assert not InputValidator.validate_numeric("abc")
        assert not InputValidator.validate_numeric("12.34.56")

    def test_validate_numeric_with_bounds(self):
        """Test numeric validation with bounds"""
        assert InputValidator.validate_numeric("50", min_val=0, max_val=100)
        assert not InputValidator.validate_numeric("150", min_val=0, max_val=100)
        assert not InputValidator.validate_numeric("-10", min_val=0)

    def test_sanitize_input(self):
        """Test input sanitization"""
        # Remove null bytes
        assert "\x00" not in InputValidator.sanitize_input("test\x00string")

        # Limit length
        long_string = "a" * 2000
        result = InputValidator.sanitize_input(long_string)
        assert len(result) <= 1000

        # Strip whitespace
        assert InputValidator.sanitize_input("  test  ") == "test"

    def test_sanitize_html(self):
        """Test HTML sanitization for XSS prevention"""
        # Allowed tags
        assert "<b>" in InputValidator.sanitize_html("<b>bold</b>")

        # Dangerous scripts removed
        result = InputValidator.sanitize_html('<script>alert("xss")</script>')
        assert "script" not in result

        # Event handlers removed
        result = InputValidator.sanitize_html('<a onclick="alert()">link</a>')
        assert "onclick" not in result

    def test_prevent_sql_injection(self):
        """Test SQL injection prevention"""
        # Valid input passes
        assert InputValidator.prevent_sql_injection("normal input")

        # SQL keywords raise error
        with pytest.raises(ValueError):
            InputValidator.prevent_sql_injection("'; DROP TABLE users; --")

        with pytest.raises(ValueError):
            InputValidator.prevent_sql_injection("1' OR '1'='1")


class TestCSRFProtection:
    """Test CSRF token management"""

    def test_generate_csrf_token(self):
        """Test CSRF token generation"""
        token = CSRFProtection.generate_csrf_token()
        assert isinstance(token, str)
        assert len(token) == 64  # 32 bytes * 2 for hex

    def test_get_csrf_token_creates_on_first_call(self):
        """Test CSRF token creation in session"""
        session = {}
        token1 = CSRFProtection.get_csrf_token(session)
        assert "csrf_token" in session
        assert token1 == session["csrf_token"]

    def test_get_csrf_token_reuses_existing(self):
        """Test CSRF token reuse"""
        session = {}
        token1 = CSRFProtection.get_csrf_token(session)
        token2 = CSRFProtection.get_csrf_token(session)
        assert token1 == token2

    def test_verify_csrf_token_valid(self):
        """Test CSRF token verification with valid token"""
        session = {}
        token = CSRFProtection.get_csrf_token(session)
        assert CSRFProtection.verify_csrf_token(session, token)

    def test_verify_csrf_token_invalid(self):
        """Test CSRF token verification with invalid token"""
        session = {}
        CSRFProtection.get_csrf_token(session)
        assert not CSRFProtection.verify_csrf_token(session, "invalid_token")

    def test_verify_csrf_token_empty_session(self):
        """Test CSRF token verification with empty session"""
        assert not CSRFProtection.verify_csrf_token({}, "any_token")

    def test_rotate_csrf_token(self):
        """Test CSRF token rotation"""
        session = {}
        token1 = CSRFProtection.get_csrf_token(session)
        token2 = CSRFProtection.rotate_csrf_token(session)
        assert token1 != token2
        assert CSRFProtection.verify_csrf_token(session, token2)
        assert not CSRFProtection.verify_csrf_token(session, token1)


class TestRateLimiter:
    """Test rate limiting"""

    def test_rate_limiter_initialization(self):
        """Test rate limiter creation"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        assert limiter.max_requests == 10
        assert limiter.window_seconds == 60

    def test_rate_limiter_allows_requests_within_limit(self):
        """Test rate limiter allows requests within limit"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        for i in range(5):
            assert not limiter.is_rate_limited("test_client")

    def test_rate_limiter_blocks_requests_exceeding_limit(self):
        """Test rate limiter blocks requests exceeding limit"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)

        # Use up the limit
        for i in range(3):
            limiter.is_rate_limited("test_client")

        # Next request should be blocked
        assert limiter.is_rate_limited("test_client")

    def test_rate_limiter_multiple_clients(self):
        """Test rate limiter tracks clients separately"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        # Client 1 uses limit
        limiter.is_rate_limited("client_1")
        limiter.is_rate_limited("client_1")

        # Client 2 should still have requests
        assert not limiter.is_rate_limited("client_2")
        assert limiter.is_rate_limited("client_1")

    def test_get_remaining_requests(self):
        """Test get remaining requests calculation"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        limiter.is_rate_limited("test_client")
        limiter.is_rate_limited("test_client")

        remaining = limiter.get_remaining_requests("test_client")
        assert remaining == 3


class TestEncryptionManager:
    """Test encryption functionality"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "test_password_123"
        hash1 = EncryptionManager.hash_password(password)
        hash2 = EncryptionManager.hash_password(password)

        # Different hashes for same password
        assert hash1 != hash2
        # Both verify correctly
        assert EncryptionManager.verify_password(password, hash1)
        assert EncryptionManager.verify_password(password, hash2)

    def test_verify_password_incorrect(self):
        """Test password verification with wrong password"""
        password = "correct_password"
        wrong_password = "wrong_password"

        password_hash = EncryptionManager.hash_password(password)
        assert not EncryptionManager.verify_password(wrong_password, password_hash)

    def test_hash_sensitive_data(self):
        """Test sensitive data hashing"""
        data = "sensitive_api_key_12345"
        hash1 = EncryptionManager.hash_sensitive_data(data)

        # Should contain salt and hash
        assert "$" in hash1
        salt, hash_hex = hash1.split("$")
        assert len(salt) > 0
        assert len(hash_hex) > 0

    def test_verify_sensitive_data(self):
        """Test sensitive data verification"""
        data = "sensitive_api_key_12345"
        data_hash = EncryptionManager.hash_sensitive_data(data)

        # Correct data verifies
        assert EncryptionManager.verify_sensitive_data(data, data_hash)

        # Wrong data doesn't verify
        assert not EncryptionManager.verify_sensitive_data("wrong_data", data_hash)


class TestSecurityHeaders:
    """Test security header configuration"""

    def test_security_headers_present(self):
        """Test all security headers are present"""
        headers = SecurityHeaders.get_headers()

        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Strict-Transport-Security" in headers
        assert "Content-Security-Policy" in headers
        assert "Referrer-Policy" in headers
        assert "Permissions-Policy" in headers

    def test_x_frame_options_deny(self):
        """Test X-Frame-Options is set to DENY"""
        headers = SecurityHeaders.get_headers()
        assert headers["X-Frame-Options"] == "DENY"

    def test_content_type_options_nosniff(self):
        """Test X-Content-Type-Options is set to nosniff"""
        headers = SecurityHeaders.get_headers()
        assert headers["X-Content-Type-Options"] == "nosniff"

    def test_hsts_header_present(self):
        """Test HSTS header is present"""
        headers = SecurityHeaders.get_headers()
        hsts = headers["Strict-Transport-Security"]
        assert "max-age=" in hsts
        assert "includeSubDomains" in hsts


# Integration tests
class TestSecurityIntegration:
    """Integration tests for security features"""

    def test_user_registration_flow(self):
        """Test secure user registration"""
        # Validate email
        email = "newuser@example.com"
        assert InputValidator.validate_email(email)

        # Sanitize username
        username = InputValidator.sanitize_input("New User 123")
        assert username == "New User 123"

        # Hash password
        password = "SecurePassword123!"
        password_hash = EncryptionManager.hash_password(password)

        # Verify can check password
        assert EncryptionManager.verify_password(password, password_hash)

    def test_api_request_protection(self):
        """Test API request protection"""
        session = {}

        # Generate CSRF token
        csrf_token = CSRFProtection.get_csrf_token(session)
        assert csrf_token is not None

        # Verify CSRF token
        assert CSRFProtection.verify_csrf_token(session, csrf_token)

        # Rate limiting
        limiter = RateLimiter(max_requests=10, window_seconds=3600)
        client_id = "test_api_client"

        # Make requests up to limit
        for i in range(10):
            assert not limiter.is_rate_limited(client_id)

        # Next request blocked
        assert limiter.is_rate_limited(client_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
