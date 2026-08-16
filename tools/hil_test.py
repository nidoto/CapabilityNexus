"""CapabilityNexus 硬件在环（HIL）测试。

连接真实硬件验证完整数据链路：
  1. ESP32（COM3 串口）→ 固件数据流（FRAME / X / Y）
  2. XInput 手柄 → 按键 / 摇杆状态
  3. 引擎：输入能力 → 处理器 → 映射 → X360 兼容输出

用法：
    py -3 tools/hil_test.py              # 自动检测并测试可用的硬件
    py -3 tools/hil_test.py --esp32      # 只测 ESP32
    py -3 tools/hil_test.py --xinput     # 只测手柄

需要硬件在线：ESP32 接 COM3，Xbox 手柄已连接。
退出码 0 = 全部通过；1 = 有失败。
"""

import ctypes
import ctypes.wintypes as wintypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devices.xinput_api import XINPUT_STATE

RESULTS = []


def report(name, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    RESULTS.append((name, ok))
    print(f"  [{tag}] {name}{suffix}")
    return ok


#
# XInput 手柄检测
#


def xinput_slots():
    try:
        x = ctypes.WinDLL("xinput1_4")
        x.XInputGetState.restype = ctypes.c_ulong
        x.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
    except Exception:
        return []

    found = []
    for i in range(4):
        state = XINPUT_STATE()
        if x.XInputGetState(i, ctypes.byref(state)) == 0:
            found.append(i)
    return found


def test_xinput():
    print("== XInput Controller ==")
    slots = xinput_slots()

    if not slots:
        return report("XInput controller detected", False, "no controller connected")

    report("XInput controller detected", True, f"slots={slots}")

    # 采样若干帧确认能读取状态（不要求按键）
    x = ctypes.WinDLL("xinput1_4")
    x.XInputGetState.restype = ctypes.c_ulong
    x.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]

    ok = True
    for _ in range(5):
        state = XINPUT_STATE()
        if x.XInputGetState(slots[0], ctypes.byref(state)) != 0:
            ok = False
            break
        time.sleep(0.02)

    return report("XInput state readable", ok)


#
# ESP32 串口检测
#


def test_esp32(port="COM3", baudrate=115200, sample_seconds=3):
    print("== ESP32 Gyro (serial) ==")

    try:
        import serial
    except ImportError:
        return report("pyserial available", False, "pyserial not installed")

    try:
        ser = serial.Serial(port, baudrate, timeout=1)
    except Exception as error:
        return report(f"ESP32 on {port}", False, str(error))

    try:
        frames = 0
        x_values = []
        y_values = []
        start = time.time()

        while time.time() - start < sample_seconds:
            line = ser.readline()
            if not line:
                continue
            text = line.decode("utf-8", errors="replace").strip()

            if text.startswith("FRAME="):
                frames += 1
            elif text.startswith("X="):
                try:
                    x_values.append(int(text.split("=")[1]))
                except ValueError:
                    pass
            elif text.startswith("Y="):
                try:
                    y_values.append(int(text.split("=")[1]))
                except ValueError:
                    pass
    finally:
        ser.close()

    report(f"ESP32 serial connected ({port})", True)
    report("FRAME stream active", frames > 0, f"{frames} frames")
    report("X axis data present", len(x_values) > 0, f"{len(x_values)} samples")
    report("Y axis data present", len(y_values) > 0, f"{len(y_values)} samples")

    if x_values:
        report("X within XInput range", min(x_values) >= -32768 and max(x_values) <= 32767,
               f"range {min(x_values)}..{max(x_values)}")

    return frames > 0 and x_values and y_values


#
# 引擎端到端（不依赖真实硬件输入，用合成数据）
#


def test_engine_pipeline():
    print("== Engine Pipeline (virtual data) ==")

    from app import CapabilityNexusApp

    try:
        app = CapabilityNexusApp()
    except Exception as error:
        return report("engine starts", False, str(error))

    try:
        # 虚拟输出存在
        instances = app.output_manager.get_instances()
        ok_virtual = "virtual_xinput" in instances
        report("virtual XInput output", ok_virtual, f"instances={list(instances.keys())}")

        # 合成数据走完整链路
        import time as _time
        from core.stream import StreamData

        app.event_bus.publish(StreamData("control.right_x", float(5000)))
        _time.sleep(0.1)

        outputs = app.status_monitor.snapshot_outputs()
        report("output event published", bool(outputs.get("right_x") is not None),
               f"right_x={outputs.get('right_x')}")

        return ok_virtual
    finally:
        app.close()


def main():
    args = sys.argv[1:]
    test_esp = "--esp32" in args or "--xinput" not in args
    test_xi = "--xinput" in args or "--esp32" not in args

    print("=" * 56)
    print(" CapabilityNexus Hardware-in-the-Loop Test")
    print("=" * 56)
    print()

    if test_xi:
        test_xinput()
        print()

    if test_esp:
        test_esp32()
        print()

    test_engine_pipeline()
    print()

    print("=" * 56)
    print(" Results")
    print("=" * 56)
    for name, ok in RESULTS:
        tag = "PASS" if ok else "FAIL"
        print(f"  [{tag}] {name}")

    failed = sum(1 for _name, ok in RESULTS if not ok)
    print()
    print(f"  {len(RESULTS) - failed}/{len(RESULTS)} passed")

    if failed:
        print("  Hardware test FAILED - check connections and retry.")
        return 1

    print("  All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
