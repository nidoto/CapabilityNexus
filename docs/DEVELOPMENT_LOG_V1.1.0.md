# CapabilityNexus 开发日志

版本：

V1.1.0


日期：

2026


---

# 1. 项目简介


CapabilityNexus 是一个事件驱动的现实输入抽象框架。


项目目标：

将现实世界中的各种输入设备：

- IMU 传感器
- 自定义硬件
- VR 设备
- 骑行设备
- 模拟设备

转换成为统一 Capability。


然后通过 Mapping 系统输出到：

- 虚拟 Xbox Controller
- 游戏
- 其他数字应用


核心思想：

设备不直接控制应用。

设备只提供能力。

CapabilityNexus 负责连接现实与虚拟。


---

# 2. V1.0 阶段完成内容


V1.0 阶段主要完成基础框架。


完成：

## EventBus


建立系统内部事件通信机制。


所有模块通过 EventBus 通信。


避免：


模块 A
直接调用
模块 B



采用：


模块 A

↓

EventBus

↓

模块 B



---

## Capability Registry


完成能力注册系统。


设备提供：


motion.pitch
motion.roll
motion.yaw



而不是：


ESP32
BNO085
某型号设备



系统只关注能力。


---

## Package System


完成 Package 加载机制。


支持：


packages/



加载外部能力包。


当前测试包：


CNX Motion Demo



---

## Stream 系统


完成原始数据流处理。


流程：



输入数据

↓

StreamData

↓

Channel



---

## Mapping Engine


完成能力到输出映射。


例如：



motion.pitch

    ↓

right_x



---

## Virtual XInput


完成虚拟 Xbox 输入输出。


当前支持：


right_x
right_y
left_trigger



---

# 3. V1.1.0 新增内容


V1.1.0 重点：

增加 Processor Pipeline。


目标：

将物理输入转换成标准控制器范围。


---

# Processor 系统


新增：


ProcessorManager



配置文件：


config/processors.json



支持处理器：


## Normalizer


作用：

范围转换。


例如：

输入：


-180 ~ 180



转换：


-32768 ~ 32767




---

## Deadzone


作用：

去除小范围抖动。


例如：


value < threshold

=

0




---

## Sensitivity


作用：

调整输入灵敏度。


例如：


output = input * sensitivity




---

## Clamp


作用：

限制输出范围。


例如：


minimum=-32768

maximum=32767




---

# 4. 当前完整数据链


当前已经验证：



UMI_DATA

↓

UMIParser

↓

StreamData

↓

StreamAdapter

↓

Channel

↓

ProcessorManager

↓

ProcessedChannel

↓

MappingEngine

↓

OutputEvent

↓

VirtualXInput

↓

游戏输入



测试成功：


输入：


UMI_DATA motion.pitch=90



输出：


right_x = 32766



说明：

软件链路已经闭环。


---

# 5. 当前测试状态


已验证：

✅ Capability 注册

✅ Package 加载

✅ Processor 加载

✅ Normalizer 工作

✅ Deadzone 工作

✅ Sensitivity 工作

✅ Clamp 工作

✅ Mapping 工作

✅ Virtual XInput 输出


---

# 6. 尚未完成内容


当前没有：

## ESP32 硬件输入


计划：


ESP32-S3

BNO085



输出：


UMI_DATA motion.pitch=value

UMI_DATA motion.roll=value

UMI_DATA motion.yaw=value




---

## 校准系统


目前：

保留 Processor 框架。


暂不开发：

- 自动校准
- 设备专属参数
- 高级滤波


原因：

当前优先完成整体框架。


---

# 7. 下一阶段目标


版本目标：


V1.2.0



目标：

完成第一次真实硬件闭环。


流程：



BNO085

↓

ESP32-S3

↓

USB Serial

↓

CapabilityNexus

↓

Virtual XInput

↓

游戏



---

# 8. 长期方向


CapabilityNexus 不限制于游戏。


未来支持：

## VR


head.pitch
head.roll
head.yaw



## 骑行设备


cycling.speed

cycling.cadence

cycling.power

cycling.resistance

cycling.steering



## 模拟设备


steering wheel

flight controller

motion platform



目标：

建立现实世界输入到数字世界的通用桥梁。


---

# 9. 开发原则


1.

核心框架稳定优先。


2.

设备通过 Capability 接入。


3.

不要在 Core 中加入设备特殊逻辑。


4.

新设备应该通过 Package 扩展。


5.

所有模块通过 EventBus 通信。


---

# 当前版本总结


版本：

V1.1.0


状态：

核心软件框架完成。


下一里程碑：

ESP32-S3 + BNO085 接入。