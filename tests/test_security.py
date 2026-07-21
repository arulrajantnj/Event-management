import os
import re

import pytest
from werkzeug.security import generate_password_hash


os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-and-not-for-production")
os.environ.setdefault("ADMIN_USERNAME", "security-test-admin")
os.environ.setdefault("ADMIN_PASSWORD_HASH", generate_password_hash("security-test-password"))

from app import app as flask_app  # noqa: E402


@pytest.fixture()
def app():
    flask_app.config.update(TESTING=True, RATELIMIT_ENABLED=False)
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


def csrf_from(html):
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "Expected a CSRF token in every POST form"
    return match.group(1)


def test_security_headers_and_csrf_token_are_rendered(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "frame-ancestors 'self'" in response.headers["Content-Security-Policy"]
    csrf_from(response.get_data(as_text=True))


def test_post_without_csrf_is_rejected(client):
    response = client.post(
        "/login",
        data={"username": "security-test-admin", "password": "security-test-password"},
    )

    assert response.status_code == 400
    assert "traceback" not in response.get_data(as_text=True).lower()


def test_post_with_csrf_reaches_login_handler(client):
    login_page = client.get("/login")
    token = csrf_from(login_page.get_data(as_text=True))
    response = client.post(
        "/login",
        data={
            "username": "wrong-user",
            "password": "wrong-password",
            "csrf_token": token,
        },
    )

    assert response.status_code == 200
    assert "Invalid Username or Password" in response.get_data(as_text=True)


def test_configured_admin_password_is_hashed(client):
    login_page = client.get("/login")
    token = csrf_from(login_page.get_data(as_text=True))
    response = client.post(
        "/login",
        data={
            "username": "security-test-admin",
            "password": "security-test-password",
            "csrf_token": token,
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin")


def test_login_rate_limit_blocks_repeated_attempts(app):
    app.config["RATELIMIT_ENABLED"] = True
    client = app.test_client()
    token = csrf_from(client.get("/login").get_data(as_text=True))
    responses = [
        client.post(
            "/login",
            data={"username": "wrong", "password": "wrong", "csrf_token": token},
            environ_overrides={"REMOTE_ADDR": "192.0.2.45"},
        )
        for _ in range(6)
    ]
    app.config["RATELIMIT_ENABLED"] = False

    assert [response.status_code for response in responses[:5]] == [200] * 5
    assert responses[5].status_code == 429
