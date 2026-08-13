CapabilityNexus V1.2.0 系统架构说明
1. 项目定位

CapabilityNexus 是一个通用现实输入能力转换框架。

目标：

将现实世界中的各种输入设备（IMU、骑行台、方向盘、手柄、动作捕捉设备等）的数据，转换成为游戏和软件可以理解的标准输入。

设备是双向的：

输入方向：设备产生能力。
输出方向：设备接收请求（如震动马达）。

核心思想：

现实设备
    ↓
设备协议
    ↓
能力抽象
    ↓
数据处理
    ↓
映射系统
    ↓
虚拟输出设备
    ↓
游戏 / 软件
2. 总体数据流

完整数据链：

ESP32 / Xbox One / USB / Serial / Bluetooth
              |
              |
              v
        设备识别 (DeviceDetector + DeviceLibrary)
              |
              |
              v
        设备驱动 (SerialDevice / XInputDevice)
              |
              |
              v
        StreamData
              |
              |
              v
       Stream Adapter
              |
              |
              v
          Channel
              |
              |
              v
      Processor Pipeline
              |
              |
              v
    ProcessedChannel
              |
              |
              v
      Transform Layer      ← 预留扩展点（未来用户自定义逻辑表）
              |              （组合 / 定时 / 条件触发）
              |
              v
        Mapping Engine
              |
              |
              v
         Output Event
              |
              |
              v
         Output Router
              |
      ┌───────┴───────┐
      v               v
   虚拟 x360      真实 Xbox One
      |               |
      v               v
    游戏          震动马达
3. 双向数据流

游戏也会向虚拟设备发送请求（如震动反馈）。

游戏
    |
    v
虚拟 x360
    |
    v
通知回调 (vgamepad)
    |
    v
DeviceRequestEvent
    |
    v
RequestHandler
    |
    v
已映射？→ 路由到真实设备 / 另一虚拟设备
    |
    v
未映射？→ 提示用户
4. Core 核心模块

目录：

core/

负责整个系统基础通信。

4.1 EventBus

文件：

core/event_bus.py

作用：

系统内部事件通信中心。

所有模块之间不直接调用。

支持两类事件：

- OutputEvent：输入方向（能力 → 输出）
- DeviceRequestEvent：输出方向（游戏请求 → 设备）
4.2 Capability Registry

文件：

core/capability_registry.py

作用：

记录设备提供什么能力。

Capability 不关心来源。

它只描述：

我有什么能力。

能力分为：

- 输入能力（轴 / 扳机 / 按钮）
- 输出能力（震动马达 / 灯）
5. 设备识别系统

目录：

devices/

5.1 DeviceDetector

文件：

devices/detector.py

作用：

枚举系统设备，提取指纹。

支持：

- XInput 手柄槽位（0-3）
- 串口（VID:PID + 描述）
5.2 DeviceLibrary

文件：

devices/device_library.py

作用：

拉取设备库（GitHub raw），按指纹匹配。

本地缓存，离线可用。

指纹匹配规则：

设备库声明什么字段，就检查什么字段。
检测指纹的多余字段不影响匹配。
5.3 设备分类

product（成品设备）：

指纹匹配 → 自动装配（如 Xbox One）。

template（开发板模板）：

指纹匹配 → 识别出板子 → 提示用户自定义能力
（如 ESP32：可能是陀螺仪 / 压力计 / 温度计）。

未知设备：

提示用户手动添加（config/devices.json）。
5.4 DeviceManager

文件：

devices/device_manager.py

作用：

装配设备。

流程：

1. 枚举设备
2. 查设备库（auto 识别）
3. 未命中 → 查 config/devices.json（手动配置）
4. 构建驱动实例（SerialDevice / XInputDevice）
6. Stream 数据流层

相关文件：

core/stream.py

core/stream_adapter.py

StreamData

代表原始输入数据。

例如：

StreamData

channel: motion.pitch

value: 90

StreamData 不处理校准、限幅、映射。

它只是数据进入系统。
7. Channel 数据标准化层

文件：

core/channel.py

作用：

把不同设备输入转换成统一格式。

Channel

id: motion.pitch

value: 90
8. Processor 系统

目录：

processors/

作用：

数据处理流水线。

支持：

Normalizer

范围转换（-180~180 → -32768~32767）。

Deadzone

死区处理（滤除小范围抖动）。

Sensitivity

灵敏度（input * 倍率）。

Clamp

限制输出范围。

配置：

config/processors.json
9. Mapping Engine

目录：

mapping/

作用：

能力 → 输出设备。

配置：

profiles/default.json

支持两种目标：

- 虚拟设备目标（right_x / button_a / left_trigger ...）
- 真实设备目标（xbox.motor_left / xbox.motor_right ...）

9.1 Transform Layer（预留扩展点）

位置：

ProcessedChannel 之后、MappingEngine 之前。

作用（未来实现，当前仅预留接口）：

用户自定义逻辑变换表。

用户可用简单逻辑语句定义变换，例如：

按 A 键 3 秒 → 触发 B 键

按 X 键两次 → 触发 Y

连按 → 双击

接口约定：

Transform Layer 接收 ProcessedChannel，输出 ProcessedChannel。

它不感知设备，只做"能力 → 能力"的变换。

当前状态：

未实现。

架构已保证插入位置不改变数据流：
StreamData → Channel → ProcessedChannel → [TransformLayer] → MappingEngine → OutputEvent

未来新增 TransformLayer 不需要改动 MappingEngine 与数据流。
10. Output 系统

目录：

output/

10.1 VirtualXInput

文件：

output/virtual_xinput.py

作用：

创建虚拟 Xbox 360 手柄（ViGEmBus / vgamepad）。

支持：

- 摇杆 / 扳机 / 按钮
- 游戏震动请求捕获（通知回调）
10.2 RealXInputOutput

文件：

output/real_xinput.py

作用：

驱动真实 Xbox One 手柄。

支持：

- 震动马达（XInputSetState）
10.3 OutputRouter

文件：

output/router.py

作用：

按 target 前缀路由输出。

- xbox.* → 真实 Xbox One 手柄
- 其他 → 虚拟 x360 手柄
10.4 RequestHandler

文件：

output/request_handler.py

作用：

处理游戏发来的请求（DeviceRequestEvent）。

已映射 → 路由到目标。

未映射 → 提示用户。

11. Protocol 协议层

目录：

protocols/

当前：

umi_protocol.py

UMI: Universal Motion Interface

serial_protocol.py

配置化串口解析器。

支持：

- 自定义键映射（KEY=VALUE）
- 可选帧处理（FRAME=）
12. Package 插件系统

目录：

packages/

作用：

设备能力包。

当前：

CNX Motion Demo

能力：motion.pitch / roll / yaw

CNX Xbox One

输入能力：摇杆 / 按钮 / 扳机

输出能力：震动马达

未来：

bno085 / bike_trainer / steering_wheel / vr_tracker
13. CLI 工具

目录：

tools/cnx_cli.py

命令：

create-package

交互式创建能力包。

add-device

交互式添加设备。

map-capability

交互式映射能力到输出目标。

list-mappings

查看当前映射。
14. 当前已经完成

V1.2.0 已完成：

架构

✅ EventBus（含双向事件）

✅ Capability Registry

✅ 设备识别（Detector + Library + Manager）

✅ 多输入源合并

✅ Stream 系统

✅ Channel 系统

✅ Processor Pipeline

✅ Mapping Engine

✅ Output System（虚拟 + 真实 + 路由）

✅ 请求处理（未满足需求提示）

✅ CLI 工具

硬件

✅ ESP32-S3 + BNO085 真实数据

✅ Xbox One 真实手柄

✅ 虚拟 Xbox 360 手柄（Windows 识别）

✅ 真实手柄震动马达
15. 设计原则

CapabilityNexus 不做：

设备驱动集合

而做：

现实能力转换平台

核心原则：

1. 核心框架稳定优先。

2. 设备通过 Capability 接入。

3. 不在 Core 中加入设备特殊逻辑。

4. 新设备应该通过 Package 扩展。

5. 所有模块通过 EventBus 通信。

6. 不写死任何设备 / 功能。

7. 未映射的能力不传输不处理。

8. 游戏请求未满足时提醒用户。
16. 下一阶段

V1.3.0：

用户自定义设备完整流程

映射配置交互

GUI 界面
