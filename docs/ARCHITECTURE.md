CapabilityNexus V1.0 系统架构说明
1. 项目定位

CapabilityNexus 是一个通用现实输入能力转换框架。

目标：

将现实世界中的各种输入设备（IMU、骑行台、方向盘、手柄、动作捕捉设备等）的数据，转换成为游戏和软件可以理解的标准输入。

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

ESP32 / USB / Serial / Bluetooth
              |
              |
              v
        UMI Protocol
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
       Mapping Engine
              |
              |
              v
       Output Event
              |
              |
              v
      Virtual Device
              |
              |
              v
          Game
3. Core 核心模块

目录：

core/

负责整个系统基础通信。

3.1 EventBus

文件：

core/event_bus.py

作用：

系统内部事件通信中心。

所有模块之间不直接调用。

例如：

错误：

ESP32
  ↓
XInput

正确：

ESP32
 ↓
StreamData
 ↓
EventBus
 ↓
各模块订阅

优势：

模块解耦
易扩展
支持插件
4. Capability 能力系统

目录：

core/capability_registry.py

作用：

记录设备提供什么能力。

例如：

motion.pitch

motion.roll

motion.yaw

表示：

设备可以提供：

前后倾斜
左右倾斜
水平旋转

Capability 不关心：

来自 ESP32
来自骑行台
来自 VR 设备

它只描述：

我有什么能力。

5. Stream 数据流层

相关文件：

core/stream.py

core/stream_adapter.py
StreamData

代表：

原始输入数据。

例如：

StreamData

source:
ESP32

channel:
motion.pitch

value:
90

StreamData 不处理：

校准
限幅
游戏映射

它只是：

数据进入系统。

6. Channel 数据标准化层

文件：

core/channel.py

作用：

把不同设备输入转换成统一格式。

例如：

ESP32:

pitch=90

骑行台：

steer_angle=90

VR：

head_rotation=90

最终：

Channel

id:
motion.pitch

value:
90
7. Processor 系统

目录：

processors/

作用：

数据处理流水线。

当前支持：

Normalizer

范围转换。

例如：

输入：

-180 ~ 180

转换：

-32768 ~ 32767

用于：

Xbox XInput。

Deadzone

死区处理。

目的：

减少：

陀螺仪漂移
传感器微震

例如：

value < 5

=> 0
Sensitivity

灵敏度。

例如：

input * 2
Clamp

限制范围。

例如：

最大32767

最小-32768
Processor设计原则

Processor 不属于设备。

例如：

错误：

BNO085Processor

正确：

Normalizer
Deadzone
Clamp

因为：

未来：

MPU6050
BNO085
BMI270

都可以使用。

8. ProcessedChannel

文件：

core/processed_channel.py

代表：

已经处理完成的数据。

例如：

输入：

pitch=90

经过：

Normalizer
Sensitivity
Clamp

得到：

32767

ProcessedChannel:

id:

motion.pitch


value:

32767


processed:

True
9. Mapping Engine

目录：

mapping/

作用：

能力 → 输出设备

例如：

配置：

motion.pitch

↓

right_x

意味着：

现实：

向前倾斜自行车

↓

游戏：

右摇杆X轴

Mapping 不关心：

输入来源。

它不知道：

这是：

ESP32
骑行台
VR

只知道：

能力名称。

10. Output 系统

目录：

output/

当前：

VirtualXInput

作用：

创建虚拟Xbox手柄。

支持：

right_x

right_y

left_trigger

未来：

可以增加：

VirtualJoystick

VirtualWheel

VirtualVRController

11. Package 插件系统

目录：

packages/

作用：

设备能力包。

例如：

当前：

CNX Motion Demo

提供：

motion.pitch

motion.roll

motion.yaw

未来：

可以增加：

packages/
    bno085/
    bike_trainer/
    steering_wheel/
    vr_tracker/
12. Protocol 协议层

目录：

protocols/

当前：

umi_protocol.py

UMI:

Universal Motion Interface

作用：

统一设备通信格式。

例如：

ESP32发送：

UMI_DATA motion.pitch=90

解析：

StreamData

未来支持：

USB:

UMI USB

Bluetooth:

UMI BLE

WiFi:

UMI TCP
13. Device 层

目录：

devices/

当前：

serial_device.py

负责：

真实硬件连接。

例如：

ESP32:

COM5

115200

当前：

测试阶段关闭：

# serial_device.connect()

等 ESP32 接入后开启。

14. 当前已经完成

V1.0 已完成：

架构

✅ EventBus

✅ Capability Registry

✅ Package System

✅ Stream System

✅ Channel System

✅ Processor Pipeline

✅ Mapping Engine

✅ Output System

软件测试

已完成：

模拟输入:

UMI_DATA motion.pitch=90


成功:

StreamData

↓

Channel

↓

ProcessedChannel

↓

Mapping

↓

OutputEvent

↓

VirtualXInput

输出：

[XInput] right_x = 32766
15. 当前未完成
硬件连接

下一阶段：

ESP32

↓

Serial/BLE

↓

UMI Protocol

真实传感器

未接入：

BNO085
MPU6050
BMI270
游戏测试

未开始：

GTA5
骑行MOD
VR游戏
模拟驾驶
16. 设计原则

CapabilityNexus 不做：

设备驱动集合

而做：

现实能力转换平台

例如：

自行车：

真实倾斜

↓

motion.roll

↓

right_x

↓

游戏转向

VR：

头部旋转

↓

motion.yaw

↓

camera rotation

骑行台：

速度

踏频

阻力

↓

game input
17. V1.0 当前状态总结

当前版本：

CapabilityNexus V1.0

完成：

软件核心框架。

状态：

模拟输入 OK

虚拟Xbox输出 OK

数据处理 OK

映射 OK


等待:

真实设备

这个 ARCHITECTURE.md 和前面的 PROJECT_CONTEXT.md 配合后，新 GPT 基本可以理解：

我们做的是什么
为什么这么设计
当前代码结构
下一步应该接 ESP32

下一条我发送第三个：