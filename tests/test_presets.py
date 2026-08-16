"""手机 Web 预设测试：加载、应用、游戏能力联动、降级、延时。"""

import json
import os

from tools.presets import apply_preset
from tools.presets import get_preset
from tools.presets import load_presets


def test_presets_file_exists_and_loads():
    presets = load_presets()
    assert len(presets) >= 2
    ids = {p["id"] for p in presets}
    assert "phone_web_wheel" in ids
    assert "phone_pad" in ids


def test_web_interface_flag():
    presets = load_presets()
    for p in presets:
        assert p.get("mode") in ("wheel", "pad")
        assert p.get("capabilities")


def test_phone_wheel_has_axes_and_vibration():
    preset = get_preset("phone_web_wheel")
    assert preset is not None
    mappings = preset["mappings"]
    # 手机方向盘 → 左摇杆 X（赛车转向标准）
    assert mappings["phone.roll"] == "left_x"
    assert mappings["phone.gas"] == "right_trigger"
    assert mappings["phone.brake"] == "left_trigger"
    caps = preset["capabilities"]
    assert "gyroscope" in caps
    assert "vibration" in caps


def test_phone_pad_has_buttons():
    preset = get_preset("phone_pad")
    assert preset is not None
    mappings = preset["mappings"]
    assert mappings["phone.button_a"] == "button_a"
    assert mappings["phone.dpad_up"] == "button_dpad_up"


def _isolate(tmp_path, monkeypatch):
    """隔离配置文件路径，避免污染真实 config。"""
    from tools import presets as mod
    import tools.config_io as cio

    cio.PROFILES_DIR = os.path.join(str(tmp_path), "profiles")
    cio.PROFILE_PATH = os.path.join(cio.PROFILES_DIR, "default.json")
    cio.ACTIVE_PROFILE_PATH = os.path.join(str(tmp_path), "active.json")
    os.makedirs(cio.PROFILES_DIR, exist_ok=True)
    cio._save_json(cio.PROFILE_PATH, {"mappings": {}})
    cio._save_json(cio.ACTIVE_PROFILE_PATH, {"profile": "default"})

    mod.PROCESSORS_PATH = os.path.join(str(tmp_path), "processors.json")
    with open(mod.PROCESSORS_PATH, "w", encoding="utf-8") as f:
        json.dump({"processors": {}}, f)

    monkeypatch.setattr(mod, "_ensure_device", lambda cfg, preset_id=None: False)
    monkeypatch.setattr(mod, "_ensure_output", lambda out_id="virtual_xinput": False)
    return mod


def test_apply_preset_to_game(tmp_path, monkeypatch):
    """应用预设到指定游戏：合并 mappings/processors 并激活。"""
    _isolate(tmp_path, monkeypatch)
    import tools.config_io as cio
    from tools.config_io import load_profile_named

    ok, _msg, _actions, _unmet = apply_preset("phone_web_wheel", game="mytestgame")
    assert ok is True
    assert cio.get_active_profile() == "mytestgame"

    profile = load_profile_named("mytestgame")
    assert profile["mappings"]["phone.roll"] == "left_x"


def test_apply_preset_returns_start_web_action(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    ok, _msg, actions, _unmet = apply_preset("phone_web_wheel")
    assert ok is True
    assert "start_web" in actions


def test_wheel_preset_degrades_to_pad_for_unsupported_game(tmp_path, monkeypatch):
    """Rush Rally 3 不支持方向盘 → 自动降级为 X360 手柄（左摇杆转向）。"""
    _isolate(tmp_path, monkeypatch)
    from tools.config_io import load_profile_named

    ok, msg, _actions, _unmet = apply_preset("phone_web_wheel", game="rushrally3")
    assert ok is True
    assert "X360" in msg or "手柄" in msg

    profile = load_profile_named("rushrally3")
    # 方向盘 → 左摇杆转向
    assert profile["mappings"]["phone.roll"] == "left_x"
    # 无 pitch 注入
    assert "phone.pitch" not in profile["mappings"]


def test_latency_warning_high_sensitivity_game():
    """Rush Rally 3 对延时敏感：高延时方案应收到风险提醒。"""
    from tools.game_capabilities import latency_warning

    ok, msg = latency_warning("rushrally3", 60)
    assert ok is False
    assert "延时" in msg

    ok, msg = latency_warning("rushrally3", 20)
    assert ok is True
    assert msg == ""


def test_apply_wheel_to_rushrally3_warns_latency(tmp_path, monkeypatch):
    """应用手机方向盘到 Rush Rally 3：降级 + 延时提醒。"""
    _isolate(tmp_path, monkeypatch)

    ok, msg, _actions, _unmet = apply_preset("phone_web_wheel", game="rushrally3")
    assert ok is True
    assert "延时" in msg
    assert "X360" in msg or "手柄" in msg


def test_latency_levels_and_colors():
    from tools.latency import color_for
    from tools.latency import level_for

    assert level_for(20) == "low"
    assert level_for(50) == "medium"
    assert level_for(100) == "high"
    # 红=高延时，黄=中，绿=低
    assert color_for("low") == "#4ade80"
    assert color_for("medium") == "#facc15"
    assert color_for("high") == "#f87171"
