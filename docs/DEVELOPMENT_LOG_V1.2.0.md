# CapabilityNexus 开发日志

版本：

V1.2.0


日期：

2026


---

# 1. 版本目标


V1.2.0 目标：


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


实际完成：


真实硬件闭环 ✅

多输入源合并 ✅

设备识别系统 ✅

双向设备输出 ✅


---

# 2. 真实硬件闭环


## 硬件


ESP32-S3 + BNO085（I2C）

固件：


arduino/esp32_firmware/


输出格式：


FRAME=1

X=12.50

Y=-3.20

R=0.10


通道映射：


X → yaw

Y → pitch

R → roll


## 软件链路


验证成功：


ESP32 Serial

↓

SerialParser

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

Virtual XInput (ViGEmBus)

↓

Windows 识别虚拟 Xbox 360 手柄


测试结果：


倾斜设备 → 右摇杆 X/Y 实时跟随


X（yaw）：-72° ~ 2°，数百个唯一值

Y（pitch）：-0.6° ~ 38°，数百个唯一值

R（roll）：-12° ~ 347°，数百个唯一值


---

# 3. 多输入源合并


## 目标


两个设备合并成一个虚拟手柄。


## 实现


Xbox One 真实手柄（XInput API）

+

ESP32 陀螺仪（串口）


合并到同一个虚拟 x360 手柄：


Xbox One 左摇杆 / 按钮 / 扳机 → 虚拟 x360


ESP32 pitch → 右摇杆 X


ESP32 roll → 右摇杆 Y


## 验证


两个来源在同一虚拟手柄上互不干扰：


left_x 来自真实手柄，right_x 来自陀螺仪


---

# 4. 设备识别系统


## 架构


枚举设备（DeviceDetector）

↓

提取指纹（USB VID:PID / XInput 槽位 / 串口描述）

↓

查设备库（DeviceLibrary，GitHub）

↓

命中 → 装配


## 设备分类


product（成品设备）：


Xbox One → 指纹自动识别 → 自动装配


template（开发板模板）：


ESP32 → 识别出是开发板 → 提示用户自定义能力


未知设备：


提示用户手动添加


## 自定义设备


ESP32 / 树莓派等开发板：


用户自己定义功能（陀螺仪 / 压力计 / 温度计 / 其他）


入口：


config/devices.json


---

# 5. 双向设备输出


## 理念


真实设备 → 客户端 → 虚拟设备 → 游戏


这条链路上，游戏也会向虚拟设备发请求（如震动）。


## 实现


OutputRouter：


xbox.* → 真实 Xbox One 手柄


其他 → 虚拟 x360 手柄


RealXInputOutput：


XInputSetState 驱动真实手柄震动马达


VirtualXInput：


注册 vgamepad 通知回调，捕获游戏震动请求


## 未满足需求处理


游戏发来虚拟设备不支持的请求（如震动）：


已映射 → 路由到目标（真实手柄 / 另一虚拟设备）


未映射 → 提示用户：


[IMPORTANT] Game requested an unmapped capability


用户可选：


1. 映射到真实设备

2. 映射到另一虚拟设备

3. 忽略


---

# 6. CLI 引导工具


新增：


tools/cnx_cli.py


命令：


python tools/cnx_cli.py create-package


交互式创建能力包（packages/xxx/）


python tools/cnx_cli.py add-device


交互式添加设备（config/devices.json）


python tools/cnx_cli.py map-capability


交互式映射能力到输出目标


python tools/cnx_cli.py list-mappings


查看当前映射


---

# 7. 新增/修改文件


## 新增


devices/detector.py

设备枚举与指纹提取


devices/device_library.py

设备库拉取（GitHub）+ 缓存 + 指纹匹配


devices/device_manager.py

设备装配管理器


output/real_xinput.py

真实设备输出（Xbox 震动马达）


output/router.py

输出路由（虚拟 vs 真实设备）


output/request_handler.py

游戏请求处理（映射 / 提示）


tools/cnx_cli.py

CLI 引导工具


arduino/esp32_firmware/

ESP32 固件


packages/xbox_one/

Xbox One 能力包（含输出能力）


## 修改


protocols/serial_protocol.py

配置化解析器（键映射 + 可选帧）


main.py

设备自动装配 + 输出路由 + 请求处理


core/system_event.py

新增 DeviceRequestEvent


---

# 8. GitHub 仓库


CapabilityNexus

https://github.com/nidoto/CapabilityNexus


CapabilityNexus-Devices（设备库）

https://github.com/nidoto/CapabilityNexus-Devices


---

# 9. 当前状态总结


版本：

V1.2.0


状态：


真实硬件闭环完成

多输入源合并完成

设备识别完成

双向输出完成


下一里程碑：


V1.3.0

用户自定义设备完整流程

映射配置交互

GUI 界面


---

# 10. 设计决策记录


## 10.1 传输模式系统


不同功能有不同的传输语义：


stream - 持续流（轴 / 陀螺仪 / 功率），按频率发送


state  - 最新值（扳机），值变化才发


edge   - 边沿触发（按钮），按下/释放瞬间发


速率档位：


slow    - 30Hz

medium  - 125Hz

fast    - 1000Hz

自定义  - rate 直接指定 Hz


实现：


core/transport.py（TransportController）

能力定义 transport 字段


## 10.2 映射表暂不重构


当前映射保持简单一对一（source -> target）。


未来完整映射模型（暂缓）：


- 一对多
- 多对一（合并策略）
- 虚拟 → 虚拟
- 真实 → 真实
- 功能级映射


映射本质是路由表：


输入功能的数据路由到用户指定的输出功能。


## 10.3 Transform Layer 预留


未来用户自定义逻辑表：


按 A 键 3 秒 → 触发 B 键


连按 / 双击 / 条件触发


扩展点位置：


ProcessedChannel → [TransformLayer] → MappingEngine


当前未实现，接口预留，不改变数据流。


## 10.4 不做设备硬件属性


不做"设备是否自动回中"等硬件属性。


原因：


中间层只转发值。

回中体现在数据本身（值归零），不需要语义化设备行为。


相关未来项：


映射层 return_to_center（输出回中策略）留待未来。
