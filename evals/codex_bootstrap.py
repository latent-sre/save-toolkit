#!/usr/bin/env python3
"""Externally authorized, hash-bound bootstrap for a staged Codex evaluator.

This module deliberately does not authorize itself.  A separately trusted launcher must execute
the exact bootstrap bytes it has pinned and pass the expected SHA-256 of the bundle manifest.  The
manifest is an allowlist, not a source of expected authority: only the caller-supplied digest makes
its contents eligible for staging.

An active process under the same OS identity can race or replace files after any user-space check;
that threat requires an outer sandbox or distinct account and is outside this bootstrap's
enforceable boundary.

The bootstrap imports only the Python standard library.  It must be launched with an absolute
interpreter path and ``-I -S -B``.  It copies the manifest-bound evaluator closure as ordinary
files into a fresh directory outside the source tree, verifies the exact staged tree, and appends
only its ``evals`` directory after the interpreter's standard-library paths before executing the
``run_codex_routing.py``.  No source evaluator byte is imported directly.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import hmac
import json
import ntpath
import os
import re
import runpy
import shutil
import stat
import sys
import sysconfig
import tempfile
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


SCHEMA_VERSION = 1
ENTRYPOINT = "evals/run_codex_routing.py"
CANARY_MANIFEST = "evals/conformance/codex-terra-routing-v1.json"
CANARY_BUNDLE_FILES = frozenset(
    {
        "evals/run_codex_routing.py",
        "evals/codex_trial.py",
        "evals/codex_harness.py",
        "evals/codex_hook_recorder.py",
        "evals/codex_model_catalog.py",
        "evals/codex_routing_grade.py",
        "evals/codex_snapshot.py",
        "evals/graders.py",
        CANARY_MANIFEST,
    }
)
MANIFEST_KEYS = frozenset({"schema_version", "files"})
FILE_KEYS = frozenset({"path", "sha256", "size"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_FILES = 512
COPY_CHUNK_BYTES = 1024 * 1024

CONTRACT_FAILURE_EXIT = 70
CLEANUP_FAILURE_EXIT = 74
EVALUATOR_FAILURE_EXIT = 1

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

_WINDOWS_RESERVED = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{number}" for number in range(1, 10)),
        *(f"LPT{number}" for number in range(1, 10)),
    }
)
_WINDOWS_FORBIDDEN = frozenset('<>:"|?*')


class BootstrapError(ValueError):
    """The isolated staging or execution contract could not be established."""


class CleanupError(BootstrapError):
    """A private stage could not be removed and manual host cleanup is required."""


@dataclass(frozen=True)
class BundleEntry:
    """One manifest-authorized ordinary file."""

    path: str
    sha256: str
    size: int


@dataclass(frozen=True)
class RuntimeContext:
    """Runtime facts; injectable only so isolation failures can be tested deterministically."""

    flags: object
    executable: str
    cwd: Path
    sys_path: tuple[str, ...]


@dataclass(frozen=True)
class WindowsVolumeFacts:
    """In-process Win32 facts that bind a private root to direct local NTFS storage."""

    drive_type: int
    filesystem: str
    dos_device: str
    volume_root: str


def _current_runtime() -> RuntimeContext:
    return RuntimeContext(
        flags=sys.flags,
        executable=sys.executable,
        cwd=Path.cwd(),
        sys_path=tuple(sys.path),
    )


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        metadata = path.lstat()
    except OSError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _is_below(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _opened_identity(metadata: os.stat_result) -> tuple[int, ...]:
    """Fields that Windows reports consistently through both path and handle stat calls."""

    return (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
        metadata.st_nlink,
        metadata.st_size,
    )


def _windows_error(message: str, code: int | None = None) -> BootstrapError:
    error = ctypes.WinError(code if code is not None else ctypes.get_last_error())
    return BootstrapError(f"{message}: {error}")


def _windows_volume_facts(path: str, drive: str) -> WindowsVolumeFacts:
    """Read drive type, filesystem, volume root, and DOS-device target in-process."""

    if os.name != "nt":
        raise BootstrapError("Windows volume lookup is unavailable")
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
        raise _windows_error("private root volume could not be resolved")
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
        raise _windows_error("private root filesystem could not be read")

    device_buffer = ctypes.create_unicode_buffer(32768)
    length = int(kernel32.QueryDosDeviceW(drive, device_buffer, len(device_buffer)))
    if length == 0:
        raise _windows_error("private root drive mapping could not be read")
    targets = tuple(
        target
        for target in "".join(device_buffer[:length]).split("\0")
        if target
    )
    if len(targets) != 1:
        raise BootstrapError("private root drive mapping is ambiguous")
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
        raise BootstrapError("private root must use a local fixed drive")
    facts = volume_probe(value, drive.upper())
    if facts.drive_type != _DRIVE_FIXED:
        raise BootstrapError("private root must use local fixed storage")
    if facts.filesystem.casefold() != "ntfs":
        raise BootstrapError("private root must use NTFS")
    expected_root = f"{drive.upper()}\\"
    if ntpath.normcase(ntpath.normpath(facts.volume_root)) != ntpath.normcase(
        ntpath.normpath(expected_root)
    ):
        raise BootstrapError("private root must use a direct drive volume")
    if re.fullmatch(
        r"\\Device\\HarddiskVolume[0-9]+", facts.dos_device, re.IGNORECASE
    ) is None:
        raise BootstrapError("private root drive is substituted or mapped")


def _validate_private_root_locality(path: Path) -> None:
    """Apply the platform storage contract to the exact externally supplied root."""

    if os.name == "nt":
        _validate_windows_private_root_locality(os.fspath(path))


def _windows_current_sid() -> str:
    """Return the current process-user SID without starting another process."""

    if os.name != "nt":
        raise BootstrapError("Windows SID lookup is unavailable")
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

    if not advapi32.OpenProcessToken(
        kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)
    ):
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
        raise BootstrapError("current process SID has an invalid shape")
    return sid


def _windows_private_directory_sddl() -> str:
    sid = _windows_current_sid()
    return f"O:{sid}D:P(A;OICI;FA;;;{sid})"


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
) -> bool:
    """Validate exact access semantics independently of DACL serialization metadata."""

    return (
        dacl_present
        and protected
        and owner_matches
        and ace_count == 1
        and ace_type == _ACCESS_ALLOWED_ACE_TYPE
        and (ace_flags & ~_INHERITED_ACE)
        == (_OBJECT_INHERIT_ACE | _CONTAINER_INHERIT_ACE)
        and access_mask == _FILE_ALL_ACCESS
        and trustee_matches
        and ace_size_matches
    )


def _windows_directory_acl_is_private(path: Path) -> bool:
    """Verify one current-user-only protected directory DACL in-process."""

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
        raise BootstrapError("Windows ACL structure layout is unsupported")

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
            raise _windows_error("private directory ACL could not be read", int(status))
        control = wintypes.WORD()
        revision = wintypes.DWORD()
        if not advapi32.GetSecurityDescriptorControl(
            descriptor, ctypes.byref(control), ctypes.byref(revision)
        ):
            raise _windows_error("private directory ACL control could not be read")
        if not advapi32.IsValidSid(owner) or not advapi32.IsValidAcl(dacl):
            return False
        acl_info = AclSizeInformation()
        if not advapi32.GetAclInformation(
            dacl,
            ctypes.byref(acl_info),
            ctypes.sizeof(acl_info),
            _ACL_SIZE_INFORMATION_CLASS,
        ):
            raise _windows_error("private directory DACL shape could not be read")
        if acl_info.ace_count != 1:
            return False
        ace_pointer = wintypes.LPVOID()
        if not advapi32.GetAce(dacl, 0, ctypes.byref(ace_pointer)) or not ace_pointer.value:
            raise _windows_error("private directory ACE could not be read")
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
        )
    finally:
        if descriptor.value:
            kernel32.LocalFree(descriptor)
        kernel32.LocalFree(current_sid)


def _set_windows_private_directory(path: Path) -> None:
    """Set and verify a protected current-user-only directory DACL in-process."""

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

    expected = _windows_private_directory_sddl()
    if not advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        expected,
        _SDDL_REVISION_1,
        ctypes.byref(descriptor),
        ctypes.byref(size),
    ):
        raise _windows_error("private directory ACL could not be constructed")
    try:
        present = wintypes.BOOL()
        defaulted = wintypes.BOOL()
        dacl = wintypes.LPVOID()
        if not advapi32.GetSecurityDescriptorDacl(
            descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)
        ) or not present.value or not dacl.value:
            raise _windows_error("private directory ACL has no DACL")
        owner = wintypes.LPVOID()
        owner_defaulted = wintypes.BOOL()
        if not advapi32.GetSecurityDescriptorOwner(
            descriptor, ctypes.byref(owner), ctypes.byref(owner_defaulted)
        ) or not owner.value:
            raise _windows_error("private directory ACL has no owner")
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
            raise _windows_error("private directory ACL could not be set", int(status))
    finally:
        kernel32.LocalFree(descriptor)
    if not _windows_directory_acl_is_private(path):
        raise BootstrapError("private directory ACL differs from the fixed descriptor")


def _secure_empty_private_directory(path: Path) -> Path:
    """Verify and secure one caller-bound empty directory before sensitive staging."""

    directory, _metadata = _absolute_normal(Path(path), kind="directory")
    try:
        if any(directory.iterdir()):
            raise BootstrapError("private directory must start empty")
        if os.name == "nt":
            _set_windows_private_directory(directory)
        else:
            os.chmod(directory, stat.S_IRWXU)
            metadata = directory.stat()
            if metadata.st_mode & 0o077 or (
                hasattr(os, "getuid") and metadata.st_uid != os.getuid()
            ):
                raise BootstrapError("private directory ownership or mode is not private")
        verified, _verified_metadata = _absolute_normal(directory, kind="directory")
        if verified != directory or any(directory.iterdir()):
            raise BootstrapError("private directory changed while it was secured")
    except BootstrapError:
        raise
    except OSError as exc:
        raise BootstrapError("private directory could not be secured") from exc
    return directory


def _absolute_normal(path: Path, *, kind: str) -> tuple[Path, os.stat_result]:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise BootstrapError("path is not absolute")
    normalized = Path(os.path.abspath(os.fspath(candidate)))
    if candidate != normalized:
        raise BootstrapError("path is not normalized")

    anchor = Path(candidate.anchor)
    current = anchor
    try:
        for component in candidate.parts[1:]:
            current /= component
            current.lstat()
            if _is_link_or_reparse(current):
                raise BootstrapError("path traverses indirection")
        metadata = candidate.lstat()
        resolved = candidate.resolve(strict=True)
    except BootstrapError:
        raise
    except OSError as exc:
        raise BootstrapError("path is unavailable") from exc
    if resolved != candidate:
        raise BootstrapError("path does not resolve to itself")
    if kind == "directory" and not stat.S_ISDIR(metadata.st_mode):
        raise BootstrapError("path is not a directory")
    if kind == "file" and (
        not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
    ):
        raise BootstrapError("path is not one ordinary file")
    return resolved, metadata


def _assert_no_indirection_below(root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise BootstrapError("path escapes its trusted root") from exc
    current = root
    for component in relative.parts:
        current /= component
        try:
            current.lstat()
        except OSError as exc:
            raise BootstrapError("path component is unavailable") from exc
        if _is_link_or_reparse(current):
            raise BootstrapError("path traverses indirection")


def _read_regular_once(path: Path, *, maximum: int) -> tuple[bytes, os.stat_result]:
    try:
        before = path.lstat()
    except OSError as exc:
        raise BootstrapError("ordinary file is unavailable") from exc
    if (
        _is_link_or_reparse(path)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size <= 0
        or before.st_size > maximum
    ):
        raise BootstrapError("ordinary file contract is invalid")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if _opened_identity(opened) != _opened_identity(before):
                raise BootstrapError("ordinary file changed before read")
            content = stream.read(maximum + 1)
            after_handle = os.fstat(stream.fileno())
        after_path = path.lstat()
    except BootstrapError:
        raise
    except OSError as exc:
        raise BootstrapError("ordinary file could not be read") from exc
    if len(content) != before.st_size or len(content) > maximum:
        raise BootstrapError("ordinary file size changed")
    if _identity(after_handle) != _identity(opened):
        raise BootstrapError("ordinary file changed during read")
    if _opened_identity(after_path) != _opened_identity(before):
        raise BootstrapError("ordinary file changed during read")
    return content, before


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise BootstrapError("manifest contains a duplicate key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> object:
    raise BootstrapError("manifest contains a non-JSON number")


def _validate_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise BootstrapError("manifest path is empty")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise BootstrapError("manifest path is not valid Unicode") from exc
    if value != unicodedata.normalize("NFC", value):
        raise BootstrapError("manifest path is not canonically normalized")
    if "\\" in value or any(unicodedata.category(character) == "Cc" for character in value):
        raise BootstrapError("manifest path contains a forbidden character")
    drive, _tail = ntpath.splitdrive(value)
    if drive or ntpath.isabs(value) or value.startswith("/"):
        raise BootstrapError("manifest path is absolute")
    parts = value.split("/")
    if len(parts) < 2 or parts[0] != "evals":
        raise BootstrapError("manifest path is outside the evaluator bundle")
    if any(part in {"", ".", ".."} for part in parts):
        raise BootstrapError("manifest path is not normalized")
    if PurePosixPath(value).as_posix() != value:
        raise BootstrapError("manifest path is not canonical")
    for part in parts:
        if part.endswith((" ", ".")) or any(character in _WINDOWS_FORBIDDEN for character in part):
            raise BootstrapError("manifest path is not portable")
        if part.split(".", 1)[0].upper() in _WINDOWS_RESERVED:
            raise BootstrapError("manifest path uses a reserved name")
    return value


def _parse_manifest(raw: bytes) -> tuple[BundleEntry, ...]:
    try:
        decoded = raw.decode("utf-8", errors="strict")
        manifest = json.loads(
            decoded,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except BootstrapError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BootstrapError("manifest is not strict UTF-8 JSON") from exc
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS:
        raise BootstrapError("manifest schema is invalid")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != SCHEMA_VERSION:
        raise BootstrapError("manifest schema version is invalid")
    rows = manifest["files"]
    if not isinstance(rows, list) or not rows or len(rows) > MAX_FILES:
        raise BootstrapError("manifest file list is empty or oversized")

    entries: list[BundleEntry] = []
    seen: set[str] = set()
    folded: set[str] = set()
    total_bytes = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != FILE_KEYS:
            raise BootstrapError("manifest file entry schema is invalid")
        relative = _validate_relative_path(row["path"])
        digest = row["sha256"]
        size = row["size"]
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise BootstrapError("manifest file digest is invalid")
        if type(size) is not int or size <= 0 or size > MAX_FILE_BYTES:
            raise BootstrapError("manifest file size is invalid")
        normalized_fold = unicodedata.normalize("NFC", relative).casefold()
        if relative in seen or normalized_fold in folded:
            raise BootstrapError("manifest contains a path collision")
        seen.add(relative)
        folded.add(normalized_fold)
        total_bytes += size
        if total_bytes > MAX_TOTAL_BYTES:
            raise BootstrapError("manifest bundle is oversized")
        entries.append(BundleEntry(relative, digest, size))

    if ENTRYPOINT not in seen:
        raise BootstrapError("manifest is missing the fixed entrypoint")
    file_paths = set(seen)
    for relative in file_paths:
        parent = PurePosixPath(relative).parent
        while parent != PurePosixPath("."):
            if parent.as_posix() in file_paths:
                raise BootstrapError("manifest path topology collides")
            parent = parent.parent
    return tuple(entries)


def _validate_canary_bundle_entries(entries: Sequence[BundleEntry]) -> None:
    """Require the complete and only executable/data closure used by the live canary."""

    if frozenset(entry.path for entry in entries) != CANARY_BUNDLE_FILES:
        raise BootstrapError("canary bundle is not the exact evaluator closure")


def _load_manifest(
    manifest_path: Path,
    expected_sha256: str,
    *,
    after_manifest_read: Callable[[Path], None] | None,
) -> tuple[BundleEntry, ...]:
    if not isinstance(expected_sha256, str) or not SHA256_RE.fullmatch(expected_sha256):
        raise BootstrapError("expected manifest digest is invalid")
    manifest, first_metadata = _absolute_normal(Path(manifest_path), kind="file")
    first, read_metadata = _read_regular_once(manifest, maximum=MAX_MANIFEST_BYTES)
    if _identity(read_metadata) != _identity(first_metadata):
        raise BootstrapError("manifest identity changed")
    if after_manifest_read is not None:
        after_manifest_read(manifest)
    second, second_metadata = _read_regular_once(manifest, maximum=MAX_MANIFEST_BYTES)
    if first != second or _identity(read_metadata) != _identity(second_metadata):
        raise BootstrapError("manifest changed while it was loaded")
    actual = hashlib.sha256(first).hexdigest()
    if not hmac.compare_digest(actual, expected_sha256):
        raise BootstrapError("manifest digest does not match caller authority")
    return _parse_manifest(first)


def _trusted_runtime_paths(runtime_paths: Sequence[str], source_root: Path) -> tuple[str, ...]:
    if not runtime_paths:
        raise BootstrapError("runtime has no standard-library paths")
    install_roots = {
        Path(sys.base_prefix).resolve(),
        Path(sys.exec_prefix).resolve(),
        Path(sysconfig.get_path("stdlib")).resolve(),
        Path(sysconfig.get_path("platstdlib")).resolve(),
    }
    zip_name = f"python{sys.version_info.major}{sys.version_info.minor}.zip"
    expected_zip_paths = {
        Path(sysconfig.get_path("stdlib")).resolve().parent / zip_name,
        Path(sysconfig.get_path("platstdlib")).resolve().parent / zip_name,
    }
    trusted: list[str] = []
    for raw in runtime_paths:
        if not isinstance(raw, str) or not raw:
            raise BootstrapError("runtime path is empty")
        candidate = Path(raw)
        if not candidate.is_absolute():
            raise BootstrapError("runtime path is not absolute")
        normalized = Path(os.path.abspath(raw))
        if candidate != normalized or _is_below(candidate, source_root):
            raise BootstrapError("runtime path is not neutral")
        lowered_parts = {part.casefold() for part in candidate.parts}
        if "site-packages" in lowered_parts or "dist-packages" in lowered_parts:
            raise BootstrapError("runtime path includes package installation state")
        if candidate.suffix.casefold() == ".zip":
            allowed = candidate in expected_zip_paths
        else:
            try:
                resolved = candidate.resolve(strict=True)
            except OSError as exc:
                raise BootstrapError("runtime path is unavailable") from exc
            allowed = any(resolved == root or _is_below(resolved, root) for root in install_roots)
        if not allowed:
            raise BootstrapError("runtime path is outside the standard library")
        trusted.append(str(candidate))
    return tuple(trusted)


def _validate_runtime(runtime: RuntimeContext, source_root: Path) -> tuple[str, ...]:
    for flag_name in ("isolated", "no_site", "dont_write_bytecode", "safe_path"):
        if not bool(getattr(runtime.flags, flag_name, False)):
            raise BootstrapError("required interpreter isolation flag is absent")
    executable = Path(runtime.executable)
    if not executable.is_absolute():
        raise BootstrapError("Python executable is not absolute")
    try:
        executable_metadata = executable.stat()
    except OSError as exc:
        raise BootstrapError("Python executable is unavailable") from exc
    if not stat.S_ISREG(executable_metadata.st_mode):
        raise BootstrapError("Python executable is not ordinary")
    cwd, _metadata = _absolute_normal(Path(runtime.cwd), kind="directory")
    if cwd == source_root or _is_below(cwd, source_root):
        raise BootstrapError("working directory is inside the source")
    return _trusted_runtime_paths(runtime.sys_path, source_root)


def _expected_directories(entries: Sequence[BundleEntry]) -> set[str]:
    directories: set[str] = set()
    for entry in entries:
        parent = PurePosixPath(entry.path).parent
        while parent != PurePosixPath("."):
            directories.add(parent.as_posix())
            parent = parent.parent
    return directories


def _source_file(source_root: Path, entry: BundleEntry) -> tuple[Path, os.stat_result]:
    candidate = source_root.joinpath(*PurePosixPath(entry.path).parts)
    _assert_no_indirection_below(source_root, candidate)
    try:
        metadata = candidate.lstat()
    except OSError as exc:
        raise BootstrapError("bundle source file is unavailable") from exc
    if (
        _is_link_or_reparse(candidate)
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_size != entry.size
        or metadata.st_size > MAX_FILE_BYTES
    ):
        raise BootstrapError("bundle source file is not one bounded ordinary file")
    return candidate, metadata


def _hash_open_regular(path: Path, expected: os.stat_result) -> tuple[str, int, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    digest = hashlib.sha256()
    total = 0
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if _opened_identity(opened) != _opened_identity(expected):
                raise BootstrapError("bundle source changed before read")
            while chunk := stream.read(COPY_CHUNK_BYTES):
                total += len(chunk)
                if total > MAX_FILE_BYTES:
                    raise BootstrapError("bundle source grew while read")
                digest.update(chunk)
            after = os.fstat(stream.fileno())
    except BootstrapError:
        raise
    except OSError as exc:
        raise BootstrapError("bundle source could not be read") from exc
    if _identity(after) != _identity(opened):
        raise BootstrapError("bundle source changed while read")
    return digest.hexdigest(), total, after


def _copy_entry(
    source_root: Path,
    stage: Path,
    entry: BundleEntry,
    *,
    after_source_read: Callable[[str, Path], None] | None,
) -> None:
    source, before = _source_file(source_root, entry)
    target = stage.joinpath(*PurePosixPath(entry.path).parts)
    _assert_no_indirection_below(stage, target.parent)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    digest = hashlib.sha256()
    total = 0
    try:
        descriptor = os.open(source, flags)
        with os.fdopen(descriptor, "rb") as source_stream, target.open("xb") as target_stream:
            opened = os.fstat(source_stream.fileno())
            if _opened_identity(opened) != _opened_identity(before):
                raise BootstrapError("bundle source changed before copy")
            while chunk := source_stream.read(COPY_CHUNK_BYTES):
                total += len(chunk)
                if total > entry.size or total > MAX_FILE_BYTES:
                    raise BootstrapError("bundle source grew during copy")
                digest.update(chunk)
                target_stream.write(chunk)
            after_handle = os.fstat(source_stream.fileno())
    except BootstrapError:
        raise
    except OSError as exc:
        raise BootstrapError("bundle file could not be copied create-only") from exc
    if total != entry.size or not hmac.compare_digest(digest.hexdigest(), entry.sha256):
        raise BootstrapError("bundle source bytes do not match the manifest")
    if _identity(after_handle) != _identity(opened):
        raise BootstrapError("bundle source changed during copy")
    if after_source_read is not None:
        after_source_read(entry.path, source)
    source_after, metadata_after = _source_file(source_root, entry)
    if source_after != source or _identity(metadata_after) != _identity(before):
        raise BootstrapError("bundle source changed after copy")
    second_digest, second_size, _second_metadata = _hash_open_regular(source, metadata_after)
    if second_size != entry.size or not hmac.compare_digest(second_digest, entry.sha256):
        raise BootstrapError("bundle source drifted after copy")


def _scan_staged_tree(stage: Path, entries: Sequence[BundleEntry]) -> None:
    expected_files = {entry.path: entry for entry in entries}
    expected_directories = _expected_directories(entries)
    seen_files: set[str] = set()
    seen_directories: set[str] = set()
    folded: set[str] = set()
    try:
        stage_metadata = stage.lstat()
    except OSError as exc:
        raise BootstrapError("stage is unavailable") from exc
    if _is_link_or_reparse(stage) or not stat.S_ISDIR(stage_metadata.st_mode):
        raise BootstrapError("stage is not an ordinary directory")

    for current_raw, directory_names, file_names in os.walk(stage, followlinks=False):
        current = Path(current_raw)
        if _is_link_or_reparse(current):
            raise BootstrapError("staged tree traverses indirection")
        directory_names.sort()
        file_names.sort()
        for name in directory_names:
            child = current / name
            if _is_link_or_reparse(child):
                raise BootstrapError("staged tree contains indirection")
            metadata = child.lstat()
            if not stat.S_ISDIR(metadata.st_mode):
                raise BootstrapError("staged tree contains a non-directory traversal entry")
            relative = child.relative_to(stage).as_posix()
            if relative not in expected_directories or relative.casefold() in folded:
                raise BootstrapError("staged tree contains an unexpected directory")
            folded.add(relative.casefold())
            seen_directories.add(relative)
        for name in file_names:
            child = current / name
            relative = child.relative_to(stage).as_posix()
            expected = expected_files.get(relative)
            if expected is None or relative.casefold() in folded:
                raise BootstrapError("staged tree contains an unexpected file")
            if _is_link_or_reparse(child):
                raise BootstrapError("staged tree contains indirection")
            metadata = child.lstat()
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise BootstrapError("staged tree contains a nonordinary file")
            digest, size, _after = _hash_open_regular(child, metadata)
            if size != expected.size or not hmac.compare_digest(digest, expected.sha256):
                raise BootstrapError("staged file does not match the manifest")
            folded.add(relative.casefold())
            seen_files.add(relative)
    if seen_files != set(expected_files) or seen_directories != expected_directories:
        raise BootstrapError("staged tree is incomplete")


def _create_stage(source_root: Path, temp_parent: Path | None) -> Path:
    if temp_parent is None:
        raise BootstrapError("private temporary parent is required")
    parent, _metadata = _absolute_normal(Path(temp_parent), kind="directory")
    if parent == source_root or _is_below(parent, source_root):
        raise BootstrapError("temporary parent is inside the source")
    _validate_private_root_locality(parent)
    _secure_empty_private_directory(parent)
    raw = tempfile.mkdtemp(prefix="codex-bootstrap-", dir=parent)
    stage = Path(raw).resolve(strict=True)
    try:
        if stage == source_root or _is_below(stage, source_root):
            raise BootstrapError("stage is inside the source")
        if stage.parent != parent:
            raise BootstrapError("stage is outside the fixed private parent")
        _secure_empty_private_directory(stage)
        if {entry.name for entry in parent.iterdir()} != {stage.name}:
            raise BootstrapError("private parent changed while the stage was created")
    except Exception:
        try:
            shutil.rmtree(stage)
            if os.path.lexists(stage):
                raise CleanupError("rejected fresh stage still exists")
        except Exception as cleanup_error:
            raise CleanupError("rejected fresh stage could not be removed") from cleanup_error
        raise
    return stage


def _stage_bundle(
    source_root: Path,
    stage: Path,
    entries: Sequence[BundleEntry],
    *,
    after_source_read: Callable[[str, Path], None] | None,
) -> None:
    source_before = source_root.lstat()
    directories = sorted(
        _expected_directories(entries),
        key=lambda value: (len(PurePosixPath(value).parts), value),
    )
    try:
        for relative in directories:
            target = stage.joinpath(*PurePosixPath(relative).parts)
            _assert_no_indirection_below(stage, target.parent)
            target.mkdir()
        for entry in sorted(entries, key=lambda item: item.path):
            _copy_entry(
                source_root,
                stage,
                entry,
                after_source_read=after_source_read,
            )
    except OSError as exc:
        raise BootstrapError("bundle could not be staged create-only") from exc
    source_after, metadata_after = _absolute_normal(source_root, kind="directory")
    if source_after != source_root or _identity(source_before) != _identity(metadata_after):
        raise BootstrapError("source root changed while the bundle was staged")


def _system_exit_code(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    return EVALUATOR_FAILURE_EXIT


def _execute_staged(
    stage: Path,
    forwarded_args: Sequence[str],
    stdlib_paths: Sequence[str],
    *,
    entry_runner: Callable[..., object],
) -> int:
    if isinstance(forwarded_args, (str, bytes)) or not all(
        isinstance(item, str) for item in forwarded_args
    ):
        raise BootstrapError("forwarded arguments are invalid")
    entrypoint = stage.joinpath(*PurePosixPath(ENTRYPOINT).parts)
    staged_evals = entrypoint.parent
    original_path = list(sys.path)
    original_argv = list(sys.argv)
    original_python_environment = {
        key: value for key, value in os.environ.items() if key.upper().startswith("PYTHON")
    }
    try:
        for key in list(os.environ):
            if key.upper().startswith("PYTHON"):
                del os.environ[key]
        sys.path[:] = [*stdlib_paths, str(staged_evals)]
        sys.argv[:] = [str(entrypoint), *forwarded_args]
        try:
            entry_runner(str(entrypoint), run_name="__main__")
        except SystemExit as exc:
            return _system_exit_code(exc.code)
        except Exception:
            print("codex-bootstrap: staged evaluator failed", file=sys.stderr)
            return EVALUATOR_FAILURE_EXIT
        return 0
    finally:
        sys.path[:] = original_path
        sys.argv[:] = original_argv
        for key in list(os.environ):
            if key.upper().startswith("PYTHON"):
                del os.environ[key]
        os.environ.update(original_python_environment)


def run_bootstrap(
    manifest_path: Path,
    expected_manifest_sha256: str,
    source_root: Path,
    forwarded_args: Sequence[str] = (),
    *,
    runtime: RuntimeContext | None = None,
    temp_parent: Path | None = None,
    after_manifest_read: Callable[[Path], None] | None = None,
    after_source_read: Callable[[str, Path], None] | None = None,
    before_stage_verify: Callable[[Path], None] | None = None,
    argument_builder: Callable[[Path], Sequence[str]] | None = None,
    entry_validator: Callable[[Sequence[BundleEntry]], None] | None = None,
    entry_runner: Callable[..., object] = runpy.run_path,
    cleanup: Callable[[Path], None] = shutil.rmtree,
) -> int:
    """Stage and execute one caller-authorized evaluator bundle.

    Return codes are intentionally path-free: the staged evaluator's ``SystemExit`` integer is
    forwarded, 70 means the bootstrap contract was rejected, and 74 means cleanup failed and
    overrides every tentative result.
    """

    stage: Path | None = None
    result = CONTRACT_FAILURE_EXIT
    try:
        if argument_builder is not None and tuple(forwarded_args):
            raise BootstrapError("fixed and forwarded arguments cannot be combined")
        source, _source_metadata = _absolute_normal(Path(source_root), kind="directory")
        active_runtime = runtime if runtime is not None else _current_runtime()
        stdlib_paths = _validate_runtime(active_runtime, source)
        entries = _load_manifest(
            Path(manifest_path),
            expected_manifest_sha256,
            after_manifest_read=after_manifest_read,
        )
        if entry_validator is not None:
            entry_validator(entries)
        stage = _create_stage(source, temp_parent)
        _stage_bundle(
            source,
            stage,
            entries,
            after_source_read=after_source_read,
        )
        if before_stage_verify is not None:
            before_stage_verify(stage)
        _scan_staged_tree(stage, entries)
        effective_args = (
            tuple(argument_builder(stage))
            if argument_builder is not None
            else tuple(forwarded_args)
        )
        result = _execute_staged(
            stage,
            effective_args,
            stdlib_paths,
            entry_runner=entry_runner,
        )
        _scan_staged_tree(stage, entries)
    except CleanupError:
        print(
            "codex-bootstrap: private stage cleanup failed; manual cleanup required",
            file=sys.stderr,
        )
        result = CLEANUP_FAILURE_EXIT
    except Exception:
        print("codex-bootstrap: evaluator bundle rejected", file=sys.stderr)
        result = CONTRACT_FAILURE_EXIT
    finally:
        if stage is not None:
            try:
                cleanup(stage)
                if os.path.lexists(stage):
                    raise CleanupError("private stage still exists after cleanup")
            except Exception:
                print(
                    "codex-bootstrap: private stage cleanup failed; manual cleanup required",
                    file=sys.stderr,
                )
                result = CLEANUP_FAILURE_EXIT
    return result


def _fixed_canary_args(
    stage: Path,
    *,
    repo_root: Path,
    codex_bin: Path,
    auth_file: Path,
    private_root: Path,
) -> tuple[str, ...]:
    """Construct the only evaluator argv accepted by the authoritative canary CLI."""

    staged_manifest, _manifest_metadata = _absolute_normal(
        stage.joinpath(*PurePosixPath(CANARY_MANIFEST).parts), kind="file"
    )
    repository, _repository_metadata = _absolute_normal(Path(repo_root), kind="directory")
    executable, _executable_metadata = _absolute_normal(Path(codex_bin), kind="file")
    credentials, _credentials_metadata = _absolute_normal(Path(auth_file), kind="file")
    private, _private_metadata = _absolute_normal(Path(private_root), kind="directory")
    return (
        "--canary",
        "--manifest",
        str(staged_manifest),
        "--repo-root",
        str(repository),
        "--codex-bin",
        str(executable),
        "--auth-file",
        str(credentials),
        "--private-root",
        str(private),
    )


def _fixed_preflight_args(
    stage: Path,
    *,
    repo_root: Path,
    codex_bin: Path,
    private_root: Path,
) -> tuple[str, ...]:
    """Construct the auth-free evaluator argv accepted by the diagnostic preflight."""

    staged_manifest, _manifest_metadata = _absolute_normal(
        stage.joinpath(*PurePosixPath(CANARY_MANIFEST).parts), kind="file"
    )
    repository, _repository_metadata = _absolute_normal(Path(repo_root), kind="directory")
    executable, _executable_metadata = _absolute_normal(Path(codex_bin), kind="file")
    private, _private_metadata = _absolute_normal(Path(private_root), kind="directory")
    return (
        "--preflight",
        "--manifest",
        str(staged_manifest),
        "--repo-root",
        str(repository),
        "--codex-bin",
        str(executable),
        "--private-root",
        str(private),
    )


def run_preflight_bootstrap(
    manifest_path: Path,
    expected_manifest_sha256: str,
    source_root: Path,
    *,
    repo_root: Path,
    codex_bin: Path,
    private_root: Path,
) -> int:
    """Stage the reviewed evaluator and run setup without auth or a model request."""

    return run_bootstrap(
        manifest_path,
        expected_manifest_sha256,
        source_root,
        argument_builder=lambda stage: _fixed_preflight_args(
            stage,
            repo_root=repo_root,
            codex_bin=codex_bin,
            private_root=private_root,
        ),
        entry_validator=_validate_canary_bundle_entries,
        temp_parent=private_root,
    )


def run_canary_bootstrap(
    manifest_path: Path,
    expected_manifest_sha256: str,
    source_root: Path,
    *,
    repo_root: Path,
    codex_bin: Path,
    auth_file: Path,
    private_root: Path,
) -> int:
    """Stage the reviewed evaluator and synthesize one non-overridable canary request."""

    return run_bootstrap(
        manifest_path,
        expected_manifest_sha256,
        source_root,
        argument_builder=lambda stage: _fixed_canary_args(
            stage,
            repo_root=repo_root,
            codex_bin=codex_bin,
            auth_file=auth_file,
            private_root=private_root,
        ),
        entry_validator=_validate_canary_bundle_entries,
        temp_parent=private_root,
    )


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise BootstrapError("invalid bootstrap arguments")


def main(argv: Sequence[str] | None = None) -> int:
    """Parse the fixed bootstrap boundary without echoing rejected argument values."""

    parser = _SafeArgumentParser(description=__doc__)
    parser.add_argument("--bundle-manifest", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--codex-bin", required=True)
    parser.add_argument("--auth-file")
    parser.add_argument("--private-root", required=True)
    parser.add_argument("--preflight", action="store_true")
    try:
        args = parser.parse_args(argv)
    except BootstrapError:
        print("codex-bootstrap: invalid arguments", file=sys.stderr)
        return CONTRACT_FAILURE_EXIT
    if args.preflight:
        if args.auth_file is not None:
            print("codex-bootstrap: invalid arguments", file=sys.stderr)
            return CONTRACT_FAILURE_EXIT
        return run_preflight_bootstrap(
            Path(args.bundle_manifest),
            args.expected_manifest_sha256,
            Path(args.source_root),
            repo_root=Path(args.repo_root),
            codex_bin=Path(args.codex_bin),
            private_root=Path(args.private_root),
        )
    if args.auth_file is None:
        print("codex-bootstrap: invalid arguments", file=sys.stderr)
        return CONTRACT_FAILURE_EXIT
    return run_canary_bootstrap(
        Path(args.bundle_manifest),
        args.expected_manifest_sha256,
        Path(args.source_root),
        repo_root=Path(args.repo_root),
        codex_bin=Path(args.codex_bin),
        auth_file=Path(args.auth_file),
        private_root=Path(args.private_root),
    )


if __name__ == "__main__":
    raise SystemExit(main())
