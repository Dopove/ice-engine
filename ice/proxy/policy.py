# SPDX-License-Identifier: BSL-1.1

from dataclasses import dataclass

@dataclass
class MemoryPolicy:
    retrieval_strategy: str = "semantic"
    relevance_threshold: float = 0.85
    max_context_window: int = 8192

    @classmethod
    def default(cls):
        return cls()
