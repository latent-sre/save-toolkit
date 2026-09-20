"""Read-only shell contracts; command strings are classified, never executed."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts/readonly-guard.py"


class CrossPlatformReads(unittest.TestCase):
    def guard(self, command, tool="PowerShell", copilot=False):
        payload = {"tool_name": tool, "tool_input": {"command": command}}
        if not copilot:
            payload["agent_type"] = "save-toolkit:sre-assistant"
        result = subprocess.run(
            [sys.executable, "-I", "-S", str(GUARD), *(["--copilot"] if copilot else [])],
            input=json.dumps(payload), text=True, capture_output=True, timeout=10,
        )
        return result.returncode

    def test_powershell_reads(self):
        for command in (
            "Get-Date -Format o", "Get-Service -Name Spooler", "Get-Process -Name python",
            "Resolve-DnsName example.com", "Test-NetConnection example.com -Port 443",
            "git status --short", "cf app orders", "gcloud run revisions list --project=example",
            "Get-Service | Select-Object -First 5",
        ):
            with self.subTest(command=command):
                self.assertEqual(42, self.guard(command))

    def test_powershell_writes_and_dynamic_code_are_denied(self):
        for command in (
            "Stop-Service Spooler", "Remove-Item file.txt", "git push", "cf restart orders",
            "Get-Date; Remove-Item file.txt", "Get-Date $(Remove-Item file.txt)",
            "& Get-Date", "Get-Service | ForEach-Object { Stop-Service $_ }",
            "Get-Service > out.txt", "Get-Service -OutVariable captured", "Get-Service --% ; whoami",
            "Invoke-Expression 'Get-Date'", "python -c pass", "powershell -Command Get-Date",
            "Get-Content Env:GRAFANA_SA_TOKEN", "Get-Date `n Remove-Item file.txt",
        ):
            with self.subTest(command=command):
                self.assertEqual(43, self.guard(command))

    def test_json_requires_explicit_safe_property_projection(self):
        for command in (
            "Get-Process -Name powershell | ConvertTo-Json -Depth 10",
            "Get-Process | Select-Object -First 1 | ConvertTo-Json",
            "Get-Service | ConvertTo-Json -Depth 3",
            "ConvertTo-Json -Depth 10",
        ):
            for copilot in (False, True):
                with self.subTest(command=command, copilot=copilot):
                    self.assertEqual(43, self.guard(command, copilot=copilot))
        for command in (
            "Get-Process -Name powershell | Select-Object -Property Name,Id,CPU | ConvertTo-Json -Depth 10",
            "Get-Process | Select-Object -Property Name | Select-Object -First 2 | ConvertTo-Json",
            "Get-Service | Select-Object -First 2 | Select-Object -Property Name,Status | ConvertTo-Json",
        ):
            with self.subTest(command=command):
                self.assertEqual(42, self.guard(command))

    @unittest.skipUnless(os.name == "nt", "Native serialization regression requires Windows")
    def test_allowed_process_json_does_not_serialize_environment(self):
        command = "Get-Process -Name powershell | Select-Object -Property Name,Id,CPU | ConvertTo-Json -Depth 10"
        self.assertEqual(42, self.guard(command))
        env = {key: value for key, value in os.environ.items() if key.upper() in {
            "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP",
            "USERPROFILE", "APPDATA", "LOCALAPPDATA",
        }}
        sentinel = "synthetic-credential-regression-value"
        env["GRAFANA_SA_TOKEN"] = sentinel
        result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                                env=env, text=True, capture_output=True, timeout=20)
        self.assertEqual(0, result.returncode)
        self.assertNotIn(sentinel, result.stdout)
        self.assertNotIn(sentinel, result.stderr)
        rows = json.loads(result.stdout)
        if isinstance(rows, dict):
            rows = [rows]
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual({"Name", "Id", "CPU"}, set(row))

    def test_macos_reads(self):
        for command in ("uname -s", "sw_vers -productVersion", "uptime", "df -h"):
            with self.subTest(command=command):
                self.assertEqual(42, self.guard(command, "Bash"))

    def test_copilot_terminal_is_scoped_without_claude_identity(self):
        self.assertEqual(42, self.guard("git status --short", "run_in_terminal", True))
        self.assertEqual(43, self.guard("git push", "run_in_terminal", True))
        self.assertEqual(43, self.guard("python -c pass", "runTerminalCommand", True))
        self.assertEqual(43, self.guard("echo $GRAFANA_SA_TOKEN", "Bash"))

    def test_posix_copilot_launcher_honors_guard_decisions(self):
        shell = shutil.which("sh")
        if shell is None:
            candidate = Path("C:/Program Files/Git/bin/sh.exe")
            shell = str(candidate) if candidate.is_file() else None
        if shell is None:
            self.skipTest("POSIX shell unavailable; installed macOS acceptance remains required")
        # Agent-scoped VS Code hooks do not receive Claude's plugin-root substitution.
        env = dict(os.environ)
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
        for command, denied in (("git status --short", False), ("git push", True)):
            result = subprocess.run(
                [shell, str(ROOT / "scripts/readonly-guard-copilot-hook.sh")],
                input=json.dumps({"tool_name": "run_in_terminal", "tool_input": {"command": command}}),
                env=env, cwd=tempfile.gettempdir(), text=True, capture_output=True, timeout=20,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            if denied:
                self.assertEqual("deny", json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"])
            else:
                self.assertEqual("", result.stdout)

    def test_grafana_curl_get_template(self):
        prefix = ('curl -q --silent --show-error --fail --max-time 20 --max-redirs 0 '
                  '--proto =https --header "Authorization: Bearer $GRAFANA_SA_TOKEN" ')
        good = prefix + '"$GRAFANA_URL/api/health"'
        self.assertEqual(42, self.guard(good, "Bash"))
        windows = good.replace('curl ', 'curl.exe ', 1).replace('$GRAFANA_', '$env:GRAFANA_')
        self.assertEqual(42, self.guard(windows, "PowerShell"))
        for command in (
            good + " --insecure", good + " --location", good + " --output out.json",
            good + " --request DELETE", good.replace("-q ", ""),
            good.replace("/api/health", "/api/admin/provisioning/dashboards/reload"),
            good.replace("$GRAFANA_URL/api/health", "https://example.com/api/health"),
            good.replace("$GRAFANA_SA_TOKEN", "literal-secret"),
        ):
            with self.subTest(command=command):
                self.assertEqual(43, self.guard(command, "Bash"))

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell launcher requires Windows")
    def test_real_powershell_launcher_allows_reads_and_denies_writes(self):
        launcher = ROOT / "scripts/readonly-guard-hook.ps1"
        for command, denied in (
            ("Get-Date -Format o", False), ("Stop-Service Spooler", True),
            ("Get-Process -Name powershell | ConvertTo-Json -Depth 10", True),
            ("Get-Process -Name powershell | Select-Object -Property Name,Id | ConvertTo-Json", False),
        ):
            payload = {"tool_name": "run_in_terminal", "tool_input": {"command": command}}
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(launcher), "-Copilot"],
                input=json.dumps(payload), text=True, capture_output=True, timeout=20,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            if denied:
                self.assertEqual("deny", json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"])
            else:
                self.assertEqual("", result.stdout)

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell launcher requires Windows")
    def test_powershell_launcher_rejects_non_guard_and_empty_deny(self):
        with tempfile.TemporaryDirectory(prefix="SRE guard spaces ") as directory:
            root = Path(directory)
            shutil.copy2(ROOT / "scripts/readonly-guard-hook.ps1", root / "readonly-guard-hook.ps1")
            for code in (0, 43, 44):
                (root / "readonly-guard.py").write_text(f"raise SystemExit({code})\n", encoding="utf-8")
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                     str(root / "readonly-guard-hook.ps1"), "-Copilot"],
                    input='{}', text=True, capture_output=True, timeout=20,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual("deny", json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"])


if __name__ == "__main__":
    unittest.main()
