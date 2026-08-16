"""设备延时评估：按连接/方案类型估计输入延时，用于设备树颜色标记。

色标（统一）：
  绿色 = 低延时（≤40ms，可畅玩）
  黄色 = 中延时（41~80ms，一般）
  红色 = 高延时（>80ms，可能卡顿）

对无法直接测量的方案（手机 Web、蓝牙等），给出估算值。
"""

LOW = "low"
MEDIUM = "medium"
HIGH = "high"

# 阈值（ms）
GREEN_MAX = 40
YELLOW_MAX = 80

# 按连接类型 / 方案的延时估算（ms）
ESTIMATES = {
    # 本地直连（XInput 物理手柄、串口直连）
    "xinput": 5,
    "serial": 10,
    "hid": 10,
    # 局域网 / Web
    "websocket": 60,
    "phone_web_wheel": 60,
    "phone_web_pad": 40,
    # 蓝牙
    "bluetooth": 30,
    "ftms": 30,
    # 默认
    "default": 50,
}


def estimate_ms(connection_type, scheme=None):
    """估算延时（ms）。scheme 为方案 id（如 phone_web_wheel）时优先。"""
    if scheme:
        key = scheme
        if key in ESTIMATES:
            return ESTIMATES[key]
    if connection_type in ESTIMATES:
        return ESTIMATES[connection_type]
    return ESTIMATES["default"]


def level_for(ms):
    """按延时 ms 返回等级：low / medium / high。"""
    if ms <= GREEN_MAX:
        return LOW
    if ms <= YELLOW_MAX:
        return MEDIUM
    return HIGH


def label_for(level):
    return {
        LOW: "低延时",
        MEDIUM: "中延时",
        HIGH: "高延时",
    }.get(level, "?")


def color_for(level):
    """等级 → 颜色（GUI 用）。"""
    return {
        LOW: "#4ade80",   # 绿
        MEDIUM: "#facc15",  # 黄
        HIGH: "#f87171",   # 红
    }.get(level, "#94a3b8")


def describe(connection_type, scheme=None):
    """返回 (ms, level, label, color)。"""
    ms = estimate_ms(connection_type, scheme)
    level = level_for(ms)
    return ms, level, label_for(level), color_for(level)
