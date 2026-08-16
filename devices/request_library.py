import json
import os
import urllib.request

from devices.remote_library import RemoteJsonLibrary


DEFAULT_LIBRARY_URL = (
    "https://raw.githubusercontent.com/nidoto/"
    "CapabilityNexus-Requests/master/index.json"
)

# 本地内置游戏库（随客户端分发，网络恢复前的离线来源）
_LOCAL_LIBRARY_SOURCE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tools",
    "game_library",
    "index.json",
)


def _local_library_path():
    """返回本地游戏库路径（兼容源码运行与打包 exe）。"""
    import sys as _sys

    candidates = []

    # 打包 exe：game_library 收集在 _internal/tools/game_library
    if getattr(_sys, "frozen", False):
        base = getattr(_sys, "_MEIPASS", os.path.dirname(_sys.executable))
        candidates.append(os.path.join(base, "tools", "game_library", "index.json"))
        exe_dir = os.path.dirname(_sys.executable)
        candidates.append(os.path.join(exe_dir, "tools", "game_library", "index.json"))

    candidates.append(_LOCAL_LIBRARY_SOURCE)

    for path in candidates:
        if os.path.exists(path):
            return path
    return _LOCAL_LIBRARY_SOURCE


LOCAL_LIBRARY_PATH = _local_library_path()

# 缓存路径：与 config_io 对齐（打包 exe 下基于 _MEIPASS 的绝对路径）
_PROJECT_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if getattr(__import__("sys"), "frozen", False):
    import sys as _sys
    _PROJECT_ROOT = getattr(_sys, "_MEIPASS", None) or os.path.dirname(_sys.executable)
DEFAULT_CACHE_PATH = os.path.join(_PROJECT_ROOT, "config", "request_library_cache.json")

# 可执行文件名匹配（忽略大小写、去空格）
def _norm(name):
    return (name or "").strip().lower()


class RequestLibrary(RemoteJsonLibrary):

    #
    # 反向需求库：
    # 收录各类程序/游戏的反向需求（如 GTA5 需要双震动、塞尔达需要陀螺仪）。
    # 索引在 GitHub（CapabilityNexus-Requests），按程序名/可执行文件名匹配。
    #
    # 用途：
    #   用户选择当前运行的程序（进程）→ 按 exe 名/程序名匹配库
    #   → 下载该程序的 requests.json → 客户端知道它需要哪些反向能力
    #

    DATA_KEY = "programs"
    LOG_PREFIX = "[RequestLibrary]"

    def __init__(self, library_url=None, cache_path=None):
        super().__init__(
            cache_path=cache_path or DEFAULT_CACHE_PATH,
            library_url=library_url or DEFAULT_LIBRARY_URL,
        )

    def refresh(self, allow_network=True):
        """加载索引：本地内置库优先，其次缓存，网络刷新可选（避免阻塞 GUI）"""
        # 本地内置游戏库（随客户端分发）
        if os.path.exists(LOCAL_LIBRARY_PATH):
            try:
                with open(LOCAL_LIBRARY_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._entries = data.get("programs", data.get("entries", []))
                print("[RequestLibrary] Loaded local library:", len(self._entries))
                return
            except Exception as e:
                print("[RequestLibrary] Local library read failed:", e)

        # 其余走基类：本地文件 → 缓存 → 网络
        super().refresh(allow_network=allow_network)

    def list_programs(self):
        if self._entries is None:
            self.refresh(allow_network=False)
        return self._entries or []

    def ensure_loaded(self):
        """确保索引已加载：缓存优先；无缓存时允许一次短网络刷新"""
        if self._entries is None:
            cached = self._load_cached()
            if cached:
                self._entries = cached.get("programs", cached.get("entries", []))
            else:
                self.refresh(allow_network=True)

    def search(self, query):
        if self._entries is None:
            self.refresh(allow_network=False)

        query = _norm(query)
        results = []

        for entry in self._entries:
            if self._match_query(entry, query):
                results.append(entry)

        return results

    def identify(self, process_name):
        """按可执行文件名 / 程序名匹配（仅缓存，不联网，避免阻塞）"""
        if self._entries is None:
            self.refresh(allow_network=False)

        proc = _norm(process_name)

        for entry in self._entries:
            executables = entry.get("executables", [])

            if not executables and entry.get("executable"):
                executables = [entry["executable"]]

            for exe in executables:
                if _norm(exe) == proc:
                    return entry

            name = _norm(entry.get("name"))
            entry_id = _norm(entry.get("id"))

            if proc and (proc == name or proc == entry_id):
                return entry

        return None

    def get_program(self, program_id):
        if self._entries is None:
            self.refresh(allow_network=False)

        for entry in self._entries:
            if entry.get("id") == program_id or entry.get("name") == program_id:
                return entry

        return None

    def _file_url(self, program_id, filename):
        # 本地内置游戏库优先
        if os.path.exists(LOCAL_LIBRARY_PATH):
            return os.path.join(
                os.path.dirname(LOCAL_LIBRARY_PATH),
                "programs",
                program_id,
                filename,
            )

        # 其余走基类（本地文件/网络 URL）
        return super()._file_url(program_id, filename, subdir="programs")

    def download(self, program_id):
        """下载并导入指定程序的反向需求配置"""
        entry = self.get_program(program_id)

        if entry is None:
            print("[RequestLibrary] Program not in library:", program_id)
            return None

        result = dict(entry)

        try:
            result["requests_data"] = self._fetch_file(
                self._file_url(program_id, "requests.json")
            )
        except Exception as e:
            print("[RequestLibrary] Requests download failed:", e)
            return None

        return result

    def _match_query(self, entry, query):
        if not query:
            return False

        fields = [
            entry.get("id"),
            entry.get("name"),
            entry.get("executable"),
            *(entry.get("executables", []) or []),
        ]

        return any(query in _norm(f) for f in fields if f)
