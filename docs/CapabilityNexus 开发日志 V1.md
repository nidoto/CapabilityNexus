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

V1.8.0 已达成：

手机 Web 方向盘方案完整可用：

- 触摸/陀螺仪双方案（按键布局菜单切换）
- 横屏扇形油门/刹车（圆心在屏幕下角，20 档）
- 屏幕锁定放行（游戏按钮/解锁键可操作，其余拦截）
- 方向盘左右合计角度（默认 90°，F1 风格，±45°/侧）

客户端设备树实时化：

- 显示手机真实上报名称/能力/数据到达延时
- 掉线自动移除节点
- 延时=真实数据到达间隔（服务端计时，无额外传输）

Web 服务按需启动 + 独立占用 8765（消除端口冲突）

客户端文件日志：

- logs/client.log（设备连接/断开、手机帧、输出值、震动、心跳）

赛车实测：

- RushRally3 从"不能完赛"到稳定完赛（约 16 名）

当前：

V1.8.0

下一步（待定）：

- 手机页中英双语
- WebRTC 不可靠通道（UDP 抗丢包，按需）
- 日志增强（会话摘要 / Hz 显示）
- 设备库投稿流程
- ESP32 / 真实 IMU 硬件接入