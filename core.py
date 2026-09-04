#!/usr/bin/env python

import os


RELS_ROOT = os.getenv("RELS_ROOT")

CID_BYTES = 32
RECORD_BYTES = CID_BYTES * 2

_HANDLES = {}


def _get_handle(rels_root: str):
    handle = _HANDLES.get(rels_root)

    if handle is None:
        os.makedirs(rels_root, exist_ok=True)
        path = os.path.join(rels_root, "today.bin")
        handle = open(path, "ab")
        _HANDLES[rels_root] = handle

    return handle


def _cid_bytes(cid: str) -> bytes:
    value = bytes.fromhex(cid)

    if len(value) != CID_BYTES:
        raise ValueError("invalid content ID")

    return value


def put(a: str, b: str, rels_root: str = RELS_ROOT) -> None:
    """Append the relationship a → b to today's relation file."""
    if rels_root is None:
        raise ValueError("rels_root is not configured")

    handle = _get_handle(rels_root)
    handle.write(_cid_bytes(a))
    handle.write(_cid_bytes(b))


def get(a: str, rels_root: str = RELS_ROOT) -> str | None:
    """Return b for a, or None if no relationship exists."""
    if rels_root is None:
        raise ValueError("rels_root is not configured")

    target = _cid_bytes(a)
    path = os.path.join(rels_root, "relations.bin")

    if not os.path.exists(path):
        return None

    with open(path, "rb") as handle:
        left = 0
        right = os.path.getsize(path) // RECORD_BYTES

        while left < right:
            middle = (left + right) // 2
            handle.seek(middle * RECORD_BYTES)

            record = handle.read(RECORD_BYTES)
            record_a = record[:CID_BYTES]

            if record_a < target:
                left = middle + 1
            elif record_a > target:
                right = middle
            else:
                return record[CID_BYTES:].hex()

    return None


def members(b: str, rels_root: str = RELS_ROOT):
    """Yield every a related to b."""
    if rels_root is None:
        raise ValueError("rels_root is not configured")

    target = _cid_bytes(b)
    path = os.path.join(rels_root, "relations-by-b.bin")

    if not os.path.exists(path):
        return

    with open(path, "rb") as handle:
        left = 0
        right = os.path.getsize(path) // RECORD_BYTES

        # Find the first record whose b >= target.
        while left < right:
            middle = (left + right) // 2
            handle.seek(middle * RECORD_BYTES)

            record = handle.read(RECORD_BYTES)
            record_b = record[:CID_BYTES]

            if record_b < target:
                left = middle + 1
            else:
                right = middle

        # Scan the contiguous matching records.
        handle.seek(left * RECORD_BYTES)

        while True:
            record = handle.read(RECORD_BYTES)

            if len(record) < RECORD_BYTES:
                return

            record_b = record[:CID_BYTES]

            if record_b != target:
                return

            yield record[CID_BYTES:].hex()

def _sort(rels_root: str = RELS_ROOT) -> None:
    """Sort today's records into forward and reverse indexes."""
    if rels_root is None:
        raise ValueError("rels_root is not configured")

    handle = _HANDLES.pop(rels_root, None)
    if handle is not None:
        handle.close()

    path = os.path.join(rels_root, "today.bin")
    by_a_path = os.path.join(rels_root, "today-by-a.bin")
    by_b_path = os.path.join(rels_root, "today-by-b.bin")

    if not os.path.exists(path):
        return

    with open(path, "rb") as handle:
        data = handle.read()

    if len(data) % RECORD_BYTES:
        raise ValueError("corrupt relationship file")

    records = [
        data[i:i + RECORD_BYTES]
        for i in range(0, len(data), RECORD_BYTES)
    ]

    records.sort()

    with open(by_a_path, "wb") as handle:
        handle.writelines(records)

    records.sort(key=lambda record: record[CID_BYTES:])
    
    with open(by_b_path, "wb") as handle:
        handle.writelines(records)


def _merge_files(
    existing_path: str,
    today_path: str,
    merged_path: str,
) -> None:
    """Merge two sorted relationship files, removing duplicates."""

    with open(existing_path, "rb") as existing, \
         open(today_path, "rb") as today, \
         open(merged_path, "wb") as merged:

        a = existing.read(RECORD_BYTES)
        b = today.read(RECORD_BYTES)

        while a and b:
            if a < b:
                merged.write(a)
                a = existing.read(RECORD_BYTES)

            elif b < a:
                merged.write(b)
                b = today.read(RECORD_BYTES)

            else:
                # Same relationship in both files.
                merged.write(a)
                a = existing.read(RECORD_BYTES)
                b = today.read(RECORD_BYTES)

        while a:
            merged.write(a)
            a = existing.read(RECORD_BYTES)

        while b:
            merged.write(b)
            b = today.read(RECORD_BYTES)


def _merge(rels_root: str = RELS_ROOT) -> None:
    """Merge today's sorted indexes into the persistent indexes."""
    if rels_root is None:
        raise ValueError("rels_root is not configured")

    today_by_a = os.path.join(rels_root, "today-by-a.bin")
    today_by_b = os.path.join(rels_root, "today-by-b.bin")

    relations = os.path.join(rels_root, "relations.bin")
    relations_by_b = os.path.join(rels_root, "relations-by-b.bin")

    new_relations = os.path.join(rels_root, "relations.new.bin")
    new_relations_by_b = os.path.join(
        rels_root,
        "relations-by-b.new.bin",
    )

    if os.path.exists(today_by_a):
        if os.path.exists(relations):
            _merge_files(
                relations,
                today_by_a,
                new_relations,
            )
            os.replace(new_relations, relations)
        else:
            os.replace(today_by_a, relations)

    if os.path.exists(today_by_b):
        if os.path.exists(relations_by_b):
            _merge_files(
                relations_by_b,
                today_by_b,
                new_relations_by_b,
            )
            os.replace(new_relations_by_b, relations_by_b)
        else:
            os.replace(today_by_b, relations_by_b)

    today_path = os.path.join(rels_root, "today.bin")

    if os.path.exists(today_path):
        os.unlink(today_path)


def build(rels_root: str = RELS_ROOT) -> None:
    """Build the queryable relationship store from today's records."""
    if rels_root is None:
        raise ValueError("rels_root is not configured")

    close(rels_root)
    _sort(rels_root)
    _merge(rels_root)


def walk(rels_root: str = RELS_ROOT):
    """Yield every A CID in sorted order."""
    if rels_root is None:
        raise ValueError("rels_root is not configured")

    path = os.path.join(rels_root, "relations.bin")

    if not os.path.exists(path):
        return

    with open(path, "rb") as handle:
        while record := handle.read(RECORD_BYTES):
            if len(record) != RECORD_BYTES:
                raise ValueError("corrupt relationship file")

            yield record[:CID_BYTES].hex()


def close(rels_root: str | None = None) -> None:
    """Flush and close open relationship files."""
    if rels_root is not None:
        handle = _HANDLES.pop(rels_root, None)

        if handle is not None:
            handle.close()

        return

    for handle in _HANDLES.values():
        handle.close()

    _HANDLES.clear()
