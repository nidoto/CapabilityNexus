# CapabilityNexus

**现实输入能力抽象与路由平台**<br>
**Real-world input capability abstraction and routing platform**

CapabilityNexus connects physical devices, sensors and custom hardware to
games and applications through a capability-based pipeline.

CapabilityNexus 将现实设备、传感器和自制硬件，通过能力抽象管线连接到游戏与应用程序。

```text
Physical Device / 现实设备
          |
          v
Protocol + Capability Layer / 协议与能力层
          |
          v
Processing + Mapping / 处理与映射
          |
          v
XInput-compatible Controller / XInput 兼容控制器
          |
          v
Game / Application / 游戏与应用
```

## Product Positioning / 产品定位

CapabilityNexus is an open-source input/output middleware layer. It is not an
Xbox emulator, game modification or vendor-driver replacement.

CapabilityNexus 是开源的输入输出中间层，不是 Xbox 模拟器、游戏 Mod，也不替代硬件厂商驱动。

## What It Can Do / 核心能力

- Combine Xbox, HID, serial, Bluetooth, TCP, UDP, FTMS, ANT and custom inputs.
  支持多种设备并行接入和组合。
- Convert hardware data into named capabilities instead of game-specific code.
  将硬件数据转换为与游戏解耦的能力。
- Map sensors, buttons and controllers into XInput-compatible, keyboard, mouse
  or DualShock-compatible outputs.
  将传感器、按钮和手柄映射到标准兼容输出。
- Process values with normalization, deadzone, sensitivity, clamp and logic
  transforms.
  支持归一化、死区、灵敏度、限幅和高级逻辑变换。
- Capture reverse requests such as rumble from games and applications.
  捕获游戏和应用发出的震动等反向请求。
- Keep proprietary sensor fusion and calibration inside closed ESP32 firmware.
  允许将传感器融合、校准和专有算法保留在闭源固件中。
- Support runtime device monitoring, mapping reload and game-oriented workflows.
  支持运行时设备监控、映射热更新和面向游戏的工作流。

## Example / 示例

An Xbox One controller can provide buttons and triggers while an ESP32/BNO085
device provides camera axes:

Xbox One 手柄提供按钮和扳机，ESP32/BNO085 提供视角轴：

```text
xbox.a              -> button_a
xbox.left_trigger   -> left_trigger
ESP32 X             -> control.right_x -> right_x
ESP32 Y             -> control.right_y -> right_y
```

The ESP32 firmware performs orientation, calibration, clamping and conversion
to final signed XInput axis values. The open client forwards those values.

ESP32 固件负责姿态计算、校准、限幅和最终 XInput 轴值转换，开源客户端负责协议接收、能力注册、映射和转发。

## Quick Start / 快速开始

1. Install Python 3.11 or newer. / 安装 Python 3.11 或更新版本。
2. Install the required runtime drivers. / 安装必要的运行时驱动。
3. Double-click `start.cmd`. / 双击 `start.cmd`。
4. Add devices from the device-tree context menu. / 从设备树右键菜单添加设备。
5. Configure mappings by double-clicking capabilities. / 双击能力配置映射。
6. Configure the game to use the XInput-compatible controller. / 在游戏中选择兼容控制器。

## Documentation / 文档

- [Product Overview / 产品说明](docs/PRODUCT_OVERVIEW.md)
- [Installation / 安装指南](docs/INSTALLATION.md)
- [Architecture / 系统架构](docs/ARCHITECTURE.md)
- [Development Log / 开发日志](docs/DEVELOPMENT_LOG_V1.7.0.md)
- [Documentation Index / 文档索引](docs/README.md)
- [Third-party Notices / 第三方声明](THIRD_PARTY_NOTICES.md)

## Status / 当前状态

The runtime pipeline, XInput-compatible output, ESP32 serial input, monitoring,
mapping and reverse-request capture are operational. HidHide detection is
implemented; its game-exclusive configuration workflow is being integrated.

当前运行管线、XInput 兼容输出、ESP32 串口输入、实时监控、映射和反向请求捕获已经可用。HidHide 依赖检测已经完成，游戏独占配置流程正在集成。
