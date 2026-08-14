# CapabilityNexus Product Overview / 产品说明

## 1. Product Definition / 产品定义

CapabilityNexus is an open-source middleware layer that moves real-world input
capabilities into digital applications.

CapabilityNexus 是一个开源中间层，将现实世界的输入能力带入游戏、模拟器、VR 应用和其他数字系统。

It does not bind a device to a specific game. A device publishes capabilities;
the mapping layer decides how those capabilities are used.

它不把设备绑定到某个具体游戏。设备只发布能力，映射层决定能力如何使用。

## 2. Capability Architecture / 能力架构

```text
Hardware / 硬件
    -> Protocol / 协议
    -> StreamData / 数据流
    -> Capability / 能力
    -> Processor / 处理器
    -> Transform / 逻辑变换
    -> Mapping / 映射
    -> Output / 输出
```

This separation allows one physical source to drive several outputs and
several sources to cooperate on one output.

这种分层允许一个现实输入驱动多个输出，也允许多个输入共同驱动一个输出。

## 3. Supported Concepts / 支持的能力模型

### Input Sources / 输入源

- Xbox/XInput controllers / Xbox 与 XInput 手柄
- HID controllers, wheels and joysticks / HID 手柄、方向盘和摇杆
- ESP32 and serial sensors / ESP32 与串口传感器
- TCP, UDP and custom connections / TCP、UDP 和自定义连接
- Bluetooth, FTMS and ANT devices / 蓝牙、FTMS 与 ANT 设备

### Outputs / 输出

- XInput-compatible controller / XInput 兼容控制器
- Keyboard / 键盘
- Mouse / 鼠标
- DualShock-compatible controller / DualShock 兼容控制器
- Real-device feedback routes / 真实设备反馈路由

### Processing / 数据处理

- Normalization / 归一化
- Deadzone / 死区
- Sensitivity / 灵敏度
- Clamp / 限幅
- Long press, double tap and hold repeat / 长按、连按和按住重复
- Runtime mapping reload / 运行时映射刷新

## 4. Advanced Product Direction / 高级产品方向

The project is designed to grow into a multi-device and multi-application
platform:

项目设计目标是发展为多设备、多应用的现实输入平台：

- Game-specific profiles / 游戏专属配置
- Device capability packages / 设备能力包
- Community device library / 社区设备库
- Reverse request and feedback routing / 反向请求与反馈路由
- Multiple physical sources into one compatible output / 多个现实设备汇入一个输出
- One capability into multiple outputs / 一个能力分发到多个输出
- Closed firmware with an open routing client / 闭源固件配合开源路由客户端

These capabilities are tracked separately as runtime features, integrations and
roadmap work. The documentation avoids presenting planned modules as completed
features.

这些能力会分别标记为运行时功能、集成功能和路线图工作，文档不会把计划功能误写成已经完成的功能。

## 5. Firmware Boundary / 固件边界

For proprietary hardware, the recommended boundary is:

对于有专有算法的硬件，推荐采用以下边界：

```text
Closed firmware / 闭源固件
  sensor fusion, calibration, filtering, proprietary algorithm
  传感器融合、校准、滤波、专有算法
                |
                v
Final control values / 最终控制值
                |
Open CapabilityNexus client / 开源 CapabilityNexus 客户端
  protocol, capability registration, mapping, forwarding
  协议、能力注册、映射、转发
```

The included ESP32 example sends signed final XInput-axis values in the range
`-32768..32767` through `X` and `Y`. The client maps them to
`control.right_x` and `control.right_y` without applying angle algorithms.

示例 ESP32 固件通过 `X` 和 `Y` 发送范围为 `-32768..32767` 的有符号最终轴值，客户端将其映射为 `control.right_x` 和 `control.right_y`，不再执行角度算法。

## 6. Bidirectional Feedback / 双向反馈

Games can send feedback to a compatible output. For example, a browser or game
may request left and right rumble. CapabilityNexus captures these requests as
device events and can display or route them.

游戏可以向兼容输出发出反馈请求，例如左右震动。CapabilityNexus 将其捕获为设备事件，并支持显示或继续路由。

## 7. Device Visibility and Exclusive Mode / 设备可见性与独占模式

Windows can expose both a physical controller and an XInput-compatible output.
Some games automatically select the physical controller. HidHide can be used
to hide the physical device from the game while allowing CapabilityNexus to
read it.

Windows 可能同时向游戏暴露实体手柄和 XInput 兼容输出，部分游戏会自动选择实体手柄。可以使用 HidHide 对游戏隐藏实体设备，同时允许 CapabilityNexus 读取。

This is an optional system integration requiring user consent, administrator
privileges and potentially a reboot. It is not part of the core routing engine.

这是可选的系统集成功能，需要用户同意、管理员权限，并可能需要重启，不属于核心路由引擎本身。

## 8. Current Runtime Status / 当前运行状态

| Area / 模块 | Status / 状态 |
|---|---|
| Event pipeline / 事件管线 | Operational / 可用 |
| XInput-compatible output / XInput 兼容输出 | Operational with ViGEmBus / 依赖 ViGEmBus 可用 |
| ESP32 serial input / ESP32 串口输入 | Operational / 可用 |
| Device and output monitoring / 设备与输出监控 | Operational / 可用 |
| Mapping and processors / 映射与处理器 | Operational / 可用 |
| Reverse request capture / 反向请求捕获 | Operational / 可用 |
| Dependency detection / 依赖检测 | Operational / 可用 |
| HidHide session configuration / HidHide 独占配置 | In progress / 集成中 |
| Hardware-in-the-loop tests / 硬件闭环测试 | Ongoing / 持续进行 |
