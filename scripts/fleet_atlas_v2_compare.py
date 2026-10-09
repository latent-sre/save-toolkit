"""Exact observable comparison for separately verified v1/v2 compatibility snapshots.

This compares evidence; it neither validates an atlas nor approves an expected delta.
Every exception names one exact JSON pointer and both values. No ignore patterns.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path):
    def nonfinite(value):
        raise ValueError(f"nonfinite JSON value: {value}")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object,
                      parse_constant=nonfinite)


def _pointer(parent: str, key: str) -> str:
    return parent + "/" + key.replace("~", "~0").replace("/", "~1")


def _equal(left, right) -> bool:
    return type(left) is type(right) and (
        left.keys() == right.keys() and all(_equal(left[k], right[k]) for k in left)
        if isinstance(left, dict) and isinstance(right, dict) else
        len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right, strict=True))
        if isinstance(left, list) and isinstance(right, list) else left == right)


def differences(before, after, path="") -> list[dict]:
    """Return all leaf changes; missing values are distinct from JSON null."""
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(before.keys() | after.keys()):
            location = _pointer(path, key)
            if key not in before or key not in after:
                result.append({"path": location,
                               "before": {"present": key in before, **({"value": before[key]} if key in before else {})},
                               "after": {"present": key in after, **({"value": after[key]} if key in after else {})}})
            else:
                result.extend(differences(before[key], after[key], location))
        return result
    if _equal(before, after):
        return []
    return [{"path": path, "before": {"present": True, "value": before},
             "after": {"present": True, "value": after}}]


def normalize(snapshot: dict) -> dict:
    """Only make entity ordering irrelevant; preserve every recorded field."""
    if not isinstance(snapshot, dict):
        raise ValueError("compatibility snapshot must be an object")
    result = dict(snapshot)
    for key in ("nodes", "edges"):
        rows = snapshot.get(key)
        if not isinstance(rows, list):
            raise ValueError(f"compatibility snapshot requires {key} array")
        indexed = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
                raise ValueError(f"{key} row requires a nonempty id")
            if row["id"] in indexed:
                raise ValueError(f"duplicate {key} identity: {row['id']}")
            indexed[row["id"]] = row
        result[key] = indexed
    return result


def compare(before: dict, after: dict, expected: list[dict]) -> dict:
    actual = differences(normalize(before), normalize(after))
    if not isinstance(expected, list):
        raise ValueError("expected deltas must be an array")
    names, paths = set(), set()
    allowed = {}
    for entry in expected:
        if (not isinstance(entry, dict) or set(entry) != {"name", "path", "before", "after"}
                or not isinstance(entry["name"], str) or not entry["name"].strip()
                or not isinstance(entry["path"], str)):
            raise ValueError("each expected delta requires name, path, before and after")
        if entry["name"] in names or entry["path"] in paths:
            raise ValueError("expected delta names and paths must be unique")
        for side in ("before", "after"):
            value = entry[side]
            if (not isinstance(value, dict) or type(value.get("present")) is not bool
                    or set(value) != ({"present", "value"} if value["present"] else {"present"})):
                raise ValueError("delta value must distinguish absence from JSON null")
        names.add(entry["name"])
        paths.add(entry["path"])
        allowed[entry["path"]] = entry
    matched, unexpected = [], []
    for delta in actual:
        rule = allowed.get(delta["path"])
        if rule and _equal(delta, {k: v for k, v in rule.items() if k != "name"}):
            matched.append(rule["name"])
        else:
            unexpected.append(delta)
    unused = sorted(names - set(matched))
    return {"outcome": "MATCH" if not unexpected and not unused else "DIFFERENT",
            "matched_expected_deltas": sorted(matched), "unexpected_deltas": unexpected,
            "unused_expected_deltas": unused,
            "scope": "observable comparison only; atlas verification and owner acceptance are separate"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--expected-deltas", type=Path)
    args = parser.parse_args(argv)
    try:
        result = compare(read_json(args.baseline), read_json(args.candidate),
                         read_json(args.expected_deltas) if args.expected_deltas else [])
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"outcome": "INVALID", "reason": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return 0 if result["outcome"] == "MATCH" else 1


if __name__ == "__main__":
    raise SystemExit(main())
