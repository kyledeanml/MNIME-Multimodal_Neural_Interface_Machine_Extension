import ctypes
import gc
import sys
from ctypes import wintypes

class _PPTS(ctypes.Structure):
    _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG),
                ("StateMask", wintypes.ULONG)]

ProcessMemoryPriority = 0
ProcessPowerThrottling = 4
THROTTLE_EXECUTION_SPEED = 0x1
IDLE_PRIORITY_CLASS = 0x40
NORMAL_PRIORITY_CLASS = 0x20
MEMORY_PRIORITY_LOW = 2
MEMORY_PRIORITY_NORMAL = 5

def _k32():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.SetProcessWorkingSetSizeEx.argtypes = [wintypes.HANDLE, ctypes.c_size_t,
                                             ctypes.c_size_t, wintypes.DWORD]
    k.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                        ctypes.c_void_p, wintypes.DWORD]
    k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    return k

def trim_now():
    gc.collect()
    try:
        import pymupdf
        pymupdf.TOOLS.store_shrink(100)
    except Exception:
        pass
    try:
        from PyQt6.QtGui import QPixmapCache
        QPixmapCache.clear()
    except Exception:
        pass
    if sys.platform != "win32":
        return
    try:
        ctypes.CDLL("ucrtbase")._heapmin()
    except Exception:
        pass
    try:
        k = _k32()
        k.SetProcessWorkingSetSizeEx(k.GetCurrentProcess(), ctypes.c_size_t(-1).value,
                                     ctypes.c_size_t(-1).value, 0)
    except Exception:
        pass

def set_efficiency_mode(on: bool):
    if sys.platform != "win32":
        return
    try:
        k = _k32()
        h = k.GetCurrentProcess()
        st = _PPTS(1, THROTTLE_EXECUTION_SPEED, THROTTLE_EXECUTION_SPEED if on else 0)
        k.SetProcessInformation(h, ProcessPowerThrottling, ctypes.byref(st), ctypes.sizeof(st))
        mp = wintypes.ULONG(MEMORY_PRIORITY_LOW if on else MEMORY_PRIORITY_NORMAL)
        k.SetProcessInformation(h, ProcessMemoryPriority, ctypes.byref(mp), ctypes.sizeof(mp))
        k.SetPriorityClass(h, IDLE_PRIORITY_CLASS if on else NORMAL_PRIORITY_CLASS)
    except Exception:
        pass
