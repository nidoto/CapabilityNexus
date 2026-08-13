# CapabilityNexus 项目上下文


## 1. 项目定位


CapabilityNexus 是一个现实输入抽象框架。


它的目标：

将不同现实设备转换成为统一数字能力。


它不是：

- 单独的手柄程序
- 单独的游戏 Mod
- 单独的传感器驱动


它是中间层。


结构：


现实设备

↓

CapabilityNexus

↓

虚拟世界



---

# 2. 核心思想


设备不直接控制游戏。


例如：

错误：


ESP32

↓

Xbox 摇杆



正确：


ESP32

↓

motion.pitch

↓

Mapping

↓

right_x



设备只负责产生能力。


---

# 3. 当前版本


当前版本：


V1.1.0



当前状态：


软件框架完成

硬件接入等待



---

# 4. 已完成模块


## Core


包含：

- EventBus
- Capability Registry
- Stream 系统


---

## Package


支持：


packages/



加载能力扩展。


---

## Processor


支持：


ProcessorManager



配置：


config/processors.json



---

## Mapping


支持：

能力到输出映射。


例如：


motion.pitch -> right_x



---

## Output


支持：


VirtualXInput



输出虚拟 Xbox 输入。


---

# 5. 当前能力


已有：


motion.pitch

motion.roll

motion.yaw



来源：


CNX Motion Demo



---

# 6. 当前测试输入协议


协议：

UMI Protocol


示例：


UMI_DATA motion.pitch=90



解析后：


StreamData



进入系统。


---

# 7. 当前真实硬件目标


第一款硬件：



ESP32-S3

BNO085



ESP32 负责：

- 读取 IMU
- 计算姿态
- 输出协议


CapabilityNexus 负责：

- 接收
- 处理
- 映射
- 输出


---

# 8. 当前不要做的事情


暂时不要：

- 针对单个设备微调
- 复杂校准算法
- 高级滤波
- 游戏专用逻辑


原因：

当前目标是完成通用框架。


---

# 9. 未来方向


## VR


能力：


head.pitch

head.roll

head.yaw



---

## 骑行


能力：


cycling.speed

cycling.cadence

cycling.power

cycling.resistance

cycling.steering



---

## 模拟设备


支持：

- 方向盘
- 飞行摇杆
- 动感平台
- 运动设备


---

# 10. 修改项目规则


修改前：

先检查：


PROJECT_CONTEXT.md

DEVELOPMENT_LOG.md

ARCHITECTURE.md



然后查看真实代码。


不要：

- 猜接口
- 创建不存在函数
- 改变已经验证架构


---

# 11. 当前最近目标


完成：


ESP32-S3

↓

UMI Protocol

↓

CapabilityNexus

↓

Virtual XInput



第一次真实硬件闭环。
