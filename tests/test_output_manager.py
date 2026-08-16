"""OutputDeviceManager 测试：配置加载、增删、运行时实例管理。"""

import os

from output.manager import OutputDeviceManager


def _write_outputs(path, outputs):
    import json

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"outputs": outputs}, f, ensure_ascii=False, indent=2)


def test_load_returns_config(tmp_path):
    path = os.path.join(str(tmp_path), "outputs.json")
    _write_outputs(path, [{"id": "virtual_xinput", "type": "xinput", "name": "pad"}])

    mgr = OutputDeviceManager(config_path=path)
    mgr.load()

    assert len(mgr.outputs) == 1
    assert mgr.outputs[0]["id"] == "virtual_xinput"
    assert mgr.get_config("virtual_xinput")["type"] == "xinput"


def test_load_missing_file_empty(tmp_path):
    path = os.path.join(str(tmp_path), "outputs.json")
    mgr = OutputDeviceManager(config_path=path)
    assert mgr.load() == []


def test_add_and_remove(tmp_path):
    path = os.path.join(str(tmp_path), "outputs.json")
    mgr = OutputDeviceManager(config_path=path)
    mgr.load()

    mgr.add("virtual_xinput", "xinput", "pad")
    assert mgr.get_config("virtual_xinput") is not None

    mgr.remove("virtual_xinput")
    assert mgr.get_config("virtual_xinput") is None
    assert os.path.exists(path)  # 持久化


def test_remove_unknown_no_error(tmp_path):
    path = os.path.join(str(tmp_path), "outputs.json")
    mgr = OutputDeviceManager(config_path=path)
    mgr.load()
    assert mgr.remove("no_such") is None


def test_build_all_skips_unknown_type(tmp_path):
    path = os.path.join(str(tmp_path), "outputs.json")
    _write_outputs(path, [
        {"id": "bad", "type": "no_such_type"},
    ])

    mgr = OutputDeviceManager(config_path=path)
    mgr.load()
    instances = mgr.build_all()

    assert instances == {}
