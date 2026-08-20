#!/usr/bin/env python3
"""Run one isolated, sanitized Codex/Terra ROUTE-001 trial.

Raw prompts, model output, stderr, hook payloads, runtime identifiers, credentials, and temporary
paths exist only inside this function's process and disposable directory.  Callers may persist only
``TrialResult.as_dict()``.  A setup, auth, timeout, output-limit, parser, or evidence failure is an
instrument ``INCONCLUSIVE`` result, never a routing PASS/FAIL.
"""
from __future__ import annotations

import dataclasses
import contextlib
import ctypes
import functools
import hashlib
import json
import ntpath
import os
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import codex_harness
import codex_hook_recorder
import codex_model_catalog
import codex_routing_grade
import codex_runtime
import codex_snapshot
import run_codex_routing


MAX_AUTH_BYTES = 4 * 1024 * 1024
MAX_CODEX_EXECUTABLE_BYTES = 512 * 1024 * 1024
MAX_PROCESS_OUTPUT_BYTES = 16 * 1024 * 1024
PROBE_TIMEOUT_SECONDS = 30
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_SE_FILE_OBJECT = 1
_OWNER_SECURITY_INFORMATION = 0x00000001
_DACL_SECURITY_INFORMATION = 0x00000004
_PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000
_SE_DACL_PRESENT = 0x0004
_SE_DACL_PROTECTED = 0x1000
_SDDL_REVISION_1 = 1
_DRIVE_FIXED = 3
_ACCESS_ALLOWED_ACE_TYPE = 0
_OBJECT_INHERIT_ACE = 0x01
_CONTAINER_INHERIT_ACE = 0x02
_INHERITED_ACE = 0x10
_FILE_ALL_ACCESS = 0x001F01FF
_ACL_SIZE_INFORMATION_CLASS = 2
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EVALUATOR_FILES = (
    "codex_harness.py",
    "codex_hook_recorder.py",
    "codex_model_catalog.py",
    "codex_routing_grade.py",
    "codex_snapshot.py",
    "codex_trial.py",
    "graders.py",
    "run_codex_routing.py",
)
HOOK_BUNDLE_FILES = ("codex_harness.py", "codex_hook_recorder.py")


class TrialContractError(ValueError):
    """The requested trial is outside the fixed ROUTE-001 campaign contract."""


class InstrumentError(RuntimeError):
    """A trusted executor boundary failed before a measurement could be made."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class CredentialEchoError(RuntimeError):
    """Trial output contains an exact sensitive value from the transient auth copy."""


@dataclass(frozen=True)
class AuthGuard:
    """Transient exact-string guard; sensitive values are excluded from repr and evidence."""

    sensitive_values: tuple[str, ...] = dataclasses.field(repr=False)

    def reject_output(self, text: str) -> None:
        if not isinstance(text, str):
            raise TypeError("auth output scan requires text")
        if any(value in text for value in self.sensitive_values):
            raise CredentialEchoError("trial output echoed an auth value")

    def reject_value(self, value: object) -> None:
        """Scan decoded JSON-compatible values, including keys and escaped strings."""

        pending = [value]
        seen: set[int] = set()
        while pending:
            child = pending.pop()
            if isinstance(child, str):
                self.reject_output(child)
                continue
            if isinstance(child, Mapping):
                identity = id(child)
                if identity in seen:
                    continue
                seen.add(identity)
                pending.extend(child.keys())
                pending.extend(child.values())
                continue
            if isinstance(child, Sequence) and not isinstance(child, (bytes, bytearray)):
                identity = id(child)
                if identity in seen:
                    continue
                seen.add(identity)
                pending.extend(child)

    def reject_jsonl(self, text: str) -> None:
        """Decode each valid JSONL record so JSON escapes cannot hide exact auth values."""

        self.reject_output(text)
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line, object_pairs_hook=lambda pairs: pairs)
            except json.JSONDecodeError:
                continue
            self.reject_value(value)

    def merged(self, other: "AuthGuard") -> "AuthGuard":
        if not isinstance(other, AuthGuard):
            raise TypeError("auth guards can only merge with auth guards")
        return AuthGuard(tuple(sorted(set(self.sensitive_values) | set(other.sensitive_values))))


@dataclass(frozen=True)
class TrialContract:
    scenario_id: str
    cohort: str
    revision: str
    trial: int
    scenario_sha256: str
    prompt_sha256: str
    manifest_sha256: str
    prompt: str = dataclasses.field(repr=False)
    enable_multi_agent: bool = False


@dataclass(frozen=True)
class CodexProbe:
    cli_version: str
    executable_sha256: str
    bundled_catalog: bytes = dataclasses.field(repr=False)


@dataclass(frozen=True)
class WindowsVolumeFacts:
    """In-process Win32 facts that bind a private root to direct local NTFS storage."""

    drive_type: int
    filesystem: str
    dos_device: str
    volume_root: str


@dataclass(frozen=True)
class HookBundleReceipt:
    """Trusted copied-hook facts; the transient recorder path is never serialized."""

    file_count: int
    source_tree_sha256: str
    staged_tree_sha256: str
    recorder_path: Path = dataclasses.field(repr=False)

    def persistable_facts(self) -> dict[str, object]:
        return {
            "file_count": self.file_count,
            "source_tree_sha256": self.source_tree_sha256,
            "staged_tree_sha256": self.staged_tree_sha256,
        }


@dataclass(frozen=True)
class ProcessCapture:
    stdout: str = dataclasses.field(repr=False)
    stderr: str = dataclasses.field(repr=False)
    returncode: int
    duration_ms: int
    timed_out: bool
    output_limited: bool


@dataclass(frozen=True)
class TrialResult:
    scenario_id: str
    cohort: str
    revision: str
    trial: int
    state: codex_routing_grade.VerdictState
    reason_codes: tuple[str, ...]
    manifest_sha256: str
    scenario_sha256: str
    prompt_sha256: str
    exact_revision: bool
    tool_policy: str
    runtime_facts: dict[str, object] | None = None
    trace_facts: dict[str, object] | None = None
    hook_facts: dict[str, object] | None = None
    verdict_facts: dict[str, object] | None = None

    def as_dict(self) -> dict[str, object]:
        """Return the only trial representation suitable for persistence."""

        authority = run_codex_routing.authority_facts(
            {}, exact_revision=self.exact_revision
        )
        codex_cli_version = codex_harness.CODEX_CLI_VERSION
        if self.runtime_facts is not None:
            observed_version = self.runtime_facts.get("codex_cli_version")
            if isinstance(observed_version, str) and observed_version:
                codex_cli_version = observed_version
        return {
            "schema_version": 1,
            "scenario": {
                "id": self.scenario_id,
                "cohort": self.cohort,
                "revision": self.revision,
                "trial": self.trial,
                "manifest_sha256": self.manifest_sha256,
                "scenario_sha256": self.scenario_sha256,
                "prompt_sha256": self.prompt_sha256,
            },
            "configuration": {
                "provider": "openai-codex",
                "codex_cli_version": codex_cli_version,
                "model": codex_harness.MODEL,
                "reasoning_effort": codex_harness.REASONING_EFFORT,
                "sandbox": codex_harness.SANDBOX_MODE,
                "approval_policy": codex_harness.APPROVAL_POLICY,
                "timeout_s": codex_harness.TIMEOUT_SECONDS,
                "tool_policy": self.tool_policy,
            },
            "state": self.state.value,
            "reason_codes": list(self.reason_codes),
            "runtime": self.runtime_facts,
            "trace": self.trace_facts,
            "hooks": self.hook_facts,
            "verdict": self.verdict_facts,
            "authority": authority,
        }


CommandRunner = Callable[..., subprocess.CompletedProcess[bytes]]
ProcessRunner = Callable[..., ProcessCapture]


def _is_reparse(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return path.is_symlink() or bool(
        getattr(metadata, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT
    )


def _windows_error(message: str, code: int | None = None) -> InstrumentError:
    error = ctypes.WinError(code if code is not None else ctypes.get_last_error())
    return InstrumentError("private-permissions-failed", f"{message}: {error}")


def _windows_volume_error(message: str, code: int | None = None) -> InstrumentError:
    error = ctypes.WinError(code if code is not None else ctypes.get_last_error())
    return InstrumentError("unsafe-temp-boundary", f"{message}: {error}")


def _windows_volume_facts(path: str, drive: str) -> WindowsVolumeFacts:
    """Read drive type, filesystem, volume root, and DOS-device target in-process."""

    if os.name != "nt":
        raise InstrumentError(
            "unsafe-temp-boundary", "Windows volume lookup is unavailable"
        )
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetVolumePathNameW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.DWORD,
    )
    kernel32.GetVolumePathNameW.restype = wintypes.BOOL
    kernel32.GetDriveTypeW.argtypes = (wintypes.LPCWSTR,)
    kernel32.GetDriveTypeW.restype = wintypes.UINT
    kernel32.GetVolumeInformationW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPWSTR,
        wintypes.DWORD,
    )
    kernel32.GetVolumeInformationW.restype = wintypes.BOOL
    kernel32.QueryDosDeviceW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.DWORD,
    )
    kernel32.QueryDosDeviceW.restype = wintypes.DWORD

    volume_root_buffer = ctypes.create_unicode_buffer(32768)
    if not kernel32.GetVolumePathNameW(
        path, volume_root_buffer, len(volume_root_buffer)
    ):
        raise _windows_volume_error("private root volume could not be resolved")
    volume_root = volume_root_buffer.value
    drive_type = int(kernel32.GetDriveTypeW(volume_root))

    serial = wintypes.DWORD()
    maximum_component = wintypes.DWORD()
    flags = wintypes.DWORD()
    filesystem_buffer = ctypes.create_unicode_buffer(256)
    if not kernel32.GetVolumeInformationW(
        volume_root,
        None,
        0,
        ctypes.byref(serial),
        ctypes.byref(maximum_component),
        ctypes.byref(flags),
        filesystem_buffer,
        len(filesystem_buffer),
    ):
        raise _windows_volume_error("private root filesystem could not be read")

    device_buffer = ctypes.create_unicode_buffer(32768)
    length = int(kernel32.QueryDosDeviceW(drive, device_buffer, len(device_buffer)))
    if length == 0:
        raise _windows_volume_error("private root drive mapping could not be read")
    targets = tuple(
        target
        for target in "".join(device_buffer[:length]).split("\0")
        if target
    )
    if len(targets) != 1:
        raise InstrumentError(
            "unsafe-temp-boundary", "private root drive mapping is ambiguous"
        )
    return WindowsVolumeFacts(
        drive_type=drive_type,
        filesystem=filesystem_buffer.value,
        dos_device=targets[0],
        volume_root=volume_root,
    )


def _validate_windows_private_root_locality(
    path: str,
    *,
    volume_probe: Callable[[str, str], WindowsVolumeFacts] = _windows_volume_facts,
) -> None:
    """Require a direct drive-letter path on one local fixed NTFS volume."""

    value = os.fspath(path)
    drive, tail = ntpath.splitdrive(value)
    if (
        value.startswith(("\\\\", "//"))
        or not re.fullmatch(r"[A-Za-z]:", drive)
        or not ntpath.isabs(value)
        or not tail.startswith(("\\", "/"))
    ):
        raise InstrumentError(
            "unsafe-temp-boundary", "private root must use a local fixed drive"
        )
    facts = volume_probe(value, drive.upper())
    if facts.drive_type != _DRIVE_FIXED:
        raise InstrumentError(
            "unsafe-temp-boundary", "private root must use local fixed storage"
        )
    if facts.filesystem.casefold() != "ntfs":
        raise InstrumentError("unsafe-temp-boundary", "private root must use NTFS")
    expected_root = f"{drive.upper()}\\"
    if ntpath.normcase(ntpath.normpath(facts.volume_root)) != ntpath.normcase(
        ntpath.normpath(expected_root)
    ):
        raise InstrumentError(
            "unsafe-temp-boundary", "private root must use a direct drive volume"
        )
    if re.fullmatch(
        r"\\Device\\HarddiskVolume[0-9]+", facts.dos_device, re.IGNORECASE
    ) is None:
        raise InstrumentError(
            "unsafe-temp-boundary", "private root drive is substituted or mapped"
        )


def _validate_private_root_locality(path: Path) -> None:
    """Apply the platform storage contract to the exact externally supplied root."""

    if os.name == "nt":
        _validate_windows_private_root_locality(os.fspath(path))


@functools.lru_cache(maxsize=1)
def _windows_current_sid() -> str:
    """Return the current process-user SID without launching a helper process."""

    if os.name != "nt":
        raise InstrumentError(
            "private-permissions-failed", "Windows SID lookup is unavailable"
        )
    from ctypes import wintypes

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    token = wintypes.HANDLE()
    advapi32.OpenProcessToken.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    )
    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.GetTokenInformation.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    advapi32.GetTokenInformation.restype = wintypes.BOOL
    advapi32.ConvertSidToStringSidW.argtypes = (
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.LPVOID),
    )
    advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = (wintypes.HLOCAL,)
    kernel32.LocalFree.restype = wintypes.HLOCAL

    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
        raise _windows_error("current process token could not be opened")
    try:
        required = wintypes.DWORD()
        advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(required))
        if ctypes.get_last_error() != 122 or required.value == 0:
            raise _windows_error("current process token SID size could not be read")
        buffer = ctypes.create_string_buffer(required.value)
        if not advapi32.GetTokenInformation(
            token, 1, buffer, required, ctypes.byref(required)
        ):
            raise _windows_error("current process token SID could not be read")
        sid_pointer = ctypes.cast(buffer, ctypes.POINTER(wintypes.LPVOID)).contents
        sid_text_pointer = wintypes.LPVOID()
        if not advapi32.ConvertSidToStringSidW(
            sid_pointer, ctypes.byref(sid_text_pointer)
        ):
            raise _windows_error("current process token SID could not be rendered")
        try:
            sid = ctypes.wstring_at(sid_text_pointer)
        finally:
            kernel32.LocalFree(sid_text_pointer)
    finally:
        kernel32.CloseHandle(token)
    if not re.fullmatch(r"S-\d+(?:-\d+)+", sid):
        raise InstrumentError(
            "private-permissions-failed", "current process SID has an invalid shape"
        )
    return sid


def _windows_private_sddl(*, directory: bool) -> str:
    sid = _windows_current_sid()
    flags = "OICI" if directory else ""
    return f"O:{sid}D:P(A;{flags};FA;;;{sid})"


def _windows_acl_shape_is_private(
    *,
    dacl_present: bool,
    protected: bool,
    owner_matches: bool,
    ace_count: int,
    ace_type: int,
    ace_flags: int,
    access_mask: int,
    trustee_matches: bool,
    ace_size_matches: bool,
    directory: bool,
) -> bool:
    """Validate exact access semantics independently of DACL serialization metadata."""

    expected_flags = _OBJECT_INHERIT_ACE | _CONTAINER_INHERIT_ACE if directory else 0
    return (
        dacl_present
        and protected
        and owner_matches
        and ace_count == 1
        and ace_type == _ACCESS_ALLOWED_ACE_TYPE
        and (ace_flags & ~_INHERITED_ACE) == expected_flags
        and access_mask == _FILE_ALL_ACCESS
        and trustee_matches
        and ace_size_matches
    )


def _windows_path_acl_is_private(path: Path, *, directory: bool) -> bool:
    """Verify one current-user-only protected DACL entirely in-process."""

    from ctypes import wintypes

    class AceHeader(ctypes.Structure):
        _fields_ = (
            ("ace_type", ctypes.c_ubyte),
            ("ace_flags", ctypes.c_ubyte),
            ("ace_size", wintypes.WORD),
        )

    class AccessAllowedAce(ctypes.Structure):
        _fields_ = (
            ("header", AceHeader),
            ("mask", wintypes.DWORD),
            ("sid_start", wintypes.DWORD),
        )

    class AclSizeInformation(ctypes.Structure):
        _fields_ = (
            ("ace_count", wintypes.DWORD),
            ("acl_bytes_in_use", wintypes.DWORD),
            ("acl_bytes_free", wintypes.DWORD),
        )

    if (
        ctypes.sizeof(AceHeader) != 4
        or AccessAllowedAce.sid_start.offset != 8
        or ctypes.sizeof(AclSizeInformation) != 12
    ):
        raise InstrumentError(
            "private-permissions-failed", "Windows ACL structure layout is unsupported"
        )

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    owner = wintypes.LPVOID()
    dacl = wintypes.LPVOID()
    descriptor = wintypes.LPVOID()
    advapi32.GetNamedSecurityInfoW.argtypes = (
        wintypes.LPCWSTR,
        ctypes.c_int,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.LPVOID),
    )
    advapi32.GetNamedSecurityInfoW.restype = wintypes.DWORD
    advapi32.GetSecurityDescriptorControl.argtypes = (
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.WORD),
        ctypes.POINTER(wintypes.DWORD),
    )
    advapi32.GetSecurityDescriptorControl.restype = wintypes.BOOL
    advapi32.ConvertStringSidToSidW.argtypes = (
        wintypes.LPCWSTR,
        ctypes.POINTER(wintypes.LPVOID),
    )
    advapi32.ConvertStringSidToSidW.restype = wintypes.BOOL
    advapi32.EqualSid.argtypes = (wintypes.LPVOID, wintypes.LPVOID)
    advapi32.EqualSid.restype = wintypes.BOOL
    advapi32.GetAclInformation.argtypes = (
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.c_int,
    )
    advapi32.GetAclInformation.restype = wintypes.BOOL
    advapi32.IsValidAcl.argtypes = (wintypes.LPVOID,)
    advapi32.IsValidAcl.restype = wintypes.BOOL
    advapi32.GetAce.argtypes = (
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.LPVOID),
    )
    advapi32.GetAce.restype = wintypes.BOOL
    advapi32.IsValidSid.argtypes = (wintypes.LPVOID,)
    advapi32.IsValidSid.restype = wintypes.BOOL
    advapi32.GetLengthSid.argtypes = (wintypes.LPVOID,)
    advapi32.GetLengthSid.restype = wintypes.DWORD
    kernel32.LocalFree.argtypes = (wintypes.HLOCAL,)
    kernel32.LocalFree.restype = wintypes.HLOCAL

    current_sid = wintypes.LPVOID()
    if not advapi32.ConvertStringSidToSidW(
        _windows_current_sid(), ctypes.byref(current_sid)
    ) or not current_sid.value:
        raise _windows_error("current process SID could not be parsed")
    try:
        status = advapi32.GetNamedSecurityInfoW(
            str(path),
            _SE_FILE_OBJECT,
            _OWNER_SECURITY_INFORMATION | _DACL_SECURITY_INFORMATION,
            ctypes.byref(owner),
            None,
            ctypes.byref(dacl),
            None,
            ctypes.byref(descriptor),
        )
        if status != 0 or not descriptor.value or not owner.value or not dacl.value:
            raise _windows_error("private path ACL could not be read", int(status))
        control = wintypes.WORD()
        revision = wintypes.DWORD()
        if not advapi32.GetSecurityDescriptorControl(
            descriptor, ctypes.byref(control), ctypes.byref(revision)
        ):
            raise _windows_error("private path ACL control could not be read")
        if not advapi32.IsValidSid(owner) or not advapi32.IsValidAcl(dacl):
            return False
        acl_info = AclSizeInformation()
        if not advapi32.GetAclInformation(
            dacl,
            ctypes.byref(acl_info),
            ctypes.sizeof(acl_info),
            _ACL_SIZE_INFORMATION_CLASS,
        ):
            raise _windows_error("private path DACL shape could not be read")
        if acl_info.ace_count != 1:
            return False
        ace_pointer = wintypes.LPVOID()
        if not advapi32.GetAce(dacl, 0, ctypes.byref(ace_pointer)) or not ace_pointer.value:
            raise _windows_error("private path ACE could not be read")
        ace = ctypes.cast(
            ace_pointer, ctypes.POINTER(AccessAllowedAce)
        ).contents
        if (
            ace.header.ace_type != _ACCESS_ALLOWED_ACE_TYPE
            or ace.header.ace_size < AccessAllowedAce.sid_start.offset + 8
        ):
            return False
        trustee = ctypes.cast(
            ctypes.byref(ace, AccessAllowedAce.sid_start.offset), wintypes.LPVOID
        )
        if not advapi32.IsValidSid(trustee):
            return False
        sid_length = int(advapi32.GetLengthSid(trustee))
        if sid_length <= 0:
            raise _windows_error("current process SID length could not be read")
        return _windows_acl_shape_is_private(
            dacl_present=bool(control.value & _SE_DACL_PRESENT),
            protected=bool(control.value & _SE_DACL_PROTECTED),
            owner_matches=bool(advapi32.EqualSid(owner, current_sid)),
            ace_count=int(acl_info.ace_count),
            ace_type=int(ace.header.ace_type),
            ace_flags=int(ace.header.ace_flags),
            access_mask=int(ace.mask),
            trustee_matches=bool(advapi32.EqualSid(trustee, current_sid)),
            ace_size_matches=(
                int(ace.header.ace_size)
                == AccessAllowedAce.sid_start.offset + sid_length
            ),
            directory=directory,
        )
    finally:
        if descriptor.value:
            kernel32.LocalFree(descriptor)
        kernel32.LocalFree(current_sid)


def _set_windows_private_path(path: Path, *, directory: bool) -> None:
    """Set and verify one current-user-only protected DACL without subprocesses."""

    from ctypes import wintypes

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    descriptor = wintypes.LPVOID()
    size = wintypes.DWORD()
    advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.DWORD),
    )
    advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    advapi32.GetSecurityDescriptorDacl.argtypes = (
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.BOOL),
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.BOOL),
    )
    advapi32.GetSecurityDescriptorDacl.restype = wintypes.BOOL
    advapi32.GetSecurityDescriptorOwner.argtypes = (
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.BOOL),
    )
    advapi32.GetSecurityDescriptorOwner.restype = wintypes.BOOL
    advapi32.SetNamedSecurityInfoW.argtypes = (
        wintypes.LPWSTR,
        ctypes.c_int,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.LPVOID,
    )
    advapi32.SetNamedSecurityInfoW.restype = wintypes.DWORD
    kernel32.LocalFree.argtypes = (wintypes.HLOCAL,)
    kernel32.LocalFree.restype = wintypes.HLOCAL

    expected = _windows_private_sddl(directory=directory)
    if not advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        expected,
        _SDDL_REVISION_1,
        ctypes.byref(descriptor),
        ctypes.byref(size),
    ):
        raise _windows_error("private ACL descriptor could not be constructed")
    try:
        present = wintypes.BOOL()
        defaulted = wintypes.BOOL()
        dacl = wintypes.LPVOID()
        if not advapi32.GetSecurityDescriptorDacl(
            descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)
        ) or not present.value or not dacl.value:
            raise _windows_error("private ACL descriptor has no DACL")
        owner = wintypes.LPVOID()
        owner_defaulted = wintypes.BOOL()
        if not advapi32.GetSecurityDescriptorOwner(
            descriptor, ctypes.byref(owner), ctypes.byref(owner_defaulted)
        ) or not owner.value:
            raise _windows_error("private ACL descriptor has no owner")
        status = advapi32.SetNamedSecurityInfoW(
            str(path),
            _SE_FILE_OBJECT,
            _OWNER_SECURITY_INFORMATION
            | _DACL_SECURITY_INFORMATION
            | _PROTECTED_DACL_SECURITY_INFORMATION,
            owner,
            None,
            dacl,
            None,
        )
        if status != 0:
            raise _windows_error("private path ACL could not be set", int(status))
    finally:
        kernel32.LocalFree(descriptor)
    if not _windows_path_acl_is_private(path, directory=directory):
        raise InstrumentError(
            "private-permissions-failed", "private path ACL differs from the fixed descriptor"
        )


def _assert_private_path(path: Path) -> None:
    if not path.exists() or _is_reparse(path):
        raise InstrumentError(
            "private-permissions-failed", "private path is missing or redirected"
        )
    if os.name == "nt":
        if not _windows_path_acl_is_private(path, directory=path.is_dir()):
            raise InstrumentError(
                "private-permissions-failed", "private path ACL differs from the fixed descriptor"
            )
        return
    if path.stat().st_mode & 0o077:
        raise InstrumentError(
            "private-permissions-failed", "private path grants group or other permissions"
        )


def _posix_private_mode(current_mode: int, *, directory: bool) -> int:
    if directory:
        return stat.S_IRWXU
    execute = stat.S_IXUSR if current_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) else 0
    return stat.S_IRUSR | stat.S_IWUSR | execute


def _secure_directory(path: Path, *, recursive: bool = False) -> Path:
    """Create and verify a private tree without launching external ACL helpers."""

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise InstrumentError(
            "private-permissions-failed", "private directory could not be created"
        ) from exc
    targets = [path]
    if recursive:
        targets.extend(sorted(path.rglob("*"), key=lambda item: str(item)))
    for target in targets:
        metadata = target.lstat()
        if (
            _is_reparse(target)
            or not (target.is_dir() or target.is_file())
            or (target.is_file() and getattr(metadata, "st_nlink", 1) != 1)
        ):
            raise InstrumentError(
                "private-permissions-failed", "private tree contains a redirected or special entry"
            )
        if os.name == "nt":
            _set_windows_private_path(target, directory=target.is_dir())
        else:
            try:
                os.chmod(
                    target,
                    _posix_private_mode(
                        target.stat().st_mode, directory=target.is_dir()
                    ),
                )
            except OSError as exc:
                raise InstrumentError(
                    "private-permissions-failed", "private path mode could not be set"
                ) from exc
        _assert_private_path(target)
    return path


def _ordinary_file(path: Path, *, label: str, require_single_link: bool = True) -> Path:
    candidate = Path(path)
    try:
        metadata = candidate.lstat()
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise InstrumentError("unsafe-file-boundary", f"{label} is unavailable") from exc
    if (
        _is_reparse(candidate)
        or not candidate.is_file()
        or resolved != candidate.absolute()
        or (require_single_link and getattr(metadata, "st_nlink", 1) != 1)
    ):
        raise InstrumentError(
            "unsafe-file-boundary", f"{label} must be one ordinary private file"
        )
    return resolved


def _sha256_file(path: Path, *, label: str) -> str:
    source = _ordinary_file(path, label=label)
    digest = hashlib.sha256()
    try:
        before = source.stat()
        with source.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        after = source.stat()
    except OSError as exc:
        raise InstrumentError("unsafe-file-boundary", f"{label} could not be hashed") from exc
    if (
        before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ino != after.st_ino
        or before.st_dev != after.st_dev
    ):
        raise InstrumentError("file-drift", f"{label} changed while it was hashed")
    return digest.hexdigest()


def _runtime_platform() -> str:
    return f"{sys.platform}-{platform.machine().casefold()}"


@functools.lru_cache(maxsize=1)
def _trusted_process_environment() -> dict[str, str]:
    """Synthesize executable-resolution inputs without trusting the caller environment."""

    if os.name == "nt":
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetWindowsDirectoryW.argtypes = (wintypes.LPWSTR, wintypes.UINT)
        kernel32.GetWindowsDirectoryW.restype = wintypes.UINT
        buffer = ctypes.create_unicode_buffer(32768)
        length = kernel32.GetWindowsDirectoryW(buffer, len(buffer))
        if length == 0 or length >= len(buffer):
            raise _windows_error("trusted Windows directory could not be resolved")
        windows = Path(buffer.value).resolve(strict=True)
        system32 = windows / "System32"
        comspec = _ordinary_file(
            system32 / "cmd.exe", label="trusted command shell", require_single_link=False
        )
        return {
            "SYSTEMROOT": str(windows),
            "WINDIR": str(windows),
            "COMSPEC": str(comspec),
            "PATH": str(system32),
            "PATHEXT": ".COM;.EXE;.BAT;.CMD",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
    return {
        "PATH": "/usr/bin:/bin",
        "COMSPEC": "/bin/sh",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


def verify_python_runtime(
    runtime_profile: codex_runtime.RuntimeProfile | None = None,
) -> tuple[Path, str]:
    """Bind the running evaluator and later hook interpreter to one reviewed runtime."""

    executable = _ordinary_file(Path(sys.executable), label="Python runtime")
    digest = _sha256_file(executable, label="Python runtime")
    version = ".".join(str(item) for item in sys.version_info[:3])
    expected_platform = (
        runtime_profile.runtime_platform
        if runtime_profile is not None
        else run_codex_routing.RUNTIME_PLATFORM
    )
    expected_version = (
        runtime_profile.python_version
        if runtime_profile is not None
        else run_codex_routing.PYTHON_VERSION
    )
    expected_digest = (
        runtime_profile.python_executable_sha256
        if runtime_profile is not None
        else run_codex_routing.PYTHON_EXECUTABLE_SHA256
    )
    expected_path = runtime_profile.python_executable_path if runtime_profile is not None else None
    if (
        _runtime_platform() != expected_platform
        or version != expected_version
        or digest != expected_digest
        or (expected_path is not None and executable != expected_path)
    ):
        raise InstrumentError(
            "python-runtime-mismatch",
            "Python runtime does not match the fixed platform, version, and executable pin",
        )
    return executable, digest


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _tree_digest(root: Path, names: Sequence[str]) -> str:
    entries: list[tuple[str, str]] = []
    for name in names:
        path = root / name
        entries.append((name, _sha256_file(path, label=f"evaluator {name}")))
    return _canonical_sha256(entries)


def _exact_hook_tree_digest(root: Path) -> str:
    """Hash the hook import directory only when it contains the two authorized files."""

    directory = Path(root)
    try:
        if _is_reparse(directory) or not directory.is_dir():
            raise InstrumentError(
                "hook-bundle-drift", "trusted hook bundle changed during trial"
            )
        entries = list(directory.iterdir())
    except OSError as exc:
        raise InstrumentError(
            "hook-bundle-drift", "trusted hook bundle changed during trial"
        ) from exc
    expected = set(HOOK_BUNDLE_FILES)
    if len(entries) != len(expected) or {entry.name for entry in entries} != expected:
        raise InstrumentError(
            "hook-bundle-drift", "trusted hook bundle changed during trial"
        )
    return _tree_digest(directory, HOOK_BUNDLE_FILES)


def _stable_file_bytes(path: Path, *, label: str, max_bytes: int) -> bytes:
    source = _ordinary_file(path, label=label)
    try:
        before = source.stat()
        if before.st_size <= 0 or before.st_size > max_bytes:
            raise InstrumentError("unsafe-file-boundary", f"{label} size is invalid")
        content = source.read_bytes()
        after = source.stat()
    except OSError as exc:
        raise InstrumentError("unsafe-file-boundary", f"{label} could not be read") from exc
    if (
        len(content) != before.st_size
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ino != after.st_ino
        or before.st_dev != after.st_dev
    ):
        raise InstrumentError("file-drift", f"{label} changed while it was read")
    return content


def validate_trial_contract(
    scenario: Mapping[str, object],
    spec: codex_harness.TrialSpec,
    *,
    manifest_sha256: str,
    manifest_path: Path = run_codex_routing.MANIFEST_PATH,
) -> TrialContract:
    """Bind a scenario object and trial coordinate to the fixed manifest shape."""

    if not isinstance(spec, codex_harness.TrialSpec):
        raise TrialContractError("trial spec must be a TrialSpec")
    if not isinstance(manifest_sha256, str) or not SHA256_RE.fullmatch(manifest_sha256):
        raise TrialContractError("manifest digest must be one lowercase SHA-256")
    try:
        evaluator_manifest_sha256 = hashlib.sha256(
            _stable_file_bytes(
                manifest_path,
                label="Terra evaluator manifest",
                max_bytes=1024 * 1024,
            )
        ).hexdigest()
    except InstrumentError as exc:
        raise TrialContractError("evaluator manifest bytes could not be verified") from exc
    if manifest_sha256 != evaluator_manifest_sha256:
        raise TrialContractError("manifest digest does not match evaluator manifest bytes")
    scenario_id = scenario.get("id")
    if scenario_id != spec.scenario_id:
        raise TrialContractError("scenario id does not match the trial spec")
    expected_cohort = (
        "paired"
        if scenario_id in run_codex_routing.PAIRED_IDS
        else "current_only"
        if scenario_id in run_codex_routing.CURRENT_ONLY_IDS
        else None
    )
    if expected_cohort is None or spec.cohort != expected_cohort:
        raise TrialContractError("scenario cohort does not match the fixed campaign")
    allowed_revisions = (
        {run_codex_routing.BEFORE_REVISION, run_codex_routing.CURRENT_REVISION}
        if expected_cohort == "paired"
        else {run_codex_routing.CURRENT_REVISION}
    )
    if spec.revision not in allowed_revisions:
        raise TrialContractError("trial revision does not match the fixed campaign cohort")
    if isinstance(spec.trial, bool) or spec.trial not in range(1, codex_harness.TRIALS + 1):
        raise TrialContractError("trial number is outside the fixed campaign")
    if scenario.get("mode") != "discovery" or scenario.get("split") != "regression":
        raise TrialContractError("scenario must be one discovery regression")
    scenario_sha256 = scenario.get("_source_sha256")
    if not isinstance(scenario_sha256, str) or not SHA256_RE.fullmatch(scenario_sha256):
        raise TrialContractError("scenario source digest is invalid")
    if scenario_sha256 != spec.scenario_sha256:
        raise TrialContractError("scenario digest does not match the manifest-bound trial spec")
    prompt = scenario.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        raise TrialContractError("scenario prompt must be non-empty text")
    try:
        codex_harness.reject_credentials(prompt, location="scenario_prompt")
    except codex_harness.CredentialExposureError as exc:
        raise TrialContractError("scenario prompt contains credential-shaped text") from exc
    routing = scenario.get("routing")
    if not isinstance(routing, Mapping):
        raise TrialContractError("scenario routing contract is missing")
    enable_multi_agent = routing.get("scope") == "root"
    return TrialContract(
        scenario_id=str(scenario_id),
        cohort=spec.cohort,
        revision=spec.revision,
        trial=spec.trial,
        scenario_sha256=scenario_sha256,
        prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        manifest_sha256=manifest_sha256,
        prompt=prompt,
        enable_multi_agent=enable_multi_agent,
    )


def scrubbed_environment(
    *,
    home: Path,
    codex_home: Path,
    temp: Path,
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build an allowlisted environment and relocate every user-state directory."""

    del source
    env = _trusted_process_environment().copy()
    appdata = home / "appdata"
    localappdata = home / "localappdata"
    env.update(
        {
            "CODEX_HOME": str(codex_home),
            "HOME": str(home),
            "USERPROFILE": str(home),
            "APPDATA": str(appdata),
            "LOCALAPPDATA": str(localappdata),
            "TEMP": str(temp),
            "TMP": str(temp),
            "TMPDIR": str(temp),
            "NO_COLOR": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
        }
    )
    try:
        codex_harness.reject_credentials(env, location="child_environment")
    except codex_harness.CredentialExposureError as exc:
        raise InstrumentError(
            "credential-shaped-environment", "child environment contains credential-shaped text"
        ) from exc
    return env


def _private_write(path: Path, content: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise InstrumentError("create-only-boundary", "private destination already exists")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise InstrumentError("create-only-boundary", "private file could not be created") from exc
    finally:
        if "descriptor" in locals() and descriptor >= 0:
            os.close(descriptor)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as exc:
        raise InstrumentError("private-permissions-failed", "private file mode could not be set") from exc


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError("duplicate auth JSON key")
        value[key] = child
    return value


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"invalid auth JSON constant {value}")


def _collect_sensitive_strings(value: object) -> tuple[str, ...]:
    found: set[str] = set()

    def visit(child: object) -> None:
        if isinstance(child, str):
            if len(child) >= 8:
                found.add(child)
            return
        if isinstance(child, Mapping):
            for nested in child.values():
                visit(nested)
            return
        if isinstance(child, list):
            for nested in child:
                visit(nested)

    visit(value)
    return tuple(sorted(found))


def _auth_guard_from_bytes(raw: bytes) -> AuthGuard:
    try:
        auth_value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise InstrumentError("auth-boundary-failed", "Codex auth is not strict JSON") from exc
    if not isinstance(auth_value, Mapping):
        raise InstrumentError("auth-boundary-failed", "Codex auth must be one JSON object")
    sensitive_values = _collect_sensitive_strings(auth_value)
    if not sensitive_values:
        raise InstrumentError(
            "auth-boundary-failed", "Codex auth contains no guardable string values"
        )
    return AuthGuard(sensitive_values=sensitive_values)


def load_auth_guard(source: Path) -> AuthGuard:
    """Read a stable auth file only to refresh the transient exact-output guard."""

    raw = _stable_file_bytes(
        Path(source), label="Codex auth", max_bytes=MAX_AUTH_BYTES
    )
    guard = _auth_guard_from_bytes(raw)
    del raw
    return guard


def copy_auth_file(source: Path, destination: Path) -> AuthGuard:
    """Copy one stable regular auth file without retaining its bytes or digest."""

    _secure_directory(destination.parent)
    origin = _ordinary_file(Path(source), label="Codex auth", require_single_link=True)
    try:
        before = origin.stat()
        if before.st_size <= 0 or before.st_size > MAX_AUTH_BYTES:
            raise InstrumentError("auth-boundary-failed", "Codex auth file size is invalid")
        raw = origin.read_bytes()
        after = origin.stat()
    except OSError as exc:
        raise InstrumentError("auth-boundary-failed", "Codex auth file could not be read") from exc
    if (
        len(raw) != before.st_size
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ino != after.st_ino
        or before.st_dev != after.st_dev
        or getattr(after, "st_nlink", 1) != 1
    ):
        raise InstrumentError("auth-boundary-failed", "Codex auth file changed while copied")
    guard = _auth_guard_from_bytes(raw)
    _private_write(destination, raw)
    if os.name == "nt":
        _set_windows_private_path(destination, directory=False)
    _assert_private_path(destination)
    try:
        copied = destination.read_bytes()
    except OSError as exc:
        raise InstrumentError("auth-boundary-failed", "Codex auth copy could not be verified") from exc
    if copied != raw:
        raise InstrumentError("auth-boundary-failed", "Codex auth copy differs from its source")
    del copied
    del raw
    return guard


def remove_auth_file(destination: Path) -> None:
    """Remove and verify absence of the disposable auth copy before parsing output."""

    target = _ordinary_file(
        Path(destination), label="disposable Codex auth", require_single_link=True
    )
    _assert_private_path(target)
    try:
        target.unlink()
    except OSError as exc:
        raise InstrumentError(
            "auth-copy-removal-failed", "disposable Codex auth could not be removed"
        ) from exc
    try:
        target.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise InstrumentError(
            "auth-copy-removal-failed", "disposable Codex auth absence could not be verified"
        ) from exc
    raise InstrumentError(
        "auth-copy-removal-failed", "disposable Codex auth still exists after removal"
    )


def _hook_tree(files: Mapping[str, bytes]) -> str:
    return _canonical_sha256(
        [(name, hashlib.sha256(files[name]).hexdigest()) for name in sorted(files)]
    )


def copy_hook_bundle(source_root: Path, destination: Path) -> HookBundleReceipt:
    """Copy the exact trusted recorder and parser into one empty private directory."""

    source = Path(source_root).resolve(strict=True)
    target = Path(destination).resolve(strict=True)
    try:
        if _is_reparse(target) or not target.is_dir() or any(target.iterdir()):
            raise InstrumentError(
                "hook-bundle-boundary-failed",
                "hook bundle destination must be one empty ordinary directory",
            )
    except OSError as exc:
        raise InstrumentError(
            "hook-bundle-boundary-failed", "hook bundle destination could not be inspected"
        ) from exc
    source_files = {
        name: _stable_file_bytes(
            source / name, label=f"hook bundle source {name}", max_bytes=2 * 1024 * 1024
        )
        for name in HOOK_BUNDLE_FILES
    }
    source_tree = _hook_tree(source_files)
    for name, content in source_files.items():
        _private_write(target / name, content)
    _secure_directory(target, recursive=True)
    staged_files = {
        name: _stable_file_bytes(
            target / name, label=f"staged hook bundle {name}", max_bytes=2 * 1024 * 1024
        )
        for name in HOOK_BUNDLE_FILES
    }
    staged_tree = _exact_hook_tree_digest(target)
    if staged_files != source_files or staged_tree != source_tree:
        raise InstrumentError(
            "hook-bundle-boundary-failed", "staged hook bundle differs from trusted source"
        )
    return HookBundleReceipt(
        file_count=len(source_files),
        source_tree_sha256=source_tree,
        staged_tree_sha256=staged_tree,
        recorder_path=target / "codex_hook_recorder.py",
    )


def copy_authorized_executable(
    source: Path,
    destination: Path,
    *,
    expected_sha256: str | None = None,
) -> Path:
    """Copy only the manifest-pinned Codex executable into the private trial boundary."""

    origin = _ordinary_file(Path(source), label="Codex executable")
    target = Path(destination)
    _secure_directory(target.parent)
    if target.exists() or target.is_symlink():
        raise InstrumentError("create-only-boundary", "runtime executable already exists")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_BINARY", 0)
    digest = hashlib.sha256()
    descriptor = -1
    try:
        before = origin.stat()
        if before.st_size <= 0 or before.st_size > MAX_CODEX_EXECUTABLE_BYTES:
            raise InstrumentError(
                "codex-executable-mismatch", "Codex executable size is outside the fixed boundary"
            )
        descriptor = os.open(target, flags, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        with origin.open("rb") as input_stream, os.fdopen(descriptor, "wb") as output_stream:
            descriptor = -1
            copied = 0
            while True:
                chunk = input_stream.read(1024 * 1024)
                if not chunk:
                    break
                copied += len(chunk)
                if copied > MAX_CODEX_EXECUTABLE_BYTES:
                    raise InstrumentError(
                        "codex-executable-mismatch", "Codex executable exceeded the byte limit"
                    )
                digest.update(chunk)
                output_stream.write(chunk)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        after = origin.stat()
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    if (
        copied != before.st_size
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ino != after.st_ino
        or before.st_dev != after.st_dev
    ):
        target.unlink(missing_ok=True)
        raise InstrumentError(
            "codex-executable-drift", "Codex executable changed while it was copied"
        )
    authorized_sha256 = expected_sha256 or run_codex_routing.CODEX_EXECUTABLE_SHA256
    if digest.hexdigest() != authorized_sha256:
        target.unlink(missing_ok=True)
        raise InstrumentError(
            "codex-executable-mismatch",
            "Codex executable does not match the manifest-authorized digest",
        )
    try:
        os.chmod(target, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    except OSError as exc:
        target.unlink(missing_ok=True)
        raise InstrumentError(
            "private-permissions-failed", "runtime executable permissions could not be set"
        ) from exc
    _secure_directory(target.parent, recursive=True)
    if _sha256_file(target, label="staged Codex executable") != digest.hexdigest():
        raise InstrumentError(
            "codex-executable-drift", "staged Codex executable differs from authorized bytes"
        )
    return target.resolve(strict=True)


def verify_hook_bundle(
    source_root: Path, bundle: HookBundleReceipt
) -> None:
    """Re-read source and staged hook bytes to close the hash-then-use window."""

    source_tree = _tree_digest(Path(source_root), HOOK_BUNDLE_FILES)
    staged_tree = _exact_hook_tree_digest(bundle.recorder_path.parent)
    if (
        source_tree != bundle.source_tree_sha256
        or staged_tree != bundle.staged_tree_sha256
        or source_tree != staged_tree
    ):
        raise InstrumentError("hook-bundle-drift", "trusted hook bundle changed during trial")


def _default_command_runner(
    command: tuple[str, ...],
    *,
    env: dict[str, str],
    timeout_s: int,
    cwd: Path,
) -> subprocess.CompletedProcess[bytes]:
    capture = launch_process(
        command,
        prompt="",
        cwd=cwd,
        env=env,
        timeout_s=timeout_s,
        output_limit=MAX_PROCESS_OUTPUT_BYTES,
    )
    if capture.timed_out or capture.output_limited:
        raise InstrumentError("codex-probe-failed", "Codex probe did not complete")
    return subprocess.CompletedProcess(
        list(command),
        capture.returncode,
        capture.stdout.encode("utf-8"),
        capture.stderr.encode("utf-8"),
    )


def probe_codex(
    executable: Path,
    env: Mapping[str, str],
    *,
    cwd: Path,
    expected_cli_version: str = codex_harness.CODEX_CLI_VERSION,
    command_runner: CommandRunner = _default_command_runner,
) -> CodexProbe:
    """Prove exact CLI bytes/version and return the local bundled catalog transiently."""

    codex_bin = _ordinary_file(Path(executable), label="Codex executable")
    executable_sha256 = _sha256_file(codex_bin, label="Codex executable")
    child_env = dict(env)
    version = command_runner(
        (str(codex_bin), "--version"),
        env=child_env,
        timeout_s=PROBE_TIMEOUT_SECONDS,
        cwd=Path(cwd),
    )
    try:
        version_stdout = version.stdout.decode("utf-8", errors="strict")
        version_stderr = version.stderr.decode("utf-8", errors="strict")
        codex_harness.reject_credentials(
            {"stdout": version_stdout, "stderr": version_stderr}, location="codex_version"
        )
    except (UnicodeDecodeError, codex_harness.CredentialExposureError) as exc:
        raise InstrumentError("codex-cli-version-mismatch", "Codex CLI version output is invalid") from exc
    if not isinstance(expected_cli_version, str) or not expected_cli_version:
        raise InstrumentError("codex-cli-version-mismatch", "Codex CLI version pin is invalid")
    expected = f"codex-cli {expected_cli_version}"
    if version.returncode != 0 or version_stdout.strip() != expected or version_stderr.strip():
        raise InstrumentError(
            "codex-cli-version-mismatch",
            f"Codex CLI version must be exactly {expected_cli_version}",
        )

    catalog = command_runner(
        (str(codex_bin), "debug", "models", "--bundled"),
        env=child_env,
        timeout_s=PROBE_TIMEOUT_SECONDS,
        cwd=Path(cwd),
    )
    try:
        catalog_stderr = catalog.stderr.decode("utf-8", errors="strict")
        codex_harness.reject_credentials(catalog_stderr, location="codex_catalog_stderr")
    except (UnicodeDecodeError, codex_harness.CredentialExposureError) as exc:
        raise InstrumentError("model-catalog-probe-failed", "Codex model catalog output is invalid") from exc
    if (
        catalog.returncode != 0
        or catalog_stderr.strip()
        or not catalog.stdout
        or len(catalog.stdout) > codex_model_catalog.MAX_CATALOG_BYTES
    ):
        raise InstrumentError(
            "model-catalog-probe-failed", "Codex bundled model catalog could not be read"
        )
    return CodexProbe(
        cli_version=expected_cli_version,
        executable_sha256=executable_sha256,
        bundled_catalog=bytes(catalog.stdout),
    )


def _open_private_capture(path: Path):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, stat.S_IRUSR | stat.S_IWUSR)
    return os.fdopen(descriptor, "wb")


def _create_windows_job(process: subprocess.Popen[bytes]) -> int:
    """Assign a suspended process to a kill-on-close Job Object, then resume it."""

    import ctypes
    from ctypes import wintypes

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    ntdll.NtResumeProcess.argtypes = (wintypes.HANDLE,)
    ntdll.NtResumeProcess.restype = ctypes.c_long

    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
    raw_handle = int(handle)
    try:
        limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        limits.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            raise OSError(ctypes.get_last_error(), "SetInformationJobObject failed")
        process_handle = wintypes.HANDLE(int(process._handle))  # type: ignore[attr-defined]
        if not kernel32.AssignProcessToJobObject(handle, process_handle):
            raise OSError(ctypes.get_last_error(), "AssignProcessToJobObject failed")
        if ntdll.NtResumeProcess(process_handle) != 0:
            raise OSError("NtResumeProcess failed")
    except BaseException:
        kernel32.CloseHandle(handle)
        raise
    return raw_handle


def _spawn_bounded_process(
    command: tuple[str, ...],
    *,
    cwd: Path,
    env: dict[str, str],
    stdin: int,
    stdout: object,
    stderr: object,
) -> tuple[subprocess.Popen[bytes], int | None]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    if os.name == "nt":
        creationflags |= 0x00000004  # CREATE_SUSPENDED closes the pre-assignment child race.
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=env,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        creationflags=creationflags,
        start_new_session=os.name != "nt",
    )
    try:
        job = _create_windows_job(process) if os.name == "nt" else None
    except BaseException:
        process.kill()
        process.wait(timeout=10)
        raise
    return process, job


def _bounded_git_runner(
    command: Sequence[str],
    *,
    stdout: object,
    stderr: object,
    stdin: int,
    cwd: Path,
    env: Mapping[str, str],
    timeout: int,
    check: bool,
) -> subprocess.CompletedProcess[bytes]:
    """Run the pinned Git archive process inside the same kill-on-close boundary as Codex."""

    if (
        stdout is not subprocess.PIPE
        or stderr is not subprocess.PIPE
        or stdin is not subprocess.DEVNULL
        or check
    ):
        raise InstrumentError(
            "process-tree-boundary-failed", "Git runner received an unsupported process contract"
        )
    child_env = dict(env)
    temp = Path(child_env.get("TEMP", ""))
    if not temp.is_absolute():
        raise InstrumentError(
            "process-tree-boundary-failed", "Git runner requires a private absolute TEMP"
        )
    stdout_path = temp / f"git-stdout-{uuid.uuid4().hex}.bin"
    stderr_path = temp / f"git-stderr-{uuid.uuid4().hex}.bin"
    process: subprocess.Popen[bytes] | None = None
    job: int | None = None
    timed_out = False
    terminated = False
    output_limit = codex_snapshot.MAX_ARCHIVE_BYTES + (1024 * 1024)
    try:
        with _open_private_capture(stdout_path) as stdout_stream, _open_private_capture(
            stderr_path
        ) as stderr_stream:
            process, job = _spawn_bounded_process(
                tuple(command),
                cwd=Path(cwd),
                env=child_env,
                stdin=subprocess.DEVNULL,
                stdout=stdout_stream,
                stderr=stderr_stream,
            )
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    timed_out = True
                    _terminate_process_tree(process, job)
                    terminated = True
                    break
                try:
                    if stdout_path.stat().st_size + stderr_path.stat().st_size > output_limit:
                        _terminate_process_tree(process, job)
                        terminated = True
                        raise InstrumentError(
                            "process-output-limit",
                            "Git archive output exceeded its fixed bound",
                        )
                except OSError as exc:
                    _terminate_process_tree(process, job)
                    terminated = True
                    raise InstrumentError(
                        "process-capture-failed", "Git output capture could not be inspected"
                    ) from exc
                time.sleep(0.05)
            try:
                returncode = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _terminate_process_tree(process, job)
                terminated = True
                returncode = process.wait(timeout=10)
                timed_out = True
        if timed_out:
            raise subprocess.TimeoutExpired(tuple(command), timeout)
        if stdout_path.stat().st_size + stderr_path.stat().st_size > output_limit:
            raise InstrumentError(
                "process-output-limit", "Git archive output exceeded its fixed bound"
            )
        stdout_bytes = stdout_path.read_bytes()
        stderr_bytes = stderr_path.read_bytes()
        if len(stdout_bytes) + len(stderr_bytes) > output_limit:
            raise InstrumentError(
                "process-output-limit", "Git archive output exceeded its fixed bound"
            )
        return subprocess.CompletedProcess(
            list(command), returncode, stdout_bytes, stderr_bytes
        )
    except (InstrumentError, subprocess.TimeoutExpired):
        raise
    except (OSError, subprocess.SubprocessError) as exc:
        raise InstrumentError(
            "process-launch-failed", "Git archive process could not run"
        ) from exc
    finally:
        if process is not None:
            _close_process_boundary(process, job, terminated=terminated)
        for capture_path in (stdout_path, stderr_path):
            try:
                capture_path.unlink(missing_ok=True)
            except OSError:
                pass


def _terminate_process_tree(process: subprocess.Popen[bytes], job: int | None) -> None:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        if job is None:
            raise InstrumentError("process-tree-boundary-failed", "Windows Job Object is missing")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
        kernel32.TerminateJobObject.restype = wintypes.BOOL
        if not kernel32.TerminateJobObject(wintypes.HANDLE(job), 1):
            raise InstrumentError(
                "process-tree-boundary-failed", "Windows process tree could not be terminated"
            )
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        # The INITIAL termination is the load-bearing one. If the group cannot be signalled here
        # then it has not been terminated and a descendant may still be running, so this stays
        # fail-closed. Raising the boundary code rather than letting a bare OSError escape also
        # stops the caller reinterpreting a termination failure as a launch failure.
        raise InstrumentError(
            "process-tree-boundary-failed", "POSIX process tree could not be terminated"
        ) from exc


def _close_process_boundary(
    process: subprocess.Popen[bytes], job: int | None, *, terminated: bool = False
) -> None:
    """Final boundary close. `terminated` states that a prior kill of this group already succeeded.

    It defaults to False because that is the safe reading: on every normal-completion path
    `_terminate_process_tree` is never called, so this close is the FIRST and ONLY kill of the
    group -- and it is what removes a descendant the leader spawned before exiting.
    """

    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        if job is None:
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        if not kernel32.CloseHandle(wintypes.HANDLE(job)):
            raise InstrumentError(
                "process-tree-boundary-failed", "Windows Job Object could not be closed"
            )
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        # This runs from a `finally` on every path, including straight after a completed
        # termination-and-wait. Once the group leader has been reaped, macOS may answer EPERM
        # rather than ESRCH for its process group id, so a second kill raised out of the `finally`
        # and turned an already-successful cleanup into a test error — masking whatever exception
        # was actually in flight.
        #
        # Tolerated ONLY when a prior kill of this group already succeeded AND the leader has been
        # reaped -- the narrow state where this call genuinely re-runs completed work.
        #
        # A reaped leader is NOT on its own evidence that the group was terminated. On every
        # normal-completion path nothing was killed first: the leader exits by itself, `poll()` is
        # already non-None, and this close is the only attempt to kill a descendant it may have
        # spawned before exiting. Inferring "already terminated" from `poll()` alone would
        # silently accept a failed first-and-only kill and let that descendant escape -- the exact
        # failure this boundary exists to prevent, reintroduced by the repair for a different one.
        if not terminated or process.poll() is None:
            raise InstrumentError(
                "process-tree-boundary-failed",
                "POSIX process tree could not be signalled and may still be running",
            ) from exc


def launch_process(
    command: tuple[str, ...],
    *,
    prompt: str,
    cwd: Path,
    env: dict[str, str],
    timeout_s: int,
    output_limit: int,
) -> ProcessCapture:
    """Launch Codex with private bounded raw captures that are destroyed by the caller."""

    stdout_path = Path(env["TEMP"]) / f"stdout-{uuid.uuid4().hex}.jsonl"
    stderr_path = Path(env["TEMP"]) / f"stderr-{uuid.uuid4().hex}.txt"
    started = time.monotonic()
    timed_out = False
    terminated = False
    output_limited = False
    returncode = -1
    process: subprocess.Popen[bytes] | None = None
    job: int | None = None
    try:
        with _open_private_capture(stdout_path) as stdout_stream, _open_private_capture(
            stderr_path
        ) as stderr_stream:
            process, job = _spawn_bounded_process(
                command,
                cwd=cwd,
                env=env,
                stdin=subprocess.PIPE,
                stdout=stdout_stream,
                stderr=stderr_stream,
            )
            assert process.stdin is not None
            try:
                process.stdin.write(prompt.encode("utf-8"))
                process.stdin.close()
            except (BrokenPipeError, OSError):
                try:
                    process.stdin.close()
                except OSError:
                    pass
            deadline = started + timeout_s
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    timed_out = True
                    _terminate_process_tree(process, job)
                    terminated = True
                    break
                try:
                    if stdout_path.stat().st_size + stderr_path.stat().st_size > output_limit:
                        output_limited = True
                        _terminate_process_tree(process, job)
                        terminated = True
                        break
                except OSError:
                    _terminate_process_tree(process, job)
                    terminated = True
                    raise InstrumentError(
                        "process-capture-failed", "Codex output capture could not be inspected"
                    )
                time.sleep(0.05)
            try:
                returncode = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _terminate_process_tree(process, job)
                terminated = True
                returncode = process.wait(timeout=10)
                timed_out = True
    except InstrumentError:
        raise
    except (OSError, subprocess.SubprocessError) as exc:
        raise InstrumentError("process-launch-failed", "Codex trial process could not run") from exc
    finally:
        if process is not None:
            _close_process_boundary(process, job, terminated=terminated)
    duration_ms = max(0, int((time.monotonic() - started) * 1000))
    try:
        captured_bytes = stdout_path.stat().st_size + stderr_path.stat().st_size
    except OSError as exc:
        raise InstrumentError(
            "process-capture-failed", "Codex output capture could not be inspected"
        ) from exc
    if captured_bytes > output_limit:
        output_limited = True
        stdout_raw = b""
        stderr_raw = b""
    else:
        try:
            stdout_raw = stdout_path.read_bytes()
            stderr_raw = stderr_path.read_bytes()
        except OSError as exc:
            raise InstrumentError(
                "process-capture-failed", "Codex output capture could not be read"
            ) from exc
        if len(stdout_raw) + len(stderr_raw) > output_limit:
            output_limited = True
            stdout_raw = b""
            stderr_raw = b""
    try:
        stdout = stdout_raw.decode("utf-8", errors="strict")
        stderr = stderr_raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise InstrumentError("process-output-invalid", "Codex output is not strict UTF-8") from exc
    return ProcessCapture(
        stdout=stdout,
        stderr=stderr,
        returncode=returncode,
        duration_ms=duration_ms,
        timed_out=timed_out,
        output_limited=output_limited,
    )


def _receipt_dict(value: object) -> dict[str, object]:
    result = dataclasses.asdict(value)
    for key, child in list(result.items()):
        if isinstance(child, tuple):
            result[key] = list(child)
    return result


def _sanitized_argv(
    command: tuple[str, ...], codex_bin: Path, workspace: Path
) -> list[str]:
    replacements = {
        str(codex_bin): "<codex-bin>",
        str(workspace): "<workspace>",
    }
    sanitized = [replacements.get(value, value) for value in command]
    if any(str(workspace) in value or str(codex_bin) in value for value in sanitized):
        raise InstrumentError("argv-sanitization-failed", "Codex argv contains an unbound path")
    return sanitized


def _base_result(
    contract: TrialContract,
    *,
    state: codex_routing_grade.VerdictState,
    reason_codes: tuple[str, ...],
    exact_revision: bool,
    runtime_facts: dict[str, object] | None = None,
    trace_facts: dict[str, object] | None = None,
    hook_facts: dict[str, object] | None = None,
    verdict_facts: dict[str, object] | None = None,
) -> TrialResult:
    return TrialResult(
        scenario_id=contract.scenario_id,
        cohort=contract.cohort,
        revision=contract.revision,
        trial=contract.trial,
        state=state,
        reason_codes=reason_codes,
        manifest_sha256=contract.manifest_sha256,
        scenario_sha256=contract.scenario_sha256,
        prompt_sha256=contract.prompt_sha256,
        exact_revision=exact_revision,
        tool_policy=(
            "no-local-effect-tools-root-collaboration-unscored"
            if contract.enable_multi_agent
            else "no-model-tools-non-root"
        ),
        runtime_facts=runtime_facts,
        trace_facts=trace_facts,
        hook_facts=hook_facts,
        verdict_facts=verdict_facts,
    )


@contextlib.contextmanager
def _private_trial_directory(
    *, parent: Path | None, repository: Path
):
    """Create one exact temp root and fail visibly if private cleanup cannot complete."""

    if parent is None:
        raise InstrumentError(
            "unsafe-temp-boundary", "private trial parent is required"
        )
    _assert_private_path(parent)
    raw = tempfile.mkdtemp(
        prefix="save-toolkit-terra-trial-",
        dir=str(parent),
    )
    root = Path(raw).resolve(strict=True)
    try:
        if root == repository or root.is_relative_to(repository):
            raise InstrumentError(
                "unsafe-temp-boundary", "trial directory must be outside the checkout"
            )
        if root.parent != parent or _is_reparse(root) or any(root.iterdir()):
            raise InstrumentError(
                "unsafe-temp-boundary",
                "fresh trial directory is redirected, misplaced, or nonempty",
            )
        _secure_directory(root)
        _assert_private_path(parent)
        yield root
    finally:
        if _is_reparse(root):
            print(
                f"codex-terra-routing: WARNING private trial path was redirected and was not "
                f"removed: {root}",
                file=sys.stderr,
            )
            raise InstrumentError(
                "private-cleanup-failed", "private trial path was redirected before cleanup"
            )
        try:
            shutil.rmtree(root)
        except OSError as exc:
            print(
                f"codex-terra-routing: WARNING private trial cleanup failed; remove this "
                f"credential-bearing path manually: {root}",
                file=sys.stderr,
            )
            raise InstrumentError(
                "private-cleanup-failed", "private trial directory could not be removed"
            ) from exc


def _validated_private_parent(path: Path, repository: Path) -> Path:
    """Revalidate the externally bound private ancestor without resolving through links."""

    candidate = Path(path)
    if not candidate.is_absolute() or candidate != Path(os.path.abspath(candidate)):
        raise InstrumentError(
            "unsafe-temp-boundary", "private trial parent must be absolute and normalized"
        )
    current = Path(candidate.anchor)
    try:
        for component in candidate.parts[1:]:
            current /= component
            metadata = current.lstat()
            if _is_reparse(current) or (
                current == candidate and not stat.S_ISDIR(metadata.st_mode)
            ):
                raise InstrumentError(
                    "unsafe-temp-boundary",
                    "private trial parent traverses a redirected or non-directory path",
                )
        resolved = candidate.resolve(strict=True)
    except InstrumentError:
        raise
    except OSError as exc:
        raise InstrumentError(
            "unsafe-temp-boundary", "private trial parent is unavailable"
        ) from exc
    if resolved != candidate:
        raise InstrumentError(
            "unsafe-temp-boundary", "private trial parent resolves through indirection"
        )
    if (
        candidate == repository
        or candidate.is_relative_to(repository)
        or repository.is_relative_to(candidate)
    ):
        raise InstrumentError(
            "unsafe-temp-boundary", "private trial parent must be outside the checkout"
        )
    _validate_private_root_locality(candidate)
    _secure_directory(candidate)
    return candidate


def _preflight_process_forbidden(*_args: object, **_kwargs: object) -> ProcessCapture:
    """Make an accidental authenticated/model-process step fail closed during preflight."""

    raise InstrumentError(
        "preflight-model-process-attempted",
        "credential-free preflight attempted to start the model process",
    )


def run_preflight(
    *,
    repo_root: Path,
    codex_bin: Path,
    scenario: Mapping[str, object],
    spec: codex_harness.TrialSpec,
    manifest_sha256: str,
    exact_revision: bool,
    runtime_profile: codex_runtime.RuntimeProfile | None = None,
    temp_parent: Path | None = None,
    command_runner: CommandRunner = _default_command_runner,
) -> TrialResult:
    """Exercise the real credential-free setup and stop before auth or a model request."""

    return _execute_trial(
        repo_root=repo_root,
        codex_bin=codex_bin,
        auth_file=None,
        scenario=scenario,
        spec=spec,
        manifest_sha256=manifest_sha256,
        exact_revision=exact_revision,
        runtime_profile=runtime_profile,
        credential_free_only=True,
        temp_parent=temp_parent,
        command_runner=command_runner,
        process_runner=_preflight_process_forbidden,
    )


def run_trial(
    *,
    repo_root: Path,
    codex_bin: Path,
    auth_file: Path,
    scenario: Mapping[str, object],
    spec: codex_harness.TrialSpec,
    manifest_sha256: str,
    exact_revision: bool,
    runtime_profile: codex_runtime.RuntimeProfile | None = None,
    temp_parent: Path | None = None,
    command_runner: CommandRunner = _default_command_runner,
    process_runner: ProcessRunner = launch_process,
) -> TrialResult:
    """Execute one fixed trial and return only sanitized, authority-bounded evidence."""

    return _execute_trial(
        repo_root=repo_root,
        codex_bin=codex_bin,
        auth_file=auth_file,
        scenario=scenario,
        spec=spec,
        manifest_sha256=manifest_sha256,
        exact_revision=exact_revision,
        runtime_profile=runtime_profile,
        credential_free_only=False,
        temp_parent=temp_parent,
        command_runner=command_runner,
        process_runner=process_runner,
    )


def _execute_trial(
    *,
    repo_root: Path,
    codex_bin: Path,
    auth_file: Path | None,
    scenario: Mapping[str, object],
    spec: codex_harness.TrialSpec,
    manifest_sha256: str,
    exact_revision: bool,
    runtime_profile: codex_runtime.RuntimeProfile | None,
    credential_free_only: bool,
    temp_parent: Path | None,
    command_runner: CommandRunner,
    process_runner: ProcessRunner,
) -> TrialResult:
    """Run the shared setup, optionally continuing into the authenticated model step."""

    contract = validate_trial_contract(
        scenario,
        spec,
        manifest_sha256=manifest_sha256,
        manifest_path=(
            runtime_profile.manifest_path
            if runtime_profile is not None
            else run_codex_routing.MANIFEST_PATH
        ),
    )
    if not isinstance(exact_revision, bool):
        raise TrialContractError("exact_revision must be a caller-supplied boolean")
    evaluator_root = Path(__file__).resolve().parent
    expected_codex_cli_version = (
        runtime_profile.codex_cli_version
        if runtime_profile is not None
        else codex_harness.CODEX_CLI_VERSION
    )
    runtime_facts: dict[str, object] = {
        "codex_cli_version": expected_codex_cli_version,
    }
    expected_codex_sha256 = (
        runtime_profile.codex_executable_sha256
        if runtime_profile is not None
        else run_codex_routing.CODEX_EXECUTABLE_SHA256
    )
    expected_python_version = (
        runtime_profile.python_version
        if runtime_profile is not None
        else run_codex_routing.PYTHON_VERSION
    )
    evaluator_files = (
        runtime_profile.evaluator_files
        if runtime_profile is not None
        else EVALUATOR_FILES
    )
    finish_after_launch: Callable[..., TrialResult] | None = None

    def finish_result(
        *,
        state: codex_routing_grade.VerdictState,
        reason_codes: tuple[str, ...],
        trace_facts: dict[str, object] | None = None,
        hook_facts: dict[str, object] | None = None,
        verdict_facts: dict[str, object] | None = None,
    ) -> TrialResult:
        if finish_after_launch is not None:
            return finish_after_launch(
                state=state,
                reason_codes=reason_codes,
                trace_facts=trace_facts,
                hook_facts=hook_facts,
                verdict_facts=verdict_facts,
            )
        return _base_result(
            contract,
            state=state,
            reason_codes=reason_codes,
            exact_revision=exact_revision,
            runtime_facts=runtime_facts,
            trace_facts=trace_facts,
            hook_facts=hook_facts,
            verdict_facts=verdict_facts,
        )

    try:
        python_executable, python_sha256 = verify_python_runtime(runtime_profile)
        runtime_facts["evaluator_tree_sha256"] = _tree_digest(evaluator_root, evaluator_files)
    except InstrumentError as exc:
        return finish_result(
            state=codex_routing_grade.VerdictState.INCONCLUSIVE,
            reason_codes=(exc.reason_code,),
        )
    repository = Path(repo_root).resolve(strict=True)
    try:
        parent = _validated_private_parent(
            Path(temp_parent) if temp_parent is not None else Path(), repository
        ) if temp_parent is not None else None
        with _private_trial_directory(parent=parent, repository=repository) as root:
            _secure_directory(root)
            paths = {
                name: root / name
                for name in (
                    "probe-home",
                    "codex-home",
                    "home",
                    "temp",
                    "snapshot",
                    "project",
                    "receipts",
                    "hook-bundle",
                    "runtime",
                )
            }
            for path in paths.values():
                _secure_directory(path)
            for path in (paths["home"] / "appdata", paths["home"] / "localappdata"):
                _secure_directory(path)

            snapshot_receipt = codex_snapshot.materialize_snapshot(
                repository,
                contract.revision,
                paths["snapshot"],
                git_executable=(
                    runtime_profile.git_executable_path
                    if runtime_profile is not None
                    else codex_snapshot.GIT_EXECUTABLE_PATH
                ),
                git_executable_sha256=(
                    runtime_profile.git_executable_sha256
                    if runtime_profile is not None
                    else codex_snapshot.GIT_EXECUTABLE_SHA256
                ),
                command_runner=_bounded_git_runner,
            )
            stage_receipt = codex_snapshot.stage_neutral_project(
                paths["snapshot"], paths["project"]
            )
            if runtime_profile is not None and not runtime_profile.copy_codex_executable:
                staged_codex = _ordinary_file(Path(codex_bin), label="protected Codex executable")
                if (
                    runtime_profile.codex_executable_path is None
                    or staged_codex != runtime_profile.codex_executable_path
                    or _sha256_file(staged_codex, label="protected Codex executable")
                    != expected_codex_sha256
                ):
                    raise InstrumentError(
                        "codex-executable-mismatch",
                        "protected Codex executable differs from the runtime profile",
                    )
            else:
                staged_codex = copy_authorized_executable(
                    Path(codex_bin),
                    paths["runtime"] / ("codex.exe" if os.name == "nt" else "codex"),
                    expected_sha256=expected_codex_sha256,
                )
            probe_env = scrubbed_environment(
                home=paths["home"],
                codex_home=paths["probe-home"],
                temp=paths["temp"],
            )
            probe = probe_codex(
                staged_codex,
                probe_env,
                cwd=paths["probe-home"],
                expected_cli_version=expected_codex_cli_version,
                command_runner=command_runner,
            )
            if probe.executable_sha256 != expected_codex_sha256:
                raise InstrumentError(
                    "codex-executable-mismatch",
                    "staged Codex executable differs from the manifest pin",
                )
            catalog_path = paths["codex-home"] / "route-models.json"
            catalog_receipt = codex_model_catalog.write_safe_catalog(
                probe.bundled_catalog, catalog_path
            )

            nonce = uuid.uuid4().hex
            hook_bundle = copy_hook_bundle(evaluator_root, paths["hook-bundle"])
            recorder = hook_bundle.recorder_path
            config = run_codex_routing.render_config(
                python_executable,
                recorder,
                paths["receipts"],
                catalog_path,
                nonce,
            )
            config_path = paths["codex-home"] / "config.toml"
            _private_write(config_path, config.encode("utf-8"))
            _secure_directory(root, recursive=True)

            env = scrubbed_environment(
                home=paths["home"],
                codex_home=paths["codex-home"],
                temp=paths["temp"],
            )
            resolved_codex = _ordinary_file(staged_codex, label="staged Codex executable")
            if (
                _sha256_file(resolved_codex, label="staged Codex executable")
                != expected_codex_sha256
            ):
                raise InstrumentError(
                    "codex-executable-drift",
                    "staged Codex executable changed before auth copy",
                )
            command = run_codex_routing.build_command(
                resolved_codex,
                paths["project"],
                enable_multi_agent=contract.enable_multi_agent,
            )
            argv = _sanitized_argv(command, resolved_codex, paths["project"])
            runtime_facts.update(
                {
                    "codex_cli_version": probe.cli_version,
                    "codex_executable_sha256": probe.executable_sha256,
                    "runtime_platform": _runtime_platform(),
                    "python_version": expected_python_version,
                    "python_executable_sha256": python_sha256,
                    "hook_bundle": hook_bundle.persistable_facts(),
                    "snapshot": _receipt_dict(snapshot_receipt),
                    "stage": _receipt_dict(stage_receipt),
                    "model_catalog": _receipt_dict(catalog_receipt),
                    "config_sha256": hashlib.sha256(config.encode("utf-8")).hexdigest(),
                    "argv": argv,
                    "argv_sha256": _canonical_sha256(argv),
                    "environment_keys": sorted(env),
                    "environment_keys_sha256": _canonical_sha256(sorted(env)),
                }
            )
            codex_snapshot.verify_staged_project(
                paths["snapshot"], paths["project"], stage_receipt
            )
            verify_hook_bundle(evaluator_root, hook_bundle)
            if (
                _sha256_file(config_path, label="Codex config")
                != runtime_facts["config_sha256"]
                or _sha256_file(catalog_path, label="safe model catalog")
                != codex_model_catalog.EXPECTED_SAFE_CATALOG_SHA256
                or _sha256_file(python_executable, label="Python executable")
                != python_sha256
                or _tree_digest(evaluator_root, evaluator_files)
                != runtime_facts["evaluator_tree_sha256"]
            ):
                raise InstrumentError(
                    "credential-free-boundary-drift",
                    "credential-free trial inputs changed before auth copy",
                )

            if credential_free_only:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("credential-free-preflight-pass",),
                )
            if auth_file is None:
                raise TrialContractError("authenticated trial requires an auth file")

            # This is deliberately the final preparation step. Its helper applies and verifies the
            # private destination ACL before returning; the next operation launches Codex once.
            auth_destination = paths["codex-home"] / "auth.json"
            auth_guard = copy_auth_file(Path(auth_file), auth_destination)
            try:
                capture = process_runner(
                    command,
                    prompt=contract.prompt,
                    cwd=paths["project"],
                    env=env,
                    timeout_s=codex_harness.TIMEOUT_SECONDS,
                    output_limit=MAX_PROCESS_OUTPUT_BYTES,
                )
            except BaseException:
                remove_auth_file(auth_destination)
                raise
            runtime_facts.update(
                {
                    "returncode": capture.returncode,
                    "duration_ms": capture.duration_ms,
                    "timed_out": capture.timed_out,
                    "output_limited": capture.output_limited,
                }
            )

            def _finish_after_launch(
                *,
                state: codex_routing_grade.VerdictState,
                reason_codes: tuple[str, ...],
                trace_facts: dict[str, object] | None = None,
                hook_facts: dict[str, object] | None = None,
                verdict_facts: dict[str, object] | None = None,
            ) -> TrialResult:
                try:
                    codex_snapshot.verify_staged_project(
                        paths["snapshot"], paths["project"], stage_receipt
                    )
                    verify_hook_bundle(evaluator_root, hook_bundle)
                    drift = (
                        _sha256_file(resolved_codex, label="staged Codex executable")
                        != expected_codex_sha256
                        or _sha256_file(config_path, label="Codex config")
                        != runtime_facts["config_sha256"]
                        or _sha256_file(catalog_path, label="safe model catalog")
                        != codex_model_catalog.EXPECTED_SAFE_CATALOG_SHA256
                        or _sha256_file(python_executable, label="Python executable")
                        != python_sha256
                        or _tree_digest(evaluator_root, evaluator_files)
                        != runtime_facts["evaluator_tree_sha256"]
                    )
                except (
                    InstrumentError,
                    codex_snapshot.SnapshotError,
                    OSError,
                    ValueError,
                ):
                    drift = True
                if drift:
                    state = codex_routing_grade.VerdictState.INCONCLUSIVE
                    reason_codes = ("post-trial-input-drift",)
                    trace_facts = None
                    hook_facts = None
                    verdict_facts = None
                return _base_result(
                    contract,
                    state=state,
                    reason_codes=reason_codes,
                    exact_revision=exact_revision,
                    runtime_facts=runtime_facts,
                    trace_facts=trace_facts,
                    hook_facts=hook_facts,
                    verdict_facts=verdict_facts,
                )

            finish_after_launch = _finish_after_launch
            refreshed_guard = auth_guard
            refresh_problem: str | None = None
            removal_problem: str | None = None
            try:
                try:
                    refreshed_guard = auth_guard.merged(load_auth_guard(auth_destination))
                except InstrumentError as exc:
                    refresh_problem = exc.reason_code
            finally:
                try:
                    remove_auth_file(auth_destination)
                except InstrumentError as exc:
                    removal_problem = exc.reason_code
            if removal_problem is not None:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("auth-copy-removal-failed",),
                )
            scan_problem = refresh_problem
            try:
                refreshed_guard.reject_output(capture.stdout)
                refreshed_guard.reject_output(capture.stderr)
                refreshed_guard.reject_jsonl(capture.stdout)
                codex_harness.reject_credentials(
                    {"stdout": capture.stdout, "stderr": capture.stderr},
                    location="trial_output",
                )
            except (CredentialEchoError, codex_harness.CredentialExposureError):
                scan_problem = "credential-shaped-output"
            except InstrumentError as exc:
                if scan_problem is None:
                    scan_problem = exc.reason_code
            if scan_problem is not None:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=(scan_problem,),
                )
            if capture.timed_out:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("process-timeout",),
                )
            if capture.output_limited:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("process-output-limit",),
                )
            runtime_facts.update(
                {
                    "stdout_bytes": len(capture.stdout.encode("utf-8")),
                    "stderr_bytes": len(capture.stderr.encode("utf-8")),
                    "stderr_sha256": hashlib.sha256(
                        capture.stderr.encode("utf-8")
                    ).hexdigest(),
                }
            )
            try:
                trace = codex_harness.parse_jsonl(
                    capture.stdout, process_exit_code=capture.returncode
                )
                hooks = codex_hook_recorder.load_receipts(
                    paths["receipts"], nonce, payload_validator=refreshed_guard.reject_value
                )
            except CredentialEchoError:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("credential-shaped-output",),
                )
            except (OSError, ValueError, codex_harness.TraceError):
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("trace-or-hook-invalid",),
                )
            verdict = codex_routing_grade.grade_trial(scenario, trace, hooks)
            return finish_result(
                state=verdict.state,
                reason_codes=verdict.reason_codes,
                trace_facts=trace.persistable_facts(),
                hook_facts=hooks.persistable_facts(),
                verdict_facts=verdict.as_dict(),
            )
    except InstrumentError as exc:
        return finish_result(
            state=codex_routing_grade.VerdictState.INCONCLUSIVE,
            reason_codes=(exc.reason_code,),
        )
    except codex_snapshot.SnapshotError:
        return finish_result(
            state=codex_routing_grade.VerdictState.INCONCLUSIVE,
            reason_codes=("snapshot-boundary-failed",),
        )
    except codex_model_catalog.CatalogError:
        return finish_result(
            state=codex_routing_grade.VerdictState.INCONCLUSIVE,
            reason_codes=("model-catalog-mismatch",),
        )
    except (OSError, ValueError):
        return finish_result(
            state=codex_routing_grade.VerdictState.INCONCLUSIVE,
            reason_codes=("executor-boundary-failed",),
        )
