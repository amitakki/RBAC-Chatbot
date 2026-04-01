"""Conversation memory data models (RC-35)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ConversationTurn:
    role: str       # "user" or "assistant"
    content: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "ConversationTurn":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", ""),
        )
