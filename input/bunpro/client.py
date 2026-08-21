from __future__ import annotations

import json
import re
import time
from http.cookiejar import CookieJar
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen


class BunproAPIError(RuntimeError):
    """Raised when Bunpro's unofficial frontend API cannot be read."""


class BunproClient:
    """Read-only client for the unofficial API used by the Bunpro website.

    Bunpro does not guarantee this private API will remain stable. Authentication
    follows the site's Rails/Devise login flow and extracts the
    ``frontend_api_token`` cookie, which is then sent as a Bearer token to
    ``api.bunpro.jp/api/frontend/*``.
    """

    DEFAULT_API_URL = "https://api.bunpro.jp"
    DEFAULT_LOGIN_URL = "https://bunpro.jp"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
                 "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    SRS_LEVELS = ("beginner", "adept", "seasoned", "expert", "master")

    _CSRF_PATTERNS = (
        re.compile(r'name=["\']authenticity_token["\'][^>]*value=["\']([^"\']+)', re.I),
        re.compile(r'value=["\']([^"\']+)["\'][^>]*name=["\']authenticity_token["\']', re.I),
    )

    def __init__(
        self,
        email: str,
        password: str,
        *,
        api_url: str = DEFAULT_API_URL,
        login_url: str = DEFAULT_LOGIN_URL,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        if not email.strip():
            raise ValueError("A Bunpro email is required")
        if not password:
            raise ValueError("A Bunpro password is required")
        self.email = email.strip()
        self.password = password
        self.api_url = api_url.rstrip("/")
        self.login_url = login_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._token: str | None = None
        self._cookie_jar = CookieJar()
        self._opener = build_opener(HTTPCookieProcessor(self._cookie_jar))

    def login(self) -> str:
        login_page = Request(
            f"{self.login_url}/login",
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": self.USER_AGENT,
            },
        )
        try:
            with self._opener.open(login_page, timeout=self.timeout) as response:
                html = response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise BunproAPIError(f"Could not load Bunpro login page: {exc}") from exc

        csrf = self._extract_csrf(html)
        form = urlencode({
            "authenticity_token": csrf,
            "user[email]": self.email,
            "user[password]": self.password,
            "user[remember_me]": "1",
            "commit": "Log in",
        }).encode("utf-8")
        request = Request(
            f"{self.login_url}/users/sign_in",
            data=form,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": self.login_url,
                "Referer": f"{self.login_url}/login",
                "User-Agent": self.USER_AGENT,
            },
        )
        try:
            with self._opener.open(request, timeout=self.timeout):
                pass
        except HTTPError as exc:
            if exc.code == 401:
                raise BunproAPIError("Bunpro login failed: invalid email or password") from exc
            raise BunproAPIError(f"Bunpro login failed (HTTP {exc.code})") from exc
        except (URLError, TimeoutError) as exc:
            raise BunproAPIError(f"Could not submit Bunpro login: {exc}") from exc

        for cookie in self._cookie_jar:
            if cookie.name == "frontend_api_token":
                self._token = cookie.value
                return cookie.value
        raise BunproAPIError("Bunpro login succeeded but frontend_api_token was not found")

    def get(self, path: str) -> dict[str, Any]:
        token = self._token or self.login()
        url = f"{self.api_url}/api/frontend/{path.lstrip('/')}"

        for attempt in range(self.max_retries + 1):
            request = Request(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "User-Agent": self.USER_AGENT,
                },
            )
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    if not isinstance(payload, dict):
                        raise BunproAPIError("Bunpro returned a non-object JSON response")
                    return payload
            except HTTPError as exc:
                if exc.code == 401 and attempt == 0:
                    self._token = None
                    token = self.login()
                    continue
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if retryable and attempt < self.max_retries:
                    time.sleep(min(2**attempt, 8))
                    continue
                detail = exc.read().decode("utf-8", errors="replace")
                raise BunproAPIError(
                    f"Bunpro API request failed ({exc.code}) for {url}: {detail}"
                ) from exc
            except (URLError, TimeoutError) as exc:
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 8))
                    continue
                raise BunproAPIError(f"Could not reach Bunpro API: {exc}") from exc

        raise BunproAPIError(f"Bunpro API request failed for {url}")

    def get_user(self) -> dict[str, Any]:
        return self.get("user")

    def get_srs_overview(self) -> dict[str, Any]:
        return self.get("user_stats/srs_level_overview")

    def get_jlpt_progress(self) -> dict[str, Any]:
        return self.get("user_stats/jlpt_progress_mixed")

    def get_srs_level_details(
        self,
        level: str,
        reviewable_type: str,
        *,
        page: int = 1,
    ) -> dict[str, Any]:
        if level not in self.SRS_LEVELS:
            raise ValueError(f"Invalid Bunpro SRS level: {level}")
        if reviewable_type not in {"GrammarPoint", "Vocab"}:
            raise ValueError(f"Invalid Bunpro reviewable type: {reviewable_type}")
        query = urlencode({
            "level": level,
            "reviewable_type": reviewable_type,
            "page": page,
        })
        return self.get(f"user_stats/srs_level_details?{query}")

    @classmethod
    def _extract_csrf(cls, html: str) -> str:
        for pattern in cls._CSRF_PATTERNS:
            match = pattern.search(html)
            if match:
                return match.group(1)
        raise BunproAPIError("CSRF token not found on Bunpro login page")
