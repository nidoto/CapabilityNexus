"""游戏能力配置：记录每个游戏支持的模式与反向输出能力。

游戏配置文件位于 tools/game_library/programs/<game>/capabilities.json：
  - supported_modes: ["x360_pad" | "keyboard_mouse" | "wheel", ...]
  - reverse_capabilities: { "rumble": {"supported": bool, "detail": str}, ... }

用途：用户选择"方案 + 游戏"后，根据游戏能力自动决定模拟方式
（如游戏不支持方向盘 → 降级为 X360 兼容手柄），并提醒未满足的能力。
"""

import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_LIB_DIR = os.path.join(PROJECT_ROOT, "tools", "game_library", "programs")

# 方案模式 → 是否要求游戏支持"方向盘/陀螺仪"
MODE_REQUIRES_GYRO = {
    "wheel": True,
    "pad": False,
}


def list_games():
    """返回有能力配置的游戏 id 列表。"""
    if not os.path.isdir(GAME_LIB_DIR):
        return []
    return sorted(
        name for name in os.listdir(GAME_LIB_DIR)
        if os.path.isfile(os.path.join(GAME_LIB_DIR, name, "capabilities.json"))
    )


def load_game_capabilities(game_id):
    """读取游戏能力配置。没有则返回 None。"""
    if not game_id:
        return None
    path = os.path.join(GAME_LIB_DIR, game_id, "capabilities.json")
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except (OSError, json.JSONDecodeError) as error:
        print(f"[GameCaps] Failed to load {game_id}: {error}")
    return None


def mode_supported(game_id, mode):
    """游戏是否支持该输入模式。"""
    caps = load_game_capabilities(game_id)
    if caps is None:
        # 无能力配置时不做限制
        return True
    supported = caps.get("supported_modes") or []
    return mode in supported


def resolve_mode(game_id, desired_mode):
    """根据游戏能力决定最终模拟模式。

    返回 (mode, message)：
      mode:   实际使用的模式（可能降级）
      message: 说明/警告。
    """
    caps = load_game_capabilities(game_id)
    if caps is None:
        return desired_mode, ""

    supported = caps.get("supported_modes") or []
    notes = caps.get("notes", "")

    if desired_mode in supported:
        msg = notes
        return desired_mode, msg

    # 期望模式不受支持 → 降级
    if desired_mode == "wheel":
        if "x360_pad" in supported:
            return "x360_pad", (
                f"游戏 {caps.get('name', game_id)} 不支持方向盘，"
                f"已降级为 X360 兼容手柄。{notes}".strip()
            )
        if "keyboard_mouse" in supported:
            return "keyboard_mouse", (
                f"游戏 {caps.get('name', game_id)} 不支持方向盘，"
                f"已降级为键鼠模拟。{notes}".strip()
            )
        return desired_mode, f"游戏能力未知，按 {desired_mode} 尝试。{notes}".strip()

    return desired_mode, notes


def unmet_reverse_capabilities(game_id, available_capabilities):
    """返回游戏中需要、但当前方案未提供的能力列表。

    available_capabilities: 当前方案提供的能力（如 ["vibration"]）。
    返回 [("rumble", "游戏需要震动但方案未提供"), ...]
    """
    caps = load_game_capabilities(game_id)
    if caps is None:
        return []
    rev = caps.get("reverse_capabilities") or {}
    unmet = []
    for name, info in rev.items():
        supported = info.get("supported", False) if isinstance(info, dict) else bool(info)
        if supported and name not in available_capabilities:
            detail = info.get("detail", "") if isinstance(info, dict) else ""
            unmet.append((name, detail))
    return unmet


# 延时敏感度阈值（ms）
LATENCY_BUDGET = {
    "low": 100,
    "medium": 50,
    "high": 30,
}


def latency_warning(game_id, preset_latency_ms):
    """评估方案延时是否满足游戏延时要求。

    返回 (ok, message)：
      ok:      True 表示满足/无风险；False 表示可能不满足，需提醒。
      message: 说明文字（无风险时可为空）。
    """
    caps = load_game_capabilities(game_id)
    if caps is None or not preset_latency_ms:
        return True, ""

    req = caps.get("latency_requirement")
    if req not in LATENCY_BUDGET:
        return True, ""

    budget = LATENCY_BUDGET[req]
    note = caps.get("latency_note", "")
    if preset_latency_ms <= budget:
        return True, ""

    return False, (
        f"该游戏对输入延时要求{req}（预算约 {budget}ms），"
        f"当前方案延时约 {preset_latency_ms}ms，可能无法畅玩。{note}"
    ).strip()
