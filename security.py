import hmac
import os
import re
from datetime import timedelta

from flask import current_app, request
from flask_wtf.csrf import generate_csrf
from werkzeug.security import check_password_hash

# Retains the original administrator login without storing its plaintext
# password. Deployments can override both values through environment variables.
LEGACY_ADMIN_USERNAME = "Arulrajan"
LEGACY_ADMIN_PASSWORD_HASH = (
    "scrypt:32768:8:1$gCugMzZLnxlipeE7$"
    "4d26f9794df8488d2f5229de5042b4cb784815aed417018fa1790e0fed3f26ad"
    "fa5207d5fb4438dcaf4a038222c0d85fa9204195c4e57b3c8797564f53a5e0ea"
)

POST_FORM_RE = re.compile(
    r"(<form\b(?=[^>]*\bmethod\s*=\s*(['\"]?)post\2)[^>]*>)",
    flags=re.IGNORECASE,
)


def configure_security(app):
    environment = os.getenv("FLASK_ENV", os.getenv("APP_ENV", "development")).lower()
    production = environment in {"production", "prod"}
    secret_key = os.getenv("SECRET_KEY", "").strip()

    if production and len(secret_key) < 32:
        raise RuntimeError("SECRET_KEY must contain at least 32 characters in production.")
    if not secret_key:
        # Development-only random key avoids a committed fallback credential.
        secret_key = os.urandom(32).hex()
        app.logger.warning(
            "SECRET_KEY is not configured; using a temporary development key. "
            "Sessions will be invalidated when the process restarts."
        )

    app.config.update(
        SECRET_KEY=secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=production,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(
            minutes=max(5, int(os.getenv("SESSION_TIMEOUT_MINUTES", "60")))
        ),
        WTF_CSRF_TIME_LIMIT=max(
            15, int(os.getenv("CSRF_TIMEOUT_MINUTES", "120"))
        ) * 60,
        MAX_CONTENT_LENGTH=max(
            1, int(os.getenv("MAX_UPLOAD_MB", "10"))
        ) * 1024 * 1024,
        ADMIN_USERNAME=os.getenv("ADMIN_USERNAME", "").strip(),
        ADMIN_PASSWORD_HASH=os.getenv("ADMIN_PASSWORD_HASH", "").strip(),
        RATELIMIT_STORAGE_URI=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
    )


def install_security_hooks(app):
    @app.after_request
    def secure_response(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(self)",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "base-uri 'self'; form-action 'self' https://api.razorpay.com; "
            "frame-ancestors 'self'; object-src 'none'; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' data: https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://code.jquery.com; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://checkout.razorpay.com https://code.jquery.com https://unpkg.com; "
            "connect-src 'self' https://api.razorpay.com; "
            "frame-src 'self' https://api.razorpay.com https://checkout.razorpay.com;",
        )

        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        content_type = response.headers.get("Content-Type", "")
        if response.status_code < 400 and "text/html" in content_type.lower():
            html = response.get_data(as_text=True)
            if "<form" in html.lower():
                token = generate_csrf()
                hidden = (
                    '<input type="hidden" name="csrf_token" value="'
                    + token
                    + '">'
                )
                html = POST_FORM_RE.sub(lambda match: match.group(1) + hidden, html)
                response.set_data(html)

        return response


def configured_admin_credentials_match(username, password):
    configured_username = (
        current_app.config.get("ADMIN_USERNAME") or LEGACY_ADMIN_USERNAME
    )
    password_hash = (
        current_app.config.get("ADMIN_PASSWORD_HASH") or LEGACY_ADMIN_PASSWORD_HASH
    )
    return hmac.compare_digest(username or "", configured_username) and check_password_hash(
        password_hash, password or ""
    )
