1. 版本问题

应该保持：

V1.1.0

不是 V1.0。

原因：

V1.0 是：

EventBus
Capability Registry
Package
Stream
Mapping

而现在已经增加：

ProcessorManager
processors.json
Normalizer
Deadzone
Sensitivity
Clamp
VirtualXInput

所以升级 V1.1.0 是正确的。

2. 当前完成度

之前写：

软件框架完成

这个描述需要更准确。

应该是：

核心软件框架完成

第一阶段硬件接入准备完成

因为：

现在还没有：

ESP32-S3
BNO085
USB Serial 实测
真实 IMU 数据

所以不能说完整完成。

3. 项目定位

之前文档里面有一点偏向：

“游戏控制器”

这是不准确的。

正确理解：

CapabilityNexus 是：

现实输入抽象层

游戏只是第一个应用场景。

未来：

自行车：

骑行台

速度
踏频
阻力
方向

↓

CapabilityNexus

↓

游戏

VR：

头部运动

身体运动

↓

CapabilityNexus

↓

VR应用

机器人：

传感器

↓

CapabilityNexus

↓

控制系统

所以文档应该强调：

不为某个游戏制作插件，而是建立现实世界到数字世界的通用输入层。

4. 架构理解

我目前理解的真实架构应该是：

                 Physical Device
                       |
                       |
                 Protocol Layer
                       |
                       |
                    StreamData
                       |
                       |
                 Stream Adapter
                       |
                       |
                    Channel
                       |
                       |
              Processor Pipeline
                       |
                       |
               ProcessedChannel
                       |
                       |
                Mapping Engine
                       |
                       |
                 OutputEvent
                       |
                       |
              Virtual Device
                       |
                       |
                    Game

其中：

Device

不知道游戏。

例如 ESP32 只负责：

pitch=90
roll=20
yaw=-5
Capability

定义能力：

motion.pitch
motion.roll
motion.yaw
Processor

负责：

物理量：

角度
速度
压力
力量

转换为：

数字输入：

-32768 ~ 32767
Mapping

负责：

motion.pitch

↓

right_x

未来：

同一个：

motion.pitch

可以：

right_x

camera_x

VR_head_rotation
5. 下一阶段

V1.2.0 已达成：

ESP32-S3 + BNO085

↓

USB Serial

↓

CapabilityNexus

↓

Virtual XInput

↓

游戏

已验证：

真实硬件闭环完成

多输入源合并完成（Xbox One + ESP32）

设备识别完成

双向设备输出完成

游戏请求未满足时提示完成

当前：

V1.2.0

下一步：

V1.3.0

目标：

用户自定义设备完整流程

映射配置交互

GUI 界面