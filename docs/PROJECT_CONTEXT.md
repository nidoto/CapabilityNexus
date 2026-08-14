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


输出不限定某一种设备：


虚拟 x360 / 键盘 / 鼠标 / 真实设备 / 任意


---

# 3. 当前版本


当前版本：


V1.6.0


当前状态：


实时输入/输出监控完成

高级逻辑表完成

GUI 流程优化完成

设备一致性修复完成


---

# 4. 已完成模块


## Core


包含：


- EventBus
- Capability Registry（含通配模式）
- Stream 系统
- 双向事件（OutputEvent / DeviceRequestEvent）
- 传输控制（stream/state/edge）
- 状态监视（StatusMonitor 实时快照）


---

## 设备识别


支持：


- 自动枚举（XInput / 串口 / USB HID / BLE）
- 指纹匹配设备库（GitHub）
- product（成品设备）自动装配
- template（开发板）提示自定义
- 未知设备手动添加


---

## 连接方式


支持：


- serial（USB 串口）
- tcp（有线/WiFi）
- udp（低延迟网络）
- bluetooth（RFCOMM）
- hid（USB HID 手柄）
- xinput（Xbox）
- ftms（BLE 骑行台）
- custom（用户自定义）


统一连接抽象 LineConnection + 工厂。


---

## 输入源


支持：


- SerialDevice（ESP32 等）
- XInputDevice（Xbox）
- HIDDevice（pygame）
- FTMSDevice（骑行台）


---

## Processor


支持：


- Normalizer / Deadzone / Sensitivity / Clamp
- config/processors.json 配置


---

## Mapping


支持：


- 能力到输出映射
- 一对多（一个输入 → 多个输出）
- 多对一（最后更新优先）
- 增益（gain）
- 回中策略（return_to_center）
- 一键全路由（AutoRouter）
- profiles/default.json


---

## Transform Layer


支持：


- 用户逻辑变换（映射前插入）
- hold（按住）/ tap（单击脉冲）/ invert（反转）
- long_press（长按）/ double_tap（连按）/ hold_repeat（按住连发）
- config/transforms.json
- 防循环（transformed 标记）


---

## Output


支持：


- VirtualXInput（XInput 兼容虚拟手柄）
- VirtualDS4（DualShock 兼容虚拟手柄）
- VirtualKeyboard（pynput）
- VirtualMouse（pynput）
- RealXInputOutput（真实 XInput 设备马达）
- OutputDeviceManager（输出设备管理，可多个并存）
- VGamepadDevice（xinput/ds4 公共基类）
- OutputRouter（路由分发）
- RequestHandler（游戏请求处理）


---

## Package


支持：


- packages/ 加载能力扩展
- motion_demo / xbox_one / hid_generic / cycling
- CLI 引导创建自定义包


---

## 客户端界面


CLI：


tools/cnx_cli.py


GUI：


tools/cnx_gui.py（tkinter，中英文）


---

# 5. 当前能力


已有能力命名空间：


motion.*      - 陀螺仪（ESP32）

xbox.*        - Xbox One 手柄（含输出马达）

hid.*         - 通用 USB HID

cycling.*     - BLE 骑行台


---

# 6. 当前真实硬件


已接入：


ESP32-S3 + BNO085（串口 COM3）


Xbox One 手柄（蓝牙 / XInput）


---

# 7. 未来方向


## 更多输出设备


虚拟方向盘 / 飞行摇杆 / HID 通用输出


## 更多输入源


ANT+ 适配器实测


## 高级逻辑表


组合键 / 条件触发


## GUI 增强


录制映射


## 设备库


投稿流程 / 自动下载


---

# 8. 修改项目规则


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

# 9. 下一阶段


V1.7.0：


虚拟方向盘/飞行摇杆输出

设备库投稿流程

GUI 录制映射
