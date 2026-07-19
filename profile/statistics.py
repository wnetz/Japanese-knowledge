from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class BuildStatistics:
    source_counts: dict[str, int] = field(default_factory=dict)
    duplicates_merged: int = 0
    unresolved_reading_count: int = 0
    confidence_scored_count: int = 0
    vocabulary_count: int = 0

    def format(self) -> str:
        lines = ["Vocabulary Profile Build Summary"]
        for source in ("wanikani", "anki"):
            if source in self.source_counts:
                display_name = "WaniKani" if source == "wanikani" else "Anki"
                lines.append(
                    f"  {display_name}: {self.source_counts[source]} vocabulary entries"
                )
        lines.extend(
            [
                f"  Final vocabulary: {self.vocabulary_count}",
                f"  Duplicates merged: {self.duplicates_merged}",
                f"  Confidence scored: {self.confidence_scored_count}",
                f"  Unresolved readings: {self.unresolved_reading_count}",
            ]
        )
        return "\n".join(lines)
