from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class FusedResult(Generic[T]):
    item: T
    score: float


def reciprocal_rank_fusion(
    ranked_results: Sequence[Sequence[T]],
    key: Callable[[T], Hashable],
    k: int = 60,
) -> list[FusedResult[T]]:
    scores: dict[Hashable, float] = {}
    first_seen: dict[Hashable, int] = {}
    best_rank: dict[Hashable, int] = {}
    items: dict[Hashable, T] = {}
    seen_order = 0

    for results in ranked_results:
        for rank, item in enumerate(results, start=1):
            item_key = key(item)
            if item_key not in items:
                items[item_key] = item
                first_seen[item_key] = seen_order
                seen_order += 1
            scores[item_key] = scores.get(item_key, 0.0) + 1 / (k + rank)
            best_rank[item_key] = min(best_rank.get(item_key, rank), rank)

    sorted_keys = sorted(
        scores,
        key=lambda item_key: (-scores[item_key], best_rank[item_key], first_seen[item_key]),
    )
    return [
        FusedResult(item=items[item_key], score=scores[item_key])
        for item_key in sorted_keys
    ]
