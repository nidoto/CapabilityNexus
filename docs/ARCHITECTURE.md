CapabilityNexus V1.6.0 系统架构说明
1. 项目定位

CapabilityNexus 是一个通用现实输入能力转换框架。

目标：

将现实世界中的各种输入设备（IMU、骑行台、方向盘、手柄、动作捕捉设备等）的数据，转换成为游戏和软件可以理解的标准输入。

设备是双向的：

输入方向：设备产生能力。
输出方向：设备接收请求（如震动马达）。

输出不限定某一种设备：

XInput 兼容 / DualShock 兼容 / 键盘 / 鼠标 / 真实设备 / 任意。

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

ESP32 / Xbox / USB / Serial / Bluetooth / WiFi
              |
              |
              v
        设备识别 (DeviceDetector + DeviceLibrary)
              |
              |
              v
        连接层 (SerialConnection / TcpConnection / ...)
              |
              |
              v
        输入源 (SerialDevice / XInputDevice / HIDDevice / FTMSDevice / ANTDevice)
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
      Transport Controller   ← stream/state/edge 传输控制
              |
              |
              v
        Transform Layer      ← 用户逻辑表（hold/tap/invert）
              |
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
      ┌───────┬───────┬───────┬───────┐
      v       v       v       v       v
   XInput   DS4     键盘    鼠标   真实设备
3. 双向数据流

游戏也会向虚拟设备发送请求（如震动反馈）。

游戏
    |
    v
虚拟 XInput 设备
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
已映射？→ 路由到目标
    |
    v
未映射？→ 提示用户
4. 应用装配

app.py - CapabilityNexusApp

职责：

- 全局对象装配（registry / package / adapter / processor / transport）
- 事件管线接线
- 输出系统装配（output_manager / router / request_handler）
- 设备发现与连接
- 优雅关闭（close）

main.py - 轻量入口

职责：

- 调用 CapabilityNexusApp
- 控制台 REPL 测试
5. Core 核心模块

目录：

core/

5.1 EventBus

core/event_bus.py

两类事件：

- OutputEvent：输入方向（能力 → 输出）
- DeviceRequestEvent：输出方向（游戏请求 → 设备）

debug 开关：默认关闭，避免热路径打印。
5.2 Capability Registry

core/capability_registry.py

支持通配模式：

hid.axis* 匹配 hid.axis0 / hid.axis1 / ...
5.3 Transport Controller

core/transport.py

按能力声明的传输模式决定是否广播：

stream - 持续流，按 rate 节流
state  - 最新值，值变化才发
edge   - 边沿触发，按下/释放瞬间才发
5.4 StatusMonitor

core/status_monitor.py

实时状态监视：

订阅 StreamData（输入）和 OutputEvent（输出）
维护实时状态快照（线程安全）
GUI 轮询读取，实现实时显示
6. 设备识别系统

目录：

devices/

6.1 DeviceDetector

devices/detector.py

枚举系统设备，提取指纹：

- XInput 手柄槽位（0-3）
- 串口（VID:PID + 描述）
6.2 DeviceLibrary

devices/device_library.py

拉取设备库（GitHub raw），按指纹匹配，本地缓存。

设备分类：

product（成品设备）→ 自动装配
template（开发板模板）→ 提示用户自定义能力
未知设备 → 提示手动添加

完整支持：

search(query) - 按名称/ID 搜索
install(id) - 下载能力包到 packages/
identify(device) - 指纹匹配
6.3 DeviceManager

devices/device_manager.py

装配设备：

1. 枚举设备
2. 查设备库（auto 识别）
3. 未命中 → 查 config/devices.json（手动配置）
4. 构建输入源实例

自动连接的成品设备（product）登记到 config（标记 auto_connected），
设备树与实时监控数据一致。
7. 连接层

目录：

devices/connection.py

统一连接抽象 LineConnection：

serial  - SerialConnection（USB 串口）
tcp     - TcpConnection（有线/WiFi）
udp     - UdpConnection（低延迟网络）
bluetooth - BluetoothConnection（RFCOMM）
custom  - 用户自定义（config/custom_connections.py）

工厂：

devices/connection_factory.py
8. 输入源

目录：

devices/

SerialDevice    - 串口设备（ESP32 等）
XInputDevice    - Xbox 手柄（XInput API）
HIDDevice       - USB HID 手柄（pygame）
FTMSDevice      - BLE 骑行台（bleak）
ANTDevice       - ANT+ 骑行设备（openant，需适配器）
9. Stream 数据流层

core/stream.py

core/stream_adapter.py

StreamData

代表原始输入数据。

StreamAdapter 按能力 id 匹配（支持通配模式）生成 Channel。
10. Channel 数据标准化层

core/channel.py

把不同设备输入转换成统一格式。

Channel

id: motion.pitch

value: 90
11. Processor 系统

processors/

支持：

Normalizer - 范围转换
Deadzone   - 死区处理
Sensitivity - 灵敏度
Clamp      - 限制范围

配置：

config/processors.json
12. Mapping Engine

mapping/

能力 → 输出设备。

配置：

profiles/default.json

映射项支持：

target（目标功能）
gain（增益）
return_to_center（回中策略）

一对多：

一个输入 → 多个输出

多对一：

多个输入 → 同一输出（最后更新优先）

一键全路由：

mapping/auto_route.py（AutoRouter）
12.1 Transform Layer

mapping/transform.py

位置：

ProcessedChannel → [TransformLayer] → MappingEngine

作用：

用户在映射前插入逻辑变换。

内置变换：

hold        - 按住 source，输出 target 持续
tap         - source 按下瞬间，输出 target 脉冲一次
invert      - 反转值（1 <-> 0）
long_press  - 长按 duration 秒后松开触发
double_tap  - 连按两次（interval 秒内）触发
hold_repeat - 按住时按 interval 秒间隔重复触发

配置：

config/transforms.json

防循环：

变换输出带 transformed 标记。
13. Output 系统

output/

13.1 VGamepadDevice

output/vgamepad_base.py

xinput / ds4 输出公共基类：

摇杆/扳机/按钮归一化与更新逻辑
子类只需定义按钮枚举和映射表
13.2 VirtualXInput

output/virtual_xinput.py

XInput 兼容虚拟手柄（ViGEmBus / vgamepad）。

支持摇杆/扳机/按钮，注册游戏震动请求捕获。
13.3 VirtualDS4

output/virtual_ds4.py

DualShock 协议兼容虚拟手柄（ViGEmBus / vgamepad）。
13.4 VirtualKeyboard

output/virtual_keyboard.py

pynput 模拟按键。

目标：key_w / key_a / key_space / F1-F12 ...
13.5 VirtualMouse

output/virtual_mouse.py

pynput 模拟鼠标。

目标：mouse_x / mouse_y / scroll / click_*
13.6 RealXInputOutput

output/real_xinput.py

驱动真实 XInput 兼容手柄震动马达（XInputSetState）。
13.7 OutputRouter

output/router.py

按 target 前缀路由：

key_*   → 虚拟键盘
mouse_* → 虚拟鼠标
ds4.*   → DualShock 兼容
xbox.*  → 真实 XInput 设备
其他    → XInput 兼容虚拟手柄
13.8 OutputDeviceManager

output/manager.py

输出设备管理（可多个并存）：

config/outputs.json 配置
加载 / 添加 / 移除 / 实例化
main.py 用用户启用的实例装配路由
13.9 RequestHandler

output/request_handler.py

处理游戏请求（DeviceRequestEvent）：

已映射 → 路由到目标
未映射 → 提示用户
13.10 OutputDeviceInfo

output/devices.py

输出设备注册表（名称 + 功能列表），供 GUI 使用。
14. Protocol 协议层

protocols/

umi_protocol.py - UMI 格式（UMI_DATA motion.pitch=90）
serial_protocol.py - 配置化串口解析（键映射 + 可选帧）
15. Package 插件系统

packages/

motion_demo  - 陀螺仪（motion.*）
xbox_one     - Xbox 手柄（xbox.*，含输出马达）
hid_generic  - 通用 USB HID（hid.*，通配）
cycling      - BLE 骑行台（cycling.*）
16. 客户端界面

16.1 CLI

tools/cnx_cli.py

命令：

add-device / remove-device / list-available
create-package
auto-route
map-capability / remove-mapping / list-mappings
list-library / library-search / install-device
16.2 GUI

tools/cnx_gui.py（tkinter）

菜单栏：系统 / 设备 / 映射 / 输出 / 帮助 / 语言
左侧输入设备树 + 右侧输出设备树（对称）
双击输入能力 → 正向映射
双击输出功能 → 反向映射
映射列显示（输入→目标，输出←驱动）
中英文切换（tools/i18n.py）
16.3 共享数据层

tools/config_io.py（CLI 和 GUI 共用）
17. 蓝牙扫描

devices/bluetooth_scanner.py

list_paired_ble() - PnP 查询当前连接设备
scan_ble() - BLE 广播扫描新设备

过滤系统内部服务，只显示真实设备。
18. 当前已经完成

V1.5.0 已完成：

架构

✅ EventBus（含双向事件 + debug 开关）
✅ Capability Registry（含通配）
✅ 传输控制（stream/state/edge）
✅ Transform Layer（hold/tap/invert）
✅ 设备识别（Detector + Library + Manager）
✅ 连接抽象（serial/tcp/udp/bluetooth/custom）
✅ 多输入源（Serial/XInput/HID/FTMS/ANT）
✅ Processor Pipeline
✅ Mapping（gain / 回中 / 一对多 / 一键全路由）
✅ 多输出设备（XInput/DS4/键盘/鼠标/真实）
✅ 输出设备管理（config/outputs.json）
✅ 请求处理（未满足需求提示）
✅ CLI 工具
✅ GUI（对称布局/双向映射/映射列/中英文）
✅ 应用装配（app.py）

硬件

✅ ESP32-S3 + BNO085
✅ Xbox One 真实手柄
✅ 虚拟 XInput / DS4 手柄（Windows 识别）
✅ 真实手柄震动马达
✅ 蓝牙设备扫描
19. 命名规范与合规说明

CapabilityNexus 是开源的现实输入抽象框架。

它模拟的是协议兼容的虚拟输入设备，不冒充任何品牌产品。

规范：

- 面向用户的界面 / 文档使用协议描述：
  XInput 兼容虚拟手柄
  DualShock 协议兼容虚拟手柄
- 内部技术标识符（xbox.* / ds4.* 能力名、类名）
  是协议层命名，指 XInput / DualShock 协议
- 不出现品牌 logo / 官方命名宣传
- 不冒充正品设备

原则：

协议兼容 ≠ 品牌假冒。
20. 设计原则

1. 核心框架稳定优先。
2. 设备通过 Capability 接入。
3. 不在 Core 中加入设备特殊逻辑。
4. 新设备应该通过 Package 扩展。
5. 所有模块通过 EventBus 通信。
6. 不写死任何设备 / 功能。
7. 未映射的能力不传输不处理。
8. 游戏请求未满足时提醒用户。
9. 中间层只转发值，不做设备语义猜测。
10. 连接方式可插拔，主流内建 + 用户自定义。
21. 下一阶段

V1.7.0：

虚拟方向盘/飞行摇杆输出
设备库投稿流程
GUI 录制映射
