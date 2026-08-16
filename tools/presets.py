"""手机 Web 预设：一键应用"输入设备 → 能力 → 客户端 → X360 兼容输出"整体方案。

预设定义在 config/phone_presets.json（interface=web）。
应用预设会：
  1. 确保输入设备（phone web 连接）存在于 config/devices.json
  2. 把预设 mappings 合并进当前激活的游戏配置
  3. 把预设 processors 合并进 config/processors.json
  4. 确保 X360 兼容输出设备启用
返回动作列表（如 start_web），由调用方执行。
"""

import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRESETS_PATH = os.path.join(PROJECT_ROOT, "config", "phone_presets.json")
PROCESSORS_PATH = os.path.join(PROJECT_ROOT, "config", "processors.json")


def load_presets():
    """返回预设列表（含 interface 标识）。"""
    try:
        if os.path.exists(PRESETS_PATH):
            with open(PRESETS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            presets = data.get("presets", [])
            if isinstance(presets, list):
                return presets
    except (OSError, json.JSONDecodeError) as error:
        print("[Presets] Failed to load:", error)
    return []


def get_preset(preset_id):
    for preset in load_presets():
        if preset.get("id") == preset_id:
            return preset
    return None


def _ensure_device(device_cfg, preset_id=None):
    """确保输入设备配置存在（记录方案 id 用于延时评估）。返回是否新增。"""
    from tools.config_io import load_config
    from tools.config_io import save_config

    config = load_config()
    devices = config.get("devices", [])

    driver = device_cfg.get("driver")
    port = (device_cfg.get("connection") or {}).get("port")
    for dev in devices:
        if dev.get("driver") == driver and (dev.get("connection") or {}).get("port") == port:
            # 已存在：更新方案 id（用于设备树延时评估）
            if preset_id and dev.get("preset_id") != preset_id:
                dev["preset_id"] = preset_id
                save_config(config)
            return False

    entry = dict(device_cfg)
    if preset_id:
        entry["preset_id"] = preset_id
    devices.append(entry)
    config["devices"] = devices
    save_config(config)
    return True


def _ensure_output(output_id="virtual_xinput"):
    """确保 X360 兼容输出设备启用。返回是否新增。"""
    from tools.config_io import load_outputs
    from tools.config_io import save_outputs

    data = load_outputs()
    outputs = data.get("outputs", [])
    for out in outputs:
        if out.get("id") == output_id:
            return False

    outputs.append({
        "id": output_id,
        "type": "xinput",
        "name": "XInput-compatible Controller",
    })
    data["outputs"] = outputs
    save_outputs(data)
    return True


def apply_preset(preset_id, game=None):
    """应用预设到指定游戏配置。

    game: 游戏 id（如 "rushrally3"）。应用时：
      1. 查游戏能力配置（tools/game_library/programs/<game>/capabilities.json）
      2. 根据游戏支持的模式决定是否降级（如不支持方向盘 → X360 兼容手柄）
      3. 把预设 mappings/processors 合并进 profiles/local/<game>.json 并激活
      4. 确保输入设备 + 输出设备，返回未满足的反向能力提醒

    返回 (ok, message, actions, unmet)：
      actions: ["start_web", ...]
      unmet:  [("rumble", "detail"), ...] 游戏需要但方案未提供的能力
    """
    from tools.config_io import load_profile_named
    from tools.config_io import save_profile_named
    from tools.config_io import set_active_profile
    from tools.game_capabilities import latency_warning
    from tools.game_capabilities import resolve_mode
    from tools.game_capabilities import unmet_reverse_capabilities

    preset = get_preset(preset_id)
    if not preset:
        return False, f"未找到预设: {preset_id}", [], []

    profile_name = game or preset.get("profile_name") or preset.get("id")
    mode = preset.get("mode", "pad")

    # 0. 按游戏能力决定实际模式（可能降级）+ 延时匹配
    warnings = []
    if game:
        resolved, msg = resolve_mode(game, mode)
        if msg:
            warnings.append(msg)
        if resolved != mode:
            # 降级：方向盘 → X360 兼容手柄（左摇杆转向）
            mode = resolved
            if resolved == "x360_pad":
                preset = _adapt_wheel_to_pad(preset)

        # 延时匹配：游戏对延时敏感 vs 方案实际延时
        preset_latency = preset.get("latency_ms")
        if preset_latency:
            ok_latency, latency_msg = latency_warning(game, preset_latency)
            if not ok_latency:
                warnings.append(latency_msg)

    # 1. 输入设备（记录方案 id 用于设备树延时评估）
    if preset.get("device"):
        _ensure_device(preset["device"], preset_id=preset.get("id"))

    # 2. 合并 mappings/processors 到游戏 profile
    existing = load_profile_named(profile_name)
    mappings = existing.get("mappings", {})
    mappings.update(preset.get("mappings", {}))
    processors = existing.get("processors", {})
    processors.update(preset.get("processors", {}))
    profile = {"mappings": mappings, "processors": processors}
    save_profile_named(profile_name, profile)

    # 3. 处理器：合并到全局配置（保证引擎按能力处理）
    try:
        with open(PROCESSORS_PATH, "r", encoding="utf-8") as f:
            processors_data = json.load(f)
    except (OSError, json.JSONDecodeError):
        processors_data = {"processors": {}}
    processors = processors_data.setdefault("processors", {})
    processors.update(preset.get("processors", {}))
    try:
        os.makedirs(os.path.dirname(PROCESSORS_PATH), exist_ok=True)
        with open(PROCESSORS_PATH, "w", encoding="utf-8") as f:
            json.dump(processors_data, f, ensure_ascii=False, indent=2)
    except OSError as error:
        return False, f"保存处理器配置失败: {error}", [], []

    # 4. 输出设备
    output_id = preset.get("output") or "virtual_xinput"
    _ensure_output(output_id)

    # 5. 激活该游戏配置
    set_active_profile(profile_name)

    # 6. 需要启动的动作
    actions = []
    if preset.get("start_web"):
        actions.append("start_web")

    # 7. 未满足的反向能力（游戏需要但方案没有）
    unmet = []
    if game:
        unmet = unmet_reverse_capabilities(game, preset.get("capabilities", []))

    message = f"已应用方案 [{preset.get('name')}] → 配置 [{profile_name}]"
    if warnings:
        message += " | " + " | ".join(warnings)

    return True, message, actions, unmet


def _adapt_wheel_to_pad(preset):
    """把"方向盘"方案降级为 X360 兼容手柄（方向盘→左摇杆转向，其余不变）。"""
    adapted = dict(preset)
    mappings = dict(preset.get("mappings", {}))
    # 方向盘 roll → 左摇杆 X（赛车标准转向）
    if "phone.roll" in mappings:
        mappings["phone.roll"] = "left_x"
    adapted["mappings"] = mappings
    adapted["mode"] = "pad"
    return adapted


def describe(preset):
    """生成预设的可读描述。"""
    name = preset.get("name", preset.get("id", "?"))
    desc = preset.get("description", "")
    mode = preset.get("mode", "")
    caps = preset.get("capabilities", [])
    lines = [name]
    if desc:
        lines.append(f"  {desc}")
    if mode:
        lines.append(f"  模式: {mode}")
    if caps:
        lines.append(f"  能力: {', '.join(caps)}")
    return "\n".join(lines)
