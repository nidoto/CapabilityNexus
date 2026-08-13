# CapabilityNexus 开发日志

版本：

V1.3.0


日期：

2026


---

# 1. 版本目标


V1.3.0 目标：


用户自定义设备完整流程

映射配置交互

GUI 界面


实际完成：


传输模式系统 ✅

一键全路由 ✅

多输出设备（键盘/鼠标/x360）✅

GUI 界面（中英文）✅

蓝牙设备扫描 ✅


---

# 2. 传输模式系统


## 理念


不同功能有不同的传输语义，不能一律按轮询发送。


## 三种模式


stream - 持续流（轴 / 陀螺仪 / 功率），按频率发送


state  - 最新值（扳机），值变化才发


edge   - 边沿触发（按钮），按下/释放瞬间发


## 速率档位


slow    - 30Hz

medium  - 125Hz

fast    - 1000Hz

自定义  - rate 直接指定 Hz


## 实现


core/transport.py（TransportController）


能力定义 transport 字段：


"transport": { "mode": "stream", "speed": "fast" }


"transport": { "mode": "state" }


"transport": { "mode": "edge" }


---

# 3. 一键全路由


## 理念


初级玩家连接成品设备后，一键把所有输入功能映射到虚拟 x360。


## 实现


mapping/auto_route.py（AutoRouter）


按能力 id 命名约定自动匹配：


xbox.left_x       -> left_x

xbox.left_trigger -> left_trigger

xbox.a            -> button_a

xbox.dpad_up      -> button_dpad_up


## 缺失输出提示


检测到输出能力（如震动马达）未被自动覆盖时提示：


Outputs not covered (need manual route):

  xbox.motor_left

  xbox.motor_right


---

# 4. 多输出设备


## 理念


输出不限定 x360，支持任意虚拟设备。


## 输出设备


Virtual X360 - 摇杆 / 按钮 / 扳机 / 十字键


Virtual Keyboard - key_w / key_a / key_space / F1-F12 ...


Virtual Mouse - mouse_x / mouse_y / scroll / click


Real Xbox One - 震动马达（真实硬件）


## 实现


output/virtual_xinput.py

output/virtual_keyboard.py（pynput）

output/virtual_mouse.py（pynput）

output/real_xinput.py（XInputSetState）

output/router.py（按前缀路由）

output/devices.py（输出设备注册表）


路由规则：


key_*   -> 虚拟键盘

mouse_* -> 虚拟鼠标

xbox.*  -> 真实 Xbox One

其他    -> 虚拟 x360


---

# 5. GUI 界面


## 技术


tkinter（Python 自带，零依赖）


## 布局


菜单栏：系统 / 设备 / 映射 / 输出 / 帮助 / 语言


左侧：设备功能树（设备 > 输入/输出分组 > 功能）


右侧：当前映射列表


底部：日志


## 交互


双击设备功能 -> 弹出映射窗口


映射窗口：选择输出设备（单选）-> 选择输出功能 -> 应用


## 中英文


默认中文，菜单切换


tools/i18n.py（中英文字典）


---

# 6. 蓝牙设备扫描


## 理念


添加蓝牙设备时，应先显示电脑已连接的设备，再搜索新设备。


## 实现


devices/bluetooth_scanner.py


list_paired_ble() - PnP 查询当前连接设备

scan_ble() - BLE 广播扫描新设备


## 过滤


排除系统内部服务（GATT / AVRCP / RFCOMM / 枚举器 / 适配器）


只显示真实用户设备


---

# 7. 添加设备窗口


连接方式下拉框：


USB / Serial


USB HID (gamepad/wheel)


XInput (Xbox)


Network / WiFi (TCP)


Network / WiFi (UDP)


Bluetooth (RFCOMM)


Bluetooth (BLE Trainer)


Custom connection


蓝牙/BLE 选择后打开扫描窗口，连接成功后：


显示自定义名称（下移）


"使用硬件库检索"勾选框（默认勾选）


---

# 8. 新增/修改文件


## 新增


core/transport.py


mapping/auto_route.py


output/virtual_keyboard.py


output/virtual_mouse.py


output/devices.py


output/request_handler.py


devices/bluetooth_scanner.py


tools/cnx_gui.py


tools/pad_widget.py


tools/config_io.py


tools/i18n.py


## 修改


output/virtual_xinput.py（震动请求捕获）


output/router.py（多设备路由）


main.py（传输控制 + 输出路由 + 请求处理）


tools/cnx_cli.py（auto-route / map 增强）


packages/*/capabilities.json（transport 字段）


---

# 9. 设计决策


## 9.1 不做设备硬件属性


不做"设备是否自动回中"等属性。


中间层只转发值，回中体现在数据本身。


## 9.2 映射表暂不重构


当前保持一对一。


未来：一对多 / 多对一 / 设备间映射。


## 9.3 Transform Layer 预留


未来用户自定义逻辑表（长按/连按/条件触发）


位置：ProcessedChannel -> [TransformLayer] -> MappingEngine


---

# 10. 当前状态总结


版本：

V1.3.0


状态：


传输模式完成

一键全路由完成

多输出设备完成

GUI 完成（中英文）

蓝牙扫描完成


下一里程碑：


V1.4.0


映射表重构（一对多/多对一）

Transform Layer 用户逻辑表

设备库完整支持
