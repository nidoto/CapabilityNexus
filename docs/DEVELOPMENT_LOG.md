# CapabilityNexus Development Log

## Project

**Name:** CapabilityNexus

**Current Version:** V1.8.0

**Status:** Core Framework Completed + Phone Web (Wheel) Scheme Usable

**Author:** Hai Lin

---

## Recent update (V1.8.0)

> Detailed per-version records live in `DEVELOPMENT_LOG_V1.x.x.md`.
> The bulk of this document below is the historical V1.0-era phase-by-phase log.

Latest cycle highlights:

- Phone Web page is now a full X360-compatible controller: gyro wheel steering,
  two control schemes (gyro gas / touch gas+brake), fan-shaped bottom-corner
  pedals in landscape, 20-level drag gas/brake.
- Wheel rotation setting means **left-right total angle** (racing-wheel
  convention, default 90° ≈ F1, ±45° per side).
- Screen lock with element-based pass-through zones (gas/brake fans, Map,
  Start, lock button stay usable; everything else is blocked).
- Client device tree shows the phone's real reported name, capabilities and
  **data-arrival latency** (measured server-side, no ping / no extra traffic),
  and removes the phone automatically on disconnect.
- Web service starts lazily and is the single owner of the phone link
  (no more port-8765 conflict with the engine).
- New file logger: `logs/client.log` captures engine events, device
  connect/disconnect, phone frames/output samples, vibration requests, etc.
- Racing test (Rush Rally 3): went from "cannot finish" to finishing ~16th
  place with the phone as a wheel.

---

# 1. Project Overview

CapabilityNexus 是一个通用现实输入能力映射平台。

目标：

将现实世界中的各种设备能力：

- IMU
- Gyroscope
- Bicycle trainer
- Steering device
- Motion controller
- Custom ESP32 hardware
- Sensors

转换为游戏和应用程序可以理解的标准输入。

核心思想：


Real World Device

    ↓

CapabilityNexus

    ↓

Virtual Input Device

    ↓

Game / Application


CapabilityNexus 不关注具体硬件。

硬件只负责提供数据。

系统负责：

- 数据接收
- 数据处理
- 数据转换
- 能力映射
- 输出模拟


---

# 2. Development Philosophy

项目设计目标：

## 2.1 Hardware Independent

设备不是核心。

能力才是核心。

例如：

ESP32 + BNO085

提供：


motion.pitch
motion.roll
motion.yaw


未来：

骑行台：


bike.speed
bike.cadence
bike.power
bike.steering


VR设备：


head.pitch
head.yaw
head.roll


都应该进入同一个系统。


---

## 2.2 Event Driven Architecture

系统采用事件驱动。

所有模块通过 EventBus 通信。

模块之间不直接依赖。


数据：


Input

↓

EventBus

↓

Processor

↓

Mapping

↓

Output



---

# 3. Development Timeline


# Phase 1 - Basic Architecture

完成：

- 项目目录设计
- Core 模块设计
- EventBus
- Capability Registry
- Package System


状态：

Completed


---

# Phase 2 - Capability System

完成：

CapabilityRegistry

支持：


motion.pitch
motion.roll
motion.yaw



示例：


[Capability Registered] motion.pitch
[Capability Registered] motion.roll
[Capability Registered] motion.yaw



状态：

Completed


---

# Phase 3 - Stream Pipeline


建立：


StreamData
|
|
v
Channel
|
|
v
ProcessedChannel



数据模型：

## StreamData

原始输入。


例如：


motion.pitch=90



转换：


StreamData

id:
motion.pitch

value:
90



---

## Channel

标准化输入。


示例：


Channel(
id="motion.pitch",
value=90
)



---

## ProcessedChannel

经过处理后的数据。


示例：

输入：


motion.pitch=90



经过：


normalizer
deadzone
sensitivity
clamp



输出：


32767



状态：

Completed


---

# Phase 4 - Processor System


建立处理链。


配置文件：


config/processors.json



支持：

## Normalizer


输入：


-180 ~ 180



输出：


-32768 ~ 32767



---

## Deadzone


过滤小范围抖动。


---

## Sensitivity


调整响应倍率。


---

## Clamp


限制输出范围。


---

当前配置：

```json
{
    "motion.pitch": [
        {
            "type": "normalizer",
            "input_min": -180,
            "input_max": 180
        },
        {
            "type": "deadzone",
            "value": 5
        },
        {
            "type": "sensitivity",
            "value": 2
        },
        {
            "type": "clamp",
            "minimum": -32768,
            "maximum": 32767
        }
    ]
}

状态：

Completed

Phase 5 - Mapping Engine

建立能力映射系统。

Profile:

profiles/default.json

当前：

motion.pitch -> right_x

motion.roll -> right_y

motion.yaw -> left_trigger

流程：

ProcessedChannel

        |

        v

MappingEngine

        |

        v

OutputEvent

状态：

Completed

Phase 6 - Virtual XInput

目标：

让游戏认为：

CapabilityNexus

就是 Xbox Controller。

输出：

right_x

right_y

left_trigger

buttons

已经完成：

VirtualXInput Framework

测试：

[XInput] right_x = 32766

状态：

Framework Completed

Phase 7 - UMI Protocol

建立统一输入协议。

当前测试：

UMI_DATA motion.pitch=90

解析：

UMIParser

↓

StreamData

状态：

Completed

4. Current Complete Data Flow

当前完整链路：

Console / ESP32

        |

        v

UMI Protocol

        |

        v

StreamData

        |

        v

StreamAdapter

        |

        v

Channel

        |

        v

ProcessorManager

        |

        v

ProcessedChannel

        |

        v

MappingEngine

        |

        v

OutputEvent

        |

        v

VirtualXInput

        |

        v

Game
5. Solved Problems
Problem 1

ProcessedChannel 创建错误

错误：

ProcessedChannel.__init__()

unexpected keyword argument id

原因：

参数设计不一致。

解决：

统一位置参数。

状态：

Solved

Problem 2

ProcessorManager 缺少 load()

错误：

AttributeError:
ProcessorManager has no attribute load

原因：

架构调整后缺少配置加载接口。

解决：

增加：

ProcessorManager.load()

状态：

Solved

Problem 3

processors.json 路径错误

错误：

FileNotFoundError

packages/motion_demo/processors.json

原因：

配置路径设计不明确。

解决：

统一：

config/processors.json

状态：

Solved

Problem 4

EventBus 重复订阅

现象：

StreamData 多次触发。

原因：

main.py 中重复：

event_bus.subscribe(
 StreamData,
 stream_receive
)

解决：

删除重复订阅。

状态：

Solved

Problem 5

Processor 无限递归

错误：

RecursionError:
maximum recursion depth exceeded

原因：

ProcessedChannel 再次进入 Channel pipeline。

解决：

增加：

if channel.processed:
    return

状态：

Solved

Problem 6

VirtualXInput 缺少 send()

错误：

AttributeError:
VirtualXInput object has no attribute send

解决：

统一输出接口：

xinput.send(
    target,
    value
)

状态：

Solved

6. Current Test Results

测试输入：

UMI_DATA motion.pitch=180

结果：

Channel

motion.pitch

180

Processor:

Normalizer

180

↓

32767

输出：

Mapping

motion.pitch

↓

right_x

最终：

[XInput]

right_x = 32767

测试：

UMI_DATA motion.pitch=-180

结果：

right_x=-32768

测试：

UMI_DATA motion.pitch=90

结果：

right_x=32766
7. Current Version Definition

当前不是 V1.1。

原因：

目前完成的是：

V1.0 Core Framework

核心框架已经建立。

未来版本规划：

V1.1 ESP32 Integration

目标：

连接真实硬件。

包括：

ESP32 Serial
Bluetooth
WiFi
Real IMU data
V1.2 Device Capability Expansion

增加：

BNO085
Bicycle trainer
Steering input
Pedal sensor
V1.3 Calibration System

增加：

用户校准
Profile保存
不同设备参数
V1.4 Game Profile System

支持：

不同游戏：

GTA5

Euro Truck Simulator

VR Games

Cycling Games
V2.0 Reality Integration Platform

目标：

现实运动进入虚拟世界。

例如：

真实自行车：

Speed
Cadence
Direction
Body movement
Head movement
Voice

进入：

线上游戏世界。

8. Next Development Goal

当前最重要：

不是继续优化 Processor。

下一步：

ESP32 Integration

原因：

现在软件链路已经验证：

Input

↓

Output

缺少：

真实设备。

下一阶段：

ESP32

↓

Serial COM

↓

UMI Protocol

↓

CapabilityNexus

↓

XInput
9. Project Status Summary

当前完成度：

约：

Core Framework: 100%

Hardware Integration: 0%

Real Device Testing: 0%

Game Testing: 0%

整体项目：

CapabilityNexus V1.0
Framework Complete
Ready for Hardware Integration

END