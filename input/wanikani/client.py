from __future__ import annotations

import json
import time
from collections.abc import Iterator, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class WaniKaniAPIError(RuntimeError):
    """Raised when the WaniKani API cannot be read successfully."""


class WaniKaniClient:
    BASE_URL = "https://api.wanikani.com/v2"
    REVISION = "20170710"

    def __init__(
        self,
        api_token: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 4,
        user_agent: str = "William-Japanese-Knowledge-Engine/2",
    ) -> None:
        token = api_token.strip()
        if not token:
            raise ValueError("A WaniKani API token is required")

        self.api_token = token
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent

    def get(self, endpoint_or_url: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        url = self._build_url(endpoint_or_url, params)
        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Wanikani-Revision": self.REVISION,
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )

        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    if not isinstance(payload, dict):
                        raise WaniKaniAPIError("WaniKani returned a non-object JSON response")
                    return payload
            except HTTPError as exc:
                retry_after = exc.headers.get("Retry-After")
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if retryable and attempt < self.max_retries:
                    delay = float(retry_after) if retry_after else min(2**attempt, 16)
                    time.sleep(delay)
                    continue
                detail = exc.read().decode("utf-8", errors="replace")
                raise WaniKaniAPIError(
                    f"WaniKani API request failed ({exc.code}) for {url}: {detail}"
                ) from exc
            except (URLError, TimeoutError) as exc:
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 16))
                    continue
                raise WaniKaniAPIError(f"Could not reach WaniKani API: {exc}") from exc

        raise WaniKaniAPIError(f"WaniKani API request failed for {url}")

    def iter_collection(
        self,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        next_url: str | None = endpoint
        next_params = params

        while next_url:
            payload = self.get(next_url, next_params)
            data = payload.get("data", [])
            if not isinstance(data, list):
                raise WaniKaniAPIError(f"Collection endpoint {endpoint} returned invalid data")

            for item in data:
                if isinstance(item, dict):
                    yield item

            pages = payload.get("pages") or {}
            next_url = pages.get("next_url")
            next_params = None

    def _build_url(
        self,
        endpoint_or_url: str,
        params: Mapping[str, Any] | None,
    ) -> str:
        if endpoint_or_url.startswith("http://") or endpoint_or_url.startswith("https://"):
            url = endpoint_or_url
        else:
            url = f"{self.BASE_URL}/{endpoint_or_url.lstrip('/')}"

        if not params:
            return url

        cleaned: dict[str, Any] = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, (list, tuple, set)):
                cleaned[key] = ",".join(str(item) for item in value)
            else:
                cleaned[key] = value

        query = urlencode(cleaned)
        return f"{url}{'&' if '?' in url else '?'}{query}" if query else url
