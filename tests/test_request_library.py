"""RequestLibrary 测试：本地游戏库加载 / 进程匹配 / 下载请求配置。"""

import os

from devices.request_library import RequestLibrary

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_LIBRARY = os.path.join(PROJECT_ROOT, "tools", "game_library", "index.json")


def _local_library():
    assert os.path.exists(LOCAL_LIBRARY), "local game library missing"
    return RequestLibrary(library_url=LOCAL_LIBRARY)


def test_local_library_exists():
    _local_library()


def test_load_index():
    lib = _local_library()
    lib.refresh(allow_network=False)
    ids = [p["id"] for p in lib.list_programs()]
    assert "gta5" in ids


def test_identify_by_executable():
    lib = _local_library()
    lib.refresh(allow_network=False)

    assert lib.identify("gta5.exe") is not None
    assert lib.identify("GTA5.exe") is not None
    assert lib.identify("unknown.exe") is None


def test_download_requests():
    lib = _local_library()
    lib.refresh(allow_network=False)

    data = lib.download("gta5")
    assert data is not None

    requests = data["requests_data"]["requests"]
    assert "xbox.motor_left" in requests
    assert "xbox.motor_right" in requests


def test_get_program():
    lib = _local_library()
    lib.refresh(allow_network=False)

    entry = lib.get_program("gta5")
    assert entry is not None
    assert entry["name"] == "Grand Theft Auto V"
