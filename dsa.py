from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Sequence, Tuple


def _safe_key(v: Any) -> Tuple[int, Any]:
    if v is None:
        return (1, None)
    return (0, v)


def merge_sort(items: Sequence[dict], key: Callable[[dict], Any], reverse: bool = False) -> List[dict]:
    arr = list(items)
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left = merge_sort(arr[:mid], key=key, reverse=reverse)
    right = merge_sort(arr[mid:], key=key, reverse=reverse)

    merged: List[dict] = []
    i = 0
    j = 0
    while i < len(left) and j < len(right):
        lk = _safe_key(key(left[i]))
        rk = _safe_key(key(right[j]))
        take_left = lk <= rk
        if reverse:
            take_left = not take_left
        if take_left:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1

    if i < len(left):
        merged.extend(left[i:])
    if j < len(right):
        merged.extend(right[j:])
    return merged


def binary_search_range(sorted_items: Sequence[dict], key: Callable[[dict], Any], target: Any) -> Tuple[int, int]:
    def k(i: int) -> Any:
        return key(sorted_items[i])

    lo = 0
    hi = len(sorted_items)
    while lo < hi:
        mid = (lo + hi) // 2
        if k(mid) < target:
            lo = mid + 1
        else:
            hi = mid
    start = lo

    lo = start
    hi = len(sorted_items)
    while lo < hi:
        mid = (lo + hi) // 2
        if k(mid) <= target:
            lo = mid + 1
        else:
            hi = mid
    end = lo
    return (start, end)


@dataclass(frozen=True)
class QueryPlan:
    strategy: str
    sorted_by: str | None
    used_binary_search: bool


def filter_sort_paginate(
    rows: Sequence[dict],
    *,
    search_q: str,
    search_col: str | None,
    filter_col: str | None,
    filter_val: str,
    sort_col: str | None,
    sort_dir: str,
    numeric_cols: set[str] | None = None,
    page: int,
    page_size: int,
) -> Tuple[List[dict], int, QueryPlan]:
    working: List[dict] = list(rows)
    used_binary = False
    sorted_by: str | None = None
    numeric_cols = numeric_cols or set()

    q = (search_q or "").strip()
    fv = (filter_val or "").strip()

    def normalize(v: Any) -> str:
        if v is None:
            return ""
        return str(v)

    def sort_key_for(col: str) -> Callable[[dict], Any]:
        if col in numeric_cols:
            def k(r: dict) -> Any:
                v = r.get(col)
                if v is None or v == "":
                    return None
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return None

            return k
        return lambda r: normalize(r.get(col)).lower()

    if filter_col and fv:
        col = filter_col
        # Exact-match filter uses sort + binary search (DSA)
        working = merge_sort(working, key=lambda r: normalize(r.get(col)))
        sorted_by = col
        start, end = binary_search_range(working, key=lambda r: normalize(r.get(col)), target=fv)
        used_binary = True
        working = working[start:end]

    if q:
        if search_col:
            cols = [search_col]
        else:
            cols = list(working[0].keys()) if working else []
        q_lower = q.lower()
        tmp: List[dict] = []
        for r in working:
            for c in cols:
                if q_lower in normalize(r.get(c)).lower():
                    tmp.append(r)
                    break
        working = tmp

    if sort_col:
        col = sort_col
        reverse = (sort_dir or "asc").lower() == "desc"
        if sorted_by != col:
            working = merge_sort(working, key=sort_key_for(col), reverse=reverse)
            sorted_by = col
        elif reverse:
            working = list(reversed(working))

    total = len(working)
    page = max(1, int(page or 1))
    page_size = max(5, min(200, int(page_size or 25)))
    start_i = (page - 1) * page_size
    end_i = start_i + page_size
    slice_rows = working[start_i:end_i]

    plan = QueryPlan(
        strategy="in-memory",
        sorted_by=sorted_by,
        used_binary_search=used_binary,
    )
    return slice_rows, total, plan
