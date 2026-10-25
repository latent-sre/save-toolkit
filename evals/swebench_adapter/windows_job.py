"""Private Windows Job Object ownership established before child execution."""

from __future__ import annotations

import ctypes
from typing import Any, ClassVar


class JobError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Windows process ownership unavailable")


class _BasicLimits(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, Any]]] = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class _IOCounters(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, Any]]] = [
        (name, ctypes.c_uint64)
        for name in (
            "ReadOperationCount",
            "WriteOperationCount",
            "OtherOperationCount",
            "ReadTransferCount",
            "WriteTransferCount",
            "OtherTransferCount",
        )
    ]


class _ExtendedLimits(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, Any]]] = [
        ("BasicLimitInformation", _BasicLimits),
        ("IoInfo", _IOCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _ThreadEntry(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, Any]]] = [
        ("dwSize", ctypes.c_uint32),
        ("cntUsage", ctypes.c_uint32),
        ("th32ThreadID", ctypes.c_uint32),
        ("th32OwnerProcessID", ctypes.c_uint32),
        ("tpBasePri", ctypes.c_int32),
        ("tpDeltaPri", ctypes.c_int32),
        ("dwFlags", ctypes.c_uint32),
    ]


def _signatures(kernel: Any) -> None:
    handle, dword, boolean = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int32
    signatures = {
        "CreateJobObjectW": (handle, [handle, ctypes.c_wchar_p]),
        "SetInformationJobObject": (boolean, [handle, ctypes.c_int32, handle, dword]),
        "OpenProcess": (handle, [dword, boolean, dword]),
        "AssignProcessToJobObject": (boolean, [handle, handle]),
        "CreateToolhelp32Snapshot": (handle, [dword, dword]),
        "Thread32First": (boolean, [handle, ctypes.POINTER(_ThreadEntry)]),
        "Thread32Next": (boolean, [handle, ctypes.POINTER(_ThreadEntry)]),
        "OpenThread": (handle, [dword, boolean, dword]),
        "ResumeThread": (dword, [handle]),
        "TerminateJobObject": (boolean, [handle, dword]),
        "CloseHandle": (boolean, [handle]),
        "GetLastError": (dword, []),
    }
    for name, (restype, argtypes) in signatures.items():
        function = getattr(kernel, name)
        function.restype = restype
        function.argtypes = argtypes


class WindowsJob:
    """Own a noninheritable kill-on-close job and resume only its suspended child."""

    def __init__(self, *, kernel: Any = None):
        self._kernel = kernel
        self._handle: Any = None
        self._clean = True
        try:
            if self._kernel is None:
                loader = getattr(ctypes, "WinDLL", None)
                if loader is None:
                    raise JobError
                self._kernel = loader("kernel32", use_last_error=True)
            _signatures(self._kernel)
            self._handle = self._kernel.CreateJobObjectW(None, None)
            if not self._handle:
                raise JobError
            limits = _ExtendedLimits()
            limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE; no breakaway flags
            if not self._kernel.SetInformationJobObject(self._handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                raise JobError
        except Exception:
            if self._handle:
                self._kernel.CloseHandle(self._handle)
                self._handle = None
            raise JobError from None

    def _primary_thread(self, pid: int) -> int:
        snapshot = self._kernel.CreateToolhelp32Snapshot(4, 0)  # SNAPTHREAD
        if not snapshot or snapshot == ctypes.c_void_p(-1).value:
            raise JobError
        threads = []
        try:
            entry = _ThreadEntry()
            entry.dwSize = ctypes.sizeof(entry)
            available = self._kernel.Thread32First(snapshot, ctypes.byref(entry))
            count = 0
            while available:
                count += 1
                if count > 100000 or entry.dwSize < 16:
                    raise JobError
                if entry.th32OwnerProcessID == pid:
                    threads.append(entry.th32ThreadID)
                entry.dwSize = ctypes.sizeof(entry)
                available = self._kernel.Thread32Next(snapshot, ctypes.byref(entry))
            if self._kernel.GetLastError() != 18 or len(threads) != 1:  # NO_MORE_FILES
                raise JobError
            return int(threads[0])
        finally:
            if not self._kernel.CloseHandle(snapshot):
                raise JobError

    def assign_and_resume(self, pid: int) -> None:
        process = self._kernel.OpenProcess(0x101, False, pid)  # SET_QUOTA | TERMINATE
        if not process:
            raise JobError
        try:
            if not self._kernel.AssignProcessToJobObject(self._handle, process):
                raise JobError
        finally:
            if not self._kernel.CloseHandle(process):
                raise JobError
        # Popen closes the primary thread handle, so enumerate the not-yet-run
        # child's single initial thread and reopen only SUSPEND_RESUME access.
        thread = self._kernel.OpenThread(2, False, self._primary_thread(pid))
        if not thread:
            raise JobError
        try:
            if self._kernel.ResumeThread(thread) != 1:
                raise JobError
        finally:
            if not self._kernel.CloseHandle(thread):
                raise JobError

    def close(self) -> bool:
        if self._handle is None:
            return self._clean
        # Keep job ownership after the root process exits. Closing its last
        # private handle is a second termination boundary for all descendants.
        terminated = bool(self._kernel.TerminateJobObject(self._handle, 1))
        closed = bool(self._kernel.CloseHandle(self._handle))
        self._clean = terminated and closed
        if closed:
            self._handle = None
        return self._clean
