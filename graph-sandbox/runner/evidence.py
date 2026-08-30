from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path

from runner.validation import validate_atomic_id


class EvidenceExporter:
    def __init__(self, evidence_root: Path, run_id: str) -> None:
        validate_atomic_id(run_id, "run_id")
        self.evidence_root = evidence_root.resolve()
        self.run_dir = self.evidence_root / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def write_json(self, relative_path: str, value: object) -> Path:
        payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
        return self._atomic_write(relative_path, payload.encode("utf-8"))

    def write_jsonl(
        self,
        relative_path: str,
        records: Iterable[Mapping[str, object]],
    ) -> Path:
        lines = [json.dumps(dict(record), sort_keys=True, separators=(",", ":")) for record in records]
        payload = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
        return self._atomic_write(relative_path, payload)

    def write_checksums(self) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        for path in sorted(self.run_dir.rglob("*")):
            if not path.is_file() or path.name == "checksums.sha256" or path.name.endswith(".tmp"):
                continue
            relative = path.relative_to(self.run_dir).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            entries.append({"sha256": digest, "path": relative})
        text = "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries)
        self._atomic_write("checksums.sha256", text.encode("ascii"))
        return entries

    def _atomic_write(self, relative_path: str, payload: bytes) -> Path:
        target = self._resolve_relative(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(payload)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, target)
            self._sync_directory(target.parent)
            return target
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def _resolve_relative(self, relative_path: str) -> Path:
        relative = Path(relative_path)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ValueError("relative evidence path must remain inside the run directory")
        candidate = (self.run_dir / relative).resolve()
        if not candidate.is_relative_to(self.run_dir.resolve()):
            raise ValueError("relative evidence path must remain inside the run directory")
        return candidate

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
