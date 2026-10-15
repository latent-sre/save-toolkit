"""Private stdio MCP file tools and fixed query replay for bounded Codex trials.

The harness supplies an exact path map. No shell, glob, arbitrary file lookup or
network operation is exposed. This process's allowlist is not an OS sandbox.
"""

from __future__ import annotations

import hashlib
import json
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import Any, cast


def text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def query_text(value: dict[str, Any]) -> str:
    return json.dumps({key: value[key] for key in ("stdout", "stderr", "exit_code")}, sort_keys=True)


class FixtureTools:
    def __init__(self, config: dict[str, Any]) -> None:
        self.paths = {name: Path(path) for name, path in config["readable"].items()}
        self.writable = set(config["writable"])
        self.resolved = {name: path.resolve(strict=name not in self.writable) for name, path in self.paths.items()}
        self.queries = config.get("queries", {})
        self.ledger = Path(config["ledger"])
        self.limit = int(config["max_calls"])
        self.count = 0

    def record(self, value: dict[str, Any]) -> None:
        with self.ledger.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, sort_keys=True) + "\n")
            handle.flush()

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.count += 1
        base = {"id": self.count, "tool": name, "arguments": arguments}
        self.record({**base, "phase": "issued"})
        ok = False
        try:
            if self.count > self.limit:
                raise ValueError("fixture tool call limit reached")
            if name == "query":
                command = arguments.get("command")
                if set(arguments) != {"command"} or not isinstance(command, str) or command not in self.queries:
                    raise ValueError("query is outside the exact synthetic read catalog")
                result = query_text(self.queries[command])
                ok = self.queries[command]["exit_code"] == 0
            else:
                path = arguments.get("path")
                if not isinstance(path, str) or path not in self.paths:
                    raise ValueError("path is outside the exact fixture/guidance allowlist")
                target = self.paths[path]
                if target.is_symlink() or target.resolve(strict=False) != self.resolved[path]:
                    raise ValueError("allowlisted path was redirected")
                if name == "read_file" and set(arguments) == {"path"}:
                    if target.stat().st_size > 131072:
                        raise ValueError("file exceeds the read limit")
                    result = target.read_text(encoding="utf-8")
                elif name == "write_file" and path in self.writable and set(arguments) == {"path", "content"}:
                    content = arguments["content"]
                    if not isinstance(content, str) or len(content.encode("utf-8")) > 131072:
                        raise ValueError("write requires text within the file size limit")
                    target.write_text(content, encoding="utf-8", newline="\n")
                    result = "written sha256=" + text_digest(content)
                else:
                    raise ValueError("tool or write is outside the declared scope")
                ok = True
        except (OSError, UnicodeError, ValueError) as exc:
            result = "fixture tool refused: " + str(exc)
        self.record({**base, "phase": "completed", "ok": ok, "result_sha256": text_digest(result)})
        return {"content": [{"type": "text", "text": result}], "isError": not ok}

    def tools(self) -> list[dict[str, Any]]:
        schema = {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        }
        result = [
            {
                "name": "read_file",
                "description": "Read an exact fixture or guidance path from the supplied catalog.",
                "inputSchema": schema,
            }
        ]
        if self.writable:
            result.append(
                {
                    "name": "write_file",
                    "description": "Write UTF-8 text to an explicitly writable task path. No execution.",
                    "inputSchema": {
                        **schema,
                        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                        "required": ["path", "content"],
                    },
                }
            )
        if self.queries:
            result.append(
                {
                    "name": "query",
                    "description": "Replay one exact synthetic read query. No shell or live cloud call occurs.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"command": {"type": "string", "enum": list(self.queries)}},
                        "required": ["command"],
                        "additionalProperties": False,
                    },
                }
            )
        return result


def main() -> None:
    # -I ignores PYTHONIOENCODING; MCP pipes still carry UTF-8 on Windows.
    cast(TextIOWrapper, sys.stdin).reconfigure(encoding="utf-8", errors="strict")
    cast(TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8", errors="strict")
    server = FixtureTools(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        method = request.get("method")
        params = request.get("params", {})
        response: dict[str, Any] = {"jsonrpc": "2.0", "id": request["id"]}
        if method == "initialize":
            response["result"] = {
                "protocolVersion": params["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "wp10-fixture", "version": "1"},
            }
        elif method == "tools/list":
            response["result"] = {"tools": server.tools()}
        elif method == "tools/call":
            response["result"] = server.call(params.get("name", ""), params.get("arguments", {}))
        elif method == "ping":
            response["result"] = {}
        else:
            response["error"] = {"code": -32601, "message": "unsupported method"}
        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
