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


设备是双向的：


输入：摇杆 / 按钮 / 传感器


输出：震动马达 / 灯 / 其他


---

# 3. 当前版本


当前版本：


V1.2.0


当前状态：


真实硬件闭环完成

多输入源合并完成

设备识别完成

双向设备输出完成


---

# 4. 已完成模块


## Core


包含：


- EventBus
- Capability Registry
- Stream 系统
- 双向事件（OutputEvent / DeviceRequestEvent）


---

## 设备识别


支持：


- 自动枚举（XInput / 串口 / USB）
- 指纹匹配设备库（GitHub）
- product（成品设备）自动装配
- template（开发板）提示自定义
- 未知设备手动添加


---

## 设备管理


支持：


- config/devices.json 配置
- 自动识别 + 手动自定义
- 协议配置化（键映射 + 帧）


---

## Processor


支持：


- Normalizer / Deadzone / Sensitivity / Clamp
- config/processors.json 配置


---

## Mapping


支持：


- 能力到输出映射
- 映射到虚拟设备 或 真实设备
- profiles/default.json


---

## Output


支持：


- VirtualXInput（虚拟 Xbox 360）
- RealXInputOutput（真实 Xbox 马达）
- OutputRouter（路由分发）
- RequestHandler（游戏请求处理）


---

## Package


支持：


- packages/ 加载能力扩展
- xbox_one（含输出能力）
- motion_demo
- CLI 引导创建自定义包


---

## CLI 工具


tools/cnx_cli.py：


- create-package
- add-device
- map-capability
- list-mappings


---

# 5. 当前能力


已有：


motion.pitch

motion.roll

motion.yaw


来源：


ESP32 + BNO085（CNX Motion Demo）


xbox.left_x / left_y / right_x / right_y


xbox.left_trigger / right_trigger


xbox.a / b / x / y / lb / rb / ls / rs


xbox.start / back / dpad_*


xbox.motor_left / motor_right（输出）


来源：


Xbox One 真实手柄


---

# 6. 当前输入协议


协议：


UMI Protocol / 串口自定义协议


串口格式（可配置）：


FRAME=1

X=12.50

Y=-3.20

R=0.10


键映射可配置：


X → motion.yaw

Y → motion.pitch

R → motion.roll


---

# 7. 当前真实硬件


已接入：


ESP32-S3 + BNO085（串口 COM3）


Xbox One 手柄（蓝牙 / XInput）


---

# 8. 当前不要做的事情


暂时不要：


- 复杂校准算法
- 高级滤波
- 游戏专用逻辑
- 设备专属硬编码


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

# 11. 下一阶段


V1.3.0：


用户自定义设备完整流程


映射配置交互


GUI 界面
