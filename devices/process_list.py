import ctypes
import ctypes.wintypes as wt


def list_processes():
    """列出当前运行的进程（进程名 + PID + 主窗口标题）

    用 Win32 Toolhelp32 快照直接枚举全部进程，快且不依赖 PowerShell。
    窗口标题为附加信息（有则显示，无则留空）。
    """
    return _enum_all_processes()


def _collect_window_titles():
    """建立 PID -> 主窗口标题 的映射（只取有标题的可见窗口）"""
    user32 = ctypes.windll.user32

    title_by_pid = {}

    def enum_proc(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)

        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        if pid.value and buf.value:
            title_by_pid[pid.value] = buf.value
        return True

    ENUM_PROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    user32.EnumWindows(ENUM_PROC(enum_proc), 0)

    return title_by_pid


def _enum_all_processes():
    """枚举全部进程（Toolhelp32），带窗口标题映射"""
    kernel32 = ctypes.windll.kernel32

    titles = _collect_window_titles()

    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wt.DWORD),
            ("cntUsage", wt.DWORD),
            ("th32ProcessID", wt.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(wt.ULONG)),
            ("th32ModuleID", wt.DWORD),
            ("cntThreads", wt.DWORD),
            ("th32ParentProcessID", wt.DWORD),
            ("pcPriClassBase", wt.LONG),
            ("dwFlags", wt.DWORD),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE_VALUE:
        return _fallback_processes()

    results = []

    try:
        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)

        if kernel32.Process32FirstW(snap, ctypes.byref(entry)):
            while True:
                pid = entry.th32ProcessID
                name = entry.szExeFile

                results.append({
                    "name": name,
                    "pid": pid,
                    "title": titles.get(pid, ""),
                })

                if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                    break
    finally:
        kernel32.CloseHandle(snap)

    if not results:
        return _fallback_processes()

    return results


def _fallback_processes():
    """兜底：用 tasklist 枚举进程名/PID（无窗口标题）"""
    import csv
    import io
    import subprocess

    processes = []

    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        for row in csv.reader(io.StringIO(result.stdout)):
            if len(row) >= 2:
                name = row[0].strip()

                try:
                    pid = int(row[1].strip())
                except ValueError:
                    pid = None

                processes.append({"name": name, "pid": pid, "title": ""})
    except Exception as e:
        print("[process_list] tasklist failed:", e)

    return processes


def process_exe_name(entry):
    """从进程项取可执行文件名（如 gta5.exe）"""
    name = entry.get("name", "")

    if not name:
        return ""

    if "." not in name:
        name = name + ".exe"

    return name.lower()
