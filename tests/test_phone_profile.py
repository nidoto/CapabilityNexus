"""手机配置存储测试：按 device_id 保存/加载、跨设备隔离、旧格式迁移。"""

import json
import os

from devices.websocket_connection import PhoneProfileStore


def test_save_and_load_by_device_id(tmp_path):
    store = PhoneProfileStore(directory=str(tmp_path))
    cfg = {"invert": {"steer": True}, "wheel_max_angle": 90, "gas_gain": 2.0}

    assert store.save("dev-abc-123", cfg) is True

    files = store.list_profiles()
    assert len(files) == 1
    assert files[0] == "dev-abc-123.json"

    loaded = store.load("dev-abc-123")
    assert loaded["wheel_max_angle"] == 90
    assert loaded["gas_gain"] == 2.0
    assert loaded["invert"]["steer"] is True


def test_profile_isolation_per_device(tmp_path):
    store = PhoneProfileStore(directory=str(tmp_path))
    store.save("dev-aaa", {"gas_gain": 1.0})
    store.save("dev-bbb", {"gas_gain": 3.0})

    assert store.load("dev-aaa")["gas_gain"] == 1.0
    assert store.load("dev-bbb")["gas_gain"] == 3.0
    # 不存在的设备返回空
    assert store.load("dev-ccc") == {}


def test_missing_profile_returns_empty(tmp_path):
    store = PhoneProfileStore(directory=str(tmp_path))
    assert store.load("no-such-device") == {}
    assert store.list_profiles() == []


def test_filename_is_device_id(tmp_path, monkeypatch):
    monkeypatch.setenv("USERNAME", "Alice")
    store = PhoneProfileStore(directory=str(tmp_path))
    store.save("dev-galaxy", {"gas_gain": 1.0})

    names = os.listdir(str(tmp_path))
    assert any(n == "dev-galaxy.json" for n in names)
    # 不再包含用户名前缀
    assert not any("Alice" in n for n in names)


def test_bad_json_returns_empty(tmp_path):
    store = PhoneProfileStore(directory=str(tmp_path))
    path = os.path.join(str(tmp_path), "x.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write("{not valid json")
    # 损坏内容不会让 load 崩溃，返回空 dict
    store.save("dev-phone", {"a": 1})
    for name in os.listdir(str(tmp_path)):
        if name.endswith(".json") and name != "x.json":
            os.remove(os.path.join(str(tmp_path), name))
    assert store.load("dev-phone") == {}


def test_migrate_legacy_by_name(tmp_path):
    """旧格式 <*>-<手机名>.json 应被复制为新格式 <device_id>.json。"""
    store = PhoneProfileStore(directory=str(tmp_path))
    # 模拟旧文件（名中含用户名，仅作兼容来源）
    legacy = os.path.join(str(tmp_path), "Alice-Xiaomi_Redmi.json")
    with open(legacy, "w", encoding="utf-8") as f:
        json.dump({"gas_gain": 1.5}, f)

    # 迁移前新文件不存在
    assert store.load("dev-new") == {}
    # 按手机显示名 "Xiaomi Redmi" 找到旧文件并迁移
    assert store.migrate_legacy("dev-new", "Xiaomi Redmi") is True
    # 旧文件保留（不删除）
    assert os.path.exists(legacy)
    # 新文件已可用且内容为旧配置
    assert store.load("dev-new") == {"gas_gain": 1.5}
    # 已迁移则不再重复迁移
    assert store.migrate_legacy("dev-new", "Xiaomi Redmi") is False


def test_migrate_legacy_no_match(tmp_path):
    store = PhoneProfileStore(directory=str(tmp_path))
    assert store.migrate_legacy("dev-x", "Unknown Phone") is False
