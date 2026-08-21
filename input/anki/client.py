from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AnkiConnectError(RuntimeError):
    """Raised when AnkiConnect cannot complete a request."""


class AnkiConnectClient:
    """Small dependency-free client for the local AnkiConnect HTTP API."""

    def __init__(
        self,
        host: str = "http://localhost:8765",
        *,
        version: int = 6,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.host = host.rstrip("/")
        self.version = version
        self.timeout_seconds = timeout_seconds

    def invoke(self, action: str, **params: Any) -> Any:
        payload = json.dumps(
            {"action": action, "version": self.version, "params": params},
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            self.host,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raise AnkiConnectError(
                f"AnkiConnect returned HTTP {exc.code} for {action}."
            ) from exc
        except URLError as exc:
            raise AnkiConnectError(
                "Could not connect to AnkiConnect. Start Anki, confirm the "
                f"AnkiConnect add-on is installed, and verify {self.host}."
            ) from exc
        except TimeoutError as exc:
            raise AnkiConnectError(
                f"AnkiConnect request timed out after {self.timeout_seconds:g} seconds."
            ) from exc

        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AnkiConnectError(
                f"AnkiConnect returned invalid JSON for {action}."
            ) from exc

        if not isinstance(envelope, dict) or "error" not in envelope or "result" not in envelope:
            raise AnkiConnectError(
                f"Unexpected AnkiConnect response shape for {action}."
            )
        if envelope["error"] is not None:
            raise AnkiConnectError(f"AnkiConnect {action} failed: {envelope['error']}")
        return envelope["result"]

    def deck_names(self) -> list[str]:
        result = self.invoke("deckNames")
        if not isinstance(result, list):
            raise AnkiConnectError("deckNames did not return a list.")
        return [str(item) for item in result]

    def find_cards(self, query: str) -> list[int]:
        result = self.invoke("findCards", query=query)
        if not isinstance(result, list):
            raise AnkiConnectError("findCards did not return a list.")
        return [int(item) for item in result]

    def cards_info(self, card_ids: list[int]) -> list[dict[str, Any]]:
        if not card_ids:
            return []
        result = self.invoke("cardsInfo", cards=card_ids)
        if not isinstance(result, list):
            raise AnkiConnectError("cardsInfo did not return a list.")
        return [item for item in result if isinstance(item, dict)]

    def get_reviews_of_cards(self, card_ids: list[int]) -> dict[str, list[Any]]:
        if not card_ids:
            return {}
        result = self.invoke("getReviewsOfCards", cards=card_ids)
        if not isinstance(result, dict):
            raise AnkiConnectError("getReviewsOfCards did not return an object.")
        return {str(key): value for key, value in result.items() if isinstance(value, list)}
