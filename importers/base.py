from __future__ import annotations

from typing import Any, Protocol


class Importer(Protocol):
    source_name: str

    def import_data(self) -> dict[str, Any]: ...
