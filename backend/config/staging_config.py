"""Fail-closed settings for the separate online CAVI TEST stack."""

import ipaddress
import re
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured


def staging_config(env):
    origin = env.get("CAVI_TEST_ORIGIN", "")
    try:
        url = urlsplit(origin)
        hostname = url.hostname or ""
        port = url.port
    except ValueError as exc:
        raise ImproperlyConfigured("CAVI_TEST_ORIGIN không hợp lệ.") from exc
    forbidden = {"app.vantaiduongbo.net", "vantaiduongbo.net", "www.vantaiduongbo.net"}
    if (url.scheme != "https" or url.username or url.password or port not in (None, 443)
            or url.path not in ("", "/") or url.query or url.fragment
            or hostname in forbidden or hostname.endswith(".")
            or not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", hostname)):
        raise ImproperlyConfigured("CAVI TEST cần origin HTTPS riêng, không dùng host production, IP, credentials hoặc đường dẫn.")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ImproperlyConfigured("CAVI TEST cần tên miền online riêng, không dùng IP.")
    if hostname.rsplit(".", 1)[-1] in {"local", "localhost", "test", "invalid", "example"} or re.search(r"(^|\.)example\.(com|net|org)$", hostname):
        raise ImproperlyConfigured("Không dùng tên miền mẫu/local làm máy chủ TEST online.")

    secret = env.get("CAVI_TEST_SECRET_KEY", "")
    password = env.get("CAVI_TEST_DB_PASSWORD", "")
    if len(secret) < 50 or len(set(secret)) < 10 or any(word in secret.lower() for word in ("replace", "change-me", "example")):
        raise ImproperlyConfigured("CAVI_TEST_SECRET_KEY phải là secret mới, ngẫu nhiên, ít nhất 50 ký tự; không lấy từ production.")
    if len(password) < 32 or len(set(password)) < 10 or any(word in password.lower() for word in ("replace", "change-me", "example")):
        raise ImproperlyConfigured("CAVI_TEST_DB_PASSWORD phải là mật khẩu TEST mới, ngẫu nhiên, ít nhất 32 ký tự.")
    if secret == password or secret == env.get("DJANGO_SECRET_KEY") or password == env.get("POSTGRES_PASSWORD"):
        raise ImproperlyConfigured("Không dùng chung secret, mật khẩu database hoặc credentials production cho TEST.")
    if env.get("CAVI_TEST_ISOLATION_CONFIRMED") != "true":
        raise ImproperlyConfigured("Phải xác minh stack/database/volume thử riêng trước khi bật CAVI_TEST_ISOLATION_CONFIRMED.")
    release = env.get("CAVI_TEST_RELEASE_ID", "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,79}", release) or release.lower() in {"main", "latest", "preview"}:
        raise ImproperlyConfigured("CAVI_TEST_RELEASE_ID phải chỉ rõ bản đang triển khai, không dùng main/latest.")
    return {"origin": f"https://{hostname}", "host": hostname, "secret": secret, "password": password, "release": release}
