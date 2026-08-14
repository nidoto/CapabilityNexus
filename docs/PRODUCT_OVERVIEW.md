# CapabilityNexus 产品说明

## 产品核心

CapabilityNexus 的核心是：

```text
任意设备 -> 任意功能 -> CapabilityNexus -> 任意功能 -> 任意设备
```

CapabilityNexus 是现实输入能力的抽象、处理、映射和路由平台。

设备只负责提供数据，应用程序只负责使用功能，CapabilityNexus 负责连接
两者之间的能力关系。

## 产品定位

CapabilityNexus 是一个开放式输入输出中间层。

它不是：

- 某一种游戏的插件
- 某一种手柄的专用工具
- Xbox 模拟器
- 硬件厂商驱动的替代品

它是：

- 现实设备能力抽象层
- 多设备输入融合引擎
- 输入能力映射系统
- 标准兼容输出路由器
- 双向输入输出反馈中间层

## 工作方式

```text
现实设备
    -> 设备协议
    -> 数据流
    -> 能力注册
    -> 数据处理
    -> 逻辑变换
    -> 功能映射
    -> 标准兼容输出
    -> 游戏或应用
```

输出方向也可以反向工作：

```text
游戏或应用
    -> 标准兼容设备请求
    -> CapabilityNexus
    -> 反馈能力
    -> 现实设备
```

## 能力抽象

CapabilityNexus 不直接依赖具体硬件名称，而是使用能力名称描述数据。

例如：

```text
motion.pitch
motion.roll
control.right_x
control.right_y
xbox.a
xbox.left_trigger
```

同一个能力可以被映射到不同功能，不同设备也可以提供相同能力。

## 输入设备

当前系统支持或预留以下输入类型：

- XInput 控制器
- HID 手柄、方向盘和摇杆
- ESP32 与串口传感器
- TCP、UDP 和自定义连接
- Bluetooth、FTMS 和 ANT 设备
- 可扩展的自定义设备

## 输出设备

当前系统支持或预留以下输出类型：

- XInput 兼容控制器
- 键盘
- 鼠标
- DualShock 兼容控制器
- 真实设备反馈输出

这里的 XInput 兼容控制器表示一种标准兼容输出，不代表 CapabilityNexus
是 Xbox 模拟器或 Xbox 产品。

## 数据处理能力

CapabilityNexus 提供以下通用处理能力：

- 输入范围归一化
- 死区处理
- 灵敏度调整
- 输出限幅
- 长按检测
- 连按检测
- 按住重复触发
- 一对多映射
- 多对一映射
- 运行时映射刷新

## 固件与客户端边界

对于包含专有算法的硬件，推荐采用以下边界：

```text
闭源固件
    -> 传感器融合、校准、滤波、专有算法
    -> 最终控制值
    -> 开源 CapabilityNexus 客户端
    -> 能力注册、映射和转发
```

这样可以让硬件厂商保留自己的算法，同时使用开放的客户端生态和标准兼容
输出能力。

## 双向反馈

CapabilityNexus 不只处理输入，也可以捕获应用程序对输出设备发出的请求。

例如，游戏向 XInput 兼容控制器发送震动请求时，客户端可以：

- 记录请求来源
- 记录左右马达数值
- 在实时监控中显示
- 映射到其他反馈设备

## 设备可见性

Windows 可能同时向应用程序暴露实体设备和 XInput 兼容输出。

当游戏自动选择实体设备时，可以使用 HidHide 将实体设备对游戏隐藏，
同时保留 CapabilityNexus 对实体设备的读取权限。

HidHide 属于可选的 Windows 系统集成功能，需要用户同意、管理员权限，
并且可能需要重启系统。

## 当前状态

- 核心事件管线：可用
- XInput 兼容输出：依赖 ViGEmBus 可用
- ESP32 串口输入：可用
- 设备和输出实时监控：可用
- 映射和处理器：可用
- 反向请求捕获：可用
- 运行时依赖检测：可用
- 游戏独占模式（HidHide 隐藏物理手柄）：可用
- 硬件闭环与游戏兼容性测试：持续进行

---

# CapabilityNexus Product Overview

## Product Core

The core idea of CapabilityNexus is:

```text
Any Device -> Any Capability -> CapabilityNexus -> Any Function -> Any Device
```

CapabilityNexus is a platform for abstracting, processing, mapping and routing
real-world input capabilities.

Devices provide data. Applications consume functions. CapabilityNexus connects
the capability relationship between them.

## Product Positioning

CapabilityNexus is an open input/output middleware layer.

It is not:

- A plug-in for one specific game
- A tool for one specific controller
- An Xbox emulator
- A replacement for vendor hardware drivers

It is:

- A real-world device capability abstraction layer
- A multi-device input fusion engine
- An input capability mapping system
- A standard-compatible output router
- A bidirectional input and feedback middleware layer

## Processing Model

```text
Physical Device
    -> Device Protocol
    -> Data Stream
    -> Capability Registry
    -> Processing
    -> Logic Transform
    -> Function Mapping
    -> Standard-compatible Output
    -> Game or Application
```

The output direction can also work in reverse:

```text
Game or Application
    -> Standard-compatible Device Request
    -> CapabilityNexus
    -> Feedback Capability
    -> Physical Device
```

## Capability Abstraction

CapabilityNexus describes data through capability identifiers instead of direct
hardware names.

Examples of capability identifiers include:

```text
motion.pitch
motion.roll
control.right_x
control.right_y
xbox.a
xbox.left_trigger
```

One capability can be mapped to different functions, and different devices can
provide the same capability.

## Input Devices

The current system supports or reserves integration points for:

- XInput controllers
- HID controllers, wheels and joysticks
- ESP32 and serial sensors
- TCP, UDP and custom connections
- Bluetooth, FTMS and ANT devices
- Extensible custom devices

## Output Devices

The current system supports or reserves integration points for:

- XInput-compatible controllers
- Keyboard
- Mouse
- DualShock-compatible controllers
- Real-device feedback outputs

The term XInput-compatible controller describes a standard-compatible output.
It does not mean CapabilityNexus is an Xbox emulator or an Xbox product.

## Processing Capabilities

CapabilityNexus provides general-purpose processing features including:

- Input range normalization
- Deadzone processing
- Sensitivity adjustment
- Output clamping
- Long-press detection
- Double-tap detection
- Hold-repeat triggering
- One-to-many mapping
- Many-to-one mapping
- Runtime mapping reload

## Firmware and Client Boundary

For hardware containing proprietary algorithms, the recommended boundary is:

```text
Closed Firmware
    -> Sensor fusion, calibration, filtering and proprietary algorithms
    -> Final control values
    -> Open CapabilityNexus Client
    -> Capability registration, mapping and forwarding
```

This allows hardware vendors to keep their algorithms private while using an
open client ecosystem and standard-compatible output capabilities.

## Bidirectional Feedback

CapabilityNexus processes more than input. It can also capture requests sent by
applications to output devices.

For example, when a game sends a rumble request to an XInput-compatible
controller, the client can:

- Record the request source
- Record left and right motor values
- Display the request in live monitoring
- Map it to another feedback device

## Device Visibility

Windows may expose both physical devices and XInput-compatible outputs to an
application.

When a game automatically selects a physical device, HidHide can hide that
physical device from the game while preserving CapabilityNexus access to it.

HidHide is an optional Windows system integration. It requires user consent,
administrator privileges and may require a system reboot.

## Current Status

- Core event pipeline: operational
- XInput-compatible output: operational with ViGEmBus
- ESP32 serial input: operational
- Device and output live monitoring: operational
- Mapping and processors: operational
- Reverse request capture: operational
- Runtime dependency detection: operational
- Game-exclusive mode (HidHide hiding physical controllers): operational
- Hardware-in-the-loop and game compatibility testing: ongoing
