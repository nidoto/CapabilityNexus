"""远程 JSON 库共享基类：缓存读写 + 文件/网络拉取。

DeviceLibrary 与 RequestLibrary 共用：远程索引（GitHub）+ 本地缓存 +
按 id 拉取子文件。子类只需提供数据键（devices/programs）与匹配逻辑。
"""

import json
import os
import urllib.request


class RemoteJsonLibrary:
    """带本地缓存与网络回退的远程 JSON 库基类。"""

    # 索引数据键：子类覆盖（如 "devices" / "programs"）
    DATA_KEY = "items"
    LOG_PREFIX = "[RemoteLibrary]"

    def __init__(self, cache_path=None, library_url=None):
        self.library_url = library_url
        self.cache_path = cache_path
        self._entries = None

    def _load_cached(self):
        if not self.cache_path or not os.path.exists(self.cache_path):
            return None
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as error:
            print(f"{self.LOG_PREFIX} Cache read failed: {error}")
            return None

    def _save_cache(self, data):
        if not self.cache_path:
            return
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as error:
            print(f"{self.LOG_PREFIX} Cache write failed: {error}")

    def _fetch_file(self, url):
        if url.startswith("http"):
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CapabilityNexus"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        if os.path.exists(url):
            with open(url, "r", encoding="utf-8") as f:
                return json.load(f)
        raise FileNotFoundError(url)

    def _file_url(self, entry_id, filename, subdir):
        """远程/本地子文件 URL。subdir 如 'devices' 或 'programs'。"""
        if os.path.exists(self.library_url):
            return os.path.join(
                os.path.dirname(self.library_url),
                subdir,
                entry_id,
                filename,
            )
        base = self.library_url.rsplit("/", 1)[0]
        return f"{base}/{subdir}/{entry_id}/{filename}"

    def _refresh_from(self, source_path_or_url, timeout=10):
        """从本地路径或网络 URL 加载索引 JSON，返回 entries 或 None。"""
        try:
            if source_path_or_url.startswith("http"):
                req = urllib.request.Request(
                    source_path_or_url,
                    headers={"User-Agent": "CapabilityNexus"},
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            else:
                with open(source_path_or_url, "r", encoding="utf-8") as f:
                    data = json.load(f)
            entries = data.get(self.DATA_KEY, [])
            return entries
        except Exception as error:
            print(f"{self.LOG_PREFIX} Load failed: {error}")
            return None

    def refresh(self, allow_network=True):
        """加载索引：本地文件优先，其次缓存，网络可选。"""
        # 1) 本地索引文件（随客户端分发）
        if self.library_url and not self.library_url.startswith("http"):
            entries = self._refresh_from(self.library_url)
            if entries is not None:
                self._entries = entries
                print(f"{self.LOG_PREFIX} Loaded local file: {len(entries)}")
                return

        # 2) 缓存优先（不联网）
        cached = self._load_cached()
        if cached:
            self._entries = cached.get(self.DATA_KEY, [])
            print(f"{self.LOG_PREFIX} Used cache: {len(self._entries)}")
            return

        # 3) 网络刷新
        if allow_network and self.library_url and self.library_url.startswith("http"):
            entries = self._refresh_from(self.library_url)
            if entries is not None:
                self._entries = entries
                self._save_cache({self.DATA_KEY: entries})
                print(f"{self.LOG_PREFIX} Refreshed from network: {len(entries)}")
                return

        self._entries = self._entries or []

    def entries(self):
        if self._entries is None:
            self.refresh(allow_network=False)
        return self._entries or []

    def get(self, entry_id):
        for entry in self.entries():
            if entry.get("id") == entry_id or entry.get("name") == entry_id:
                return entry
        return None
