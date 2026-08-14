import json
import os
import urllib.request


DEFAULT_LIBRARY_URL = (
    "https://raw.githubusercontent.com/nidoto/"
    "CapabilityNexus-Requests/master/index.json"
)

DEFAULT_CACHE_PATH = os.path.join("config", "request_library_cache.json")

# 可执行文件名匹配（忽略大小写、去空格）
def _norm(name):
    return (name or "").strip().lower()


class RequestLibrary:

    #
    # 反向需求库：
    # 收录各类程序/游戏的反向需求（如 GTA5 需要双震动、塞尔达需要陀螺仪）。
    # 索引在 GitHub（CapabilityNexus-Requests），按程序名/可执行文件名匹配。
    #
    # 用途：
    #   用户选择当前运行的程序（进程）→ 按 exe 名/程序名匹配库
    #   → 下载该程序的 requests.json → 客户端知道它需要哪些反向能力
    #

    def __init__(self, library_url=None, cache_path=None):
        self.library_url = library_url or DEFAULT_LIBRARY_URL
        self.cache_path = cache_path or DEFAULT_CACHE_PATH
        self._entries = None

    def _load_cached(self):
        if not self.cache_path or not os.path.exists(self.cache_path):
            return None

        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("[RequestLibrary] Cache read failed:", e)
            return None

    def _save_cache(self, data):
        if not self.cache_path:
            return

        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("[RequestLibrary] Cache write failed:", e)

    def refresh(self, allow_network=True):
        """加载索引：缓存优先，网络刷新可选（避免阻塞 GUI）"""
        # 本地库文件
        if os.path.exists(self.library_url):
            try:
                with open(self.library_url, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._entries = data.get("programs", data.get("entries", []))
                self._save_cache(data)
                print("[RequestLibrary] Loaded local file:", len(self._entries))
                return
            except Exception as e:
                print("[RequestLibrary] Local file read failed:", e)

        # 缓存优先：有缓存就用缓存，不联网
        cached = self._load_cached()
        if cached:
            self._entries = cached.get("programs", cached.get("entries", []))
            print("[RequestLibrary] Used cache:", len(self._entries))

        # 需要网络时再尝试刷新（短超时）
        if allow_network:
            try:
                req = urllib.request.Request(
                    self.library_url,
                    headers={"User-Agent": "CapabilityNexus"},
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                self._entries = data.get("programs", data.get("entries", []))
                self._save_cache(data)
                print("[RequestLibrary] Refreshed from GitHub:", len(self._entries))
            except Exception as e:
                print("[RequestLibrary] GitHub refresh failed:", e)
                if self._entries is None:
                    self._entries = []

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
        if os.path.exists(self.library_url):
            return os.path.join(
                os.path.dirname(self.library_url),
                "programs",
                program_id,
                filename,
            )

        base = self.library_url.rsplit("/", 1)[0]
        return f"{base}/programs/{program_id}/{filename}"

    def _fetch_file(self, url):
        if url.startswith("http"):
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CapabilityNexus"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                return json.loads(resp.read().decode("utf-8"))

        if os.path.exists(url):
            with open(url, "r", encoding="utf-8") as f:
                return json.load(f)

        raise FileNotFoundError(url)

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

    def save_local(self, path):
        """导出索引到本地（供投稿 / 备份）"""
        if self._entries is None:
            self.refresh()

        with open(path, "w", encoding="utf-8") as f:
            json.dump({"programs": self._entries}, f, ensure_ascii=False, indent=2)
