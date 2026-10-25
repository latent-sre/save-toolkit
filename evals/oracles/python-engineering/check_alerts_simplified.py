"""Outcome checks for build-python-engineering-remove-abstraction.

`alerts.send_alert(transport, recipient, subject, body, cc=None)` must send the same message as
before, add a Cc header only when cc is given, and keep app.py working unchanged. Structure: the
factory/provider/manager/base-class stack is gone (at most two classes remain in alerts/, none of
them a factory, provider, manager or abstract base).
"""

import ast
import sys
from pathlib import Path

from oracle_protocol import candidate_call

sys.path.insert(0, str(Path.cwd()))
import alerts
import app


class Transport:
    def __init__(self):
        self.sent = []

    def send_message(self, message):
        self.sent.append(message)


transport = Transport()
candidate_call(alerts.send_alert, transport, "ops@example.com", "Disk full", "db-3 at 97%")
(message,) = transport.sent
assert message["To"] == "ops@example.com" and message["Subject"] == "Disk full", "headers changed"
assert message["From"] == "alerts@example.com", "sender changed"
assert message.get_content().strip() == "db-3 at 97%", "body changed"
assert message["Cc"] is None, "a Cc header appears without cc"

transport = Transport()
candidate_call(alerts.send_alert, transport, "ops@example.com", "Disk full", "db-3", cc=["a@example.com", "b@example.com"])
(message,) = transport.sent
cc = [address.strip() for address in str(message["Cc"]).split(",")]
assert cc == ["a@example.com", "b@example.com"], f"Cc header is {message['Cc']!r}"
assert message["To"] == "ops@example.com", "cc changed the recipient"

transport = Transport()
candidate_call(app.page_on_call, transport, "replica lag")
assert len(transport.sent) == 1 and transport.sent[0]["Subject"] == "ALERT: replica lag", "app.py no longer works"

classes = []
abstract = False
for source in Path("alerts").rglob("*.py"):
    tree = ast.parse(source.read_text(encoding="utf-8"))
    classes += [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = {alias.name for alias in node.names} | {getattr(node, "module", None) or ""}
            abstract |= bool(names & {"abc", "ABC", "abstractmethod"})
layered = [name for name in classes if any(word in name for word in ("Factory", "Provider", "Manager"))]
assert not layered, f"indirection layers remain: {layered}"
assert not abstract, "an abstract base remains for a single implementation"
assert len(classes) <= 2, f"{len(classes)} classes remain in alerts/: {classes}"
print("alerts simplified: PASS")
