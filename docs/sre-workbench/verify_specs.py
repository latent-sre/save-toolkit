"""Check planning schemas, fixtures, local links and ID coverage; no product execution."""

from __future__ import annotations

import json
import re
from functools import partial
from pathlib import Path
from urllib.parse import unquote, urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FENCE = re.compile(r"(?ms)^([\x60~]{3})[^\n]*\n.*?^\1[^\n]*$")
# Planning-ID prefix -> (the package document that defines the IDs, how many it defines).
ID_OWNERS = {
    "CAP": ("capabilities.md", 25),
    "REQ": ("product.md", 17),
    "NFR": ("product.md", 12),
    "AC": ("verification.md", 36),
    "WP": ("delivery.md", 16),
    "DEC": ("decisions-and-risks.md", 15),
    "RISK": ("decisions-and-risks.md", 16),
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def contained(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes {root}: {path}")
    return resolved


def anchors(text: str) -> set[str]:
    found: set[str] = set()
    counts: dict[str, int] = {}
    for title in re.findall(r"(?m)^#{1,6} +(.+?)\s*$", FENCE.sub("", text)):
        slug = re.sub(r"[^\w\s-]", "", title.casefold())
        slug = re.sub(r"\s", "-", slug)
        count = counts.get(slug, 0)
        found.add(slug if count == 0 else f"{slug}-{count}")
        counts[slug] = count + 1
    return found


def load_schemas() -> dict[str, dict]:
    """The package schemas by name, each checked against its metaschema."""
    paths = sorted((PACKAGE / "schemas").glob("*.schema.json"))
    schemas = {path.name.removesuffix(".schema.json"): read_json(path) for path in paths}
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    return schemas


def check_fixtures(schemas: dict[str, dict], cases: list[dict]) -> list[str]:
    """Each example is accepted or rejected as the manifest says; valid ones' inputs pass their schema."""
    failures: list[str] = []
    registry = Registry().with_resources([(schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()])
    validator = partial(Draft202012Validator, registry=registry, format_checker=FormatChecker())
    examples = PACKAGE / "examples"

    instance_names = {case["file"] for case in cases}
    actual_names = {p.name for p in examples.glob("*.json")} - {"cases.json"}
    if actual_names != instance_names or len(instance_names) != len(cases):
        failures.append("Example manifest must cover every JSON fixture exactly once")
    for case in cases:
        instance = read_json(contained(examples / case["file"], examples))
        errors = list(validator(schemas[case["schema"]]).iter_errors(instance))
        if bool(errors) == case["valid"]:
            detail = errors[0].message if errors else "unexpectedly accepted"
            failures.append(f"{case['file']}: {detail}")
        if not case["valid"]:
            continue
        input_schemas = []
        if "input_schema" in case:
            input_schemas.append(schemas[case["input_schema"]])
        if "input_manifest" in case:
            input_schemas.append(read_json(contained(examples / case["input_manifest"], examples))["input_schema"])
        for input_schema in input_schemas:
            failures += [f"{case['file']} operation inputs: {error.message}"
                         for error in validator(input_schema).iter_errors(instance["inputs"])]
        if isinstance(instance, dict):
            for key in ("input_schema", "output_schema"):
                if key in instance:
                    Draft202012Validator.check_schema(instance[key])
    return failures


def check_links(documents: list[Path]) -> list[str]:
    """Each local link resolves inside the repository, and each Markdown anchor it names exists."""
    failures: list[str] = []
    for document in documents:
        text = FENCE.sub("", document.read_text(encoding="utf-8"))
        for raw in LINK.findall(text):
            target = urlsplit(raw.strip("<>"))
            if target.scheme or target.netloc:
                continue
            try:
                resolved = contained(document.parent / unquote(target.path), ROOT) if target.path else document
            except ValueError as error:
                failures.append(str(error))
                continue
            if not resolved.exists():
                failures.append(f"{document.relative_to(ROOT)}: missing link {raw}")
            elif (target.fragment and resolved.suffix == ".md"
                  and unquote(target.fragment) not in anchors(resolved.read_text(encoding="utf-8"))):
                failures.append(f"{document.relative_to(ROOT)}: missing anchor {raw}")
    return failures


def check_ids(markdown: list[Path]) -> list[str]:
    """Each owner defines exactly its numbered IDs, and the package cites no others."""
    failures: list[str] = []
    package_text = "\n".join(path.read_text(encoding="utf-8") for path in markdown)
    for prefix, (owner, count) in ID_OWNERS.items():
        expected = {f"{prefix}-{number:02}" for number in range(1, count + 1)}
        pattern = rf"\b{prefix}-\d{{2}}\b"
        owned = set(re.findall(pattern, (PACKAGE / owner).read_text(encoding="utf-8")))
        referenced = set(re.findall(pattern, package_text))
        if owned != expected or not referenced.issubset(expected):
            failures.append(f"{prefix} coverage: missing={sorted(expected-owned)}, unknown={sorted(referenced-expected)}")
    return failures


def main() -> int:
    schemas = load_schemas()
    cases = read_json(PACKAGE / "examples/cases.json")
    markdown = sorted(PACKAGE.rglob("*.md"))
    failures = [
        *check_fixtures(schemas, cases),
        *check_links([*markdown, ROOT / "docs/fleet-roadmap.md"]),
        *check_ids(markdown),
    ]
    if failures:
        print("\n".join(failures))
        return 1
    positive = sum(case["valid"] for case in cases)
    print(f"PASS: {len(schemas)} schemas; {positive} positive and {len(cases)-positive} negative fixtures; "
          f"{len(markdown)} package documents plus roadmap links; all planning IDs covered.")
    print("This checks specification structure, not product behavior or live readiness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
