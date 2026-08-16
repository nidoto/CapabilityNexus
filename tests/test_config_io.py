"""config_io 测试：配置读写、多游戏 profile、激活切换、本地目录。"""

import json
import os
import tempfile

from tools import config_io


def _write_profile(dir_path, name, data):
    path = os.path.join(dir_path, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return path


def test_load_profile_empty_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(config_io, "PROFILES_DIR", str(tmp_path))
    monkeypatch.setattr(config_io, "ACTIVE_PROFILE_PATH", str(tmp_path / "active.json"))
    monkeypatch.setattr(config_io, "BUILTIN_ROOT", str(tmp_path))

    assert config_io.load_profile() == {"mappings": {}}


def test_list_profiles(tmp_path, monkeypatch):
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    _write_profile(str(profiles_dir), "default", {"mappings": {}})
    _write_profile(str(profiles_dir), "cyberpunk2077", {"mappings": {}})

    local_dir = profiles_dir / "local"
    local_dir.mkdir()
    _write_profile(str(local_dir), "custom", {"mappings": {}})

    monkeypatch.setattr(config_io, "PROFILES_DIR", str(profiles_dir))
    monkeypatch.setattr(config_io, "ACTIVE_PROFILE_PATH", str(tmp_path / "active.json"))

    names = config_io.list_profiles()
    assert "default" in names
    assert "cyberpunk2077" in names
    assert "custom" in names


def test_active_profile_roundtrip(tmp_path, monkeypatch):
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    _write_profile(str(profiles_dir), "default", {"mappings": {}})
    _write_profile(str(profiles_dir), "cyberpunk2077", {"mappings": {}})

    active_path = tmp_path / "active.json"
    monkeypatch.setattr(config_io, "PROFILES_DIR", str(profiles_dir))
    monkeypatch.setattr(config_io, "ACTIVE_PROFILE_PATH", str(active_path))

    assert config_io.get_active_profile() == "default"

    assert config_io.set_active_profile("cyberpunk2077") is True
    assert config_io.get_active_profile() == "cyberpunk2077"


def test_set_active_profile_invalid(tmp_path, monkeypatch):
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    _write_profile(str(profiles_dir), "default", {"mappings": {}})

    monkeypatch.setattr(config_io, "PROFILES_DIR", str(profiles_dir))
    monkeypatch.setattr(config_io, "ACTIVE_PROFILE_PATH", str(tmp_path / "active.json"))

    assert config_io.set_active_profile("not_exist") is False


def test_local_profile_takes_priority(tmp_path, monkeypatch):
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    local_dir = profiles_dir / "local"
    local_dir.mkdir()

    # 根目录与 local 都有同名配置
    _write_profile(str(profiles_dir), "game", {"mappings": {"a": "x"}})
    _write_profile(str(local_dir), "game", {"mappings": {"a": "y"}})

    monkeypatch.setattr(config_io, "PROFILES_DIR", str(profiles_dir))
    monkeypatch.setattr(config_io, "ACTIVE_PROFILE_PATH", str(tmp_path / "active.json"))

    loaded = config_io.load_profile_named("game")
    assert loaded["mappings"]["a"] == "y"


def test_save_profile_named_roundtrip(tmp_path, monkeypatch):
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()

    monkeypatch.setattr(config_io, "PROFILES_DIR", str(profiles_dir))
    monkeypatch.setattr(config_io, "ACTIVE_PROFILE_PATH", str(tmp_path / "active.json"))

    config_io.save_profile_named("testgame", {"mappings": {"src": "target"}})
    assert os.path.exists(os.path.join(str(profiles_dir), "local", "testgame.json"))

    loaded = config_io.load_profile_named("testgame")
    assert loaded["mappings"]["src"] == "target"
