# CapabilityNexus 开发日志

版本：

V1.5.0


日期：

2026


---

# 1. 版本目标


V1.5.0 目标：


更多输出设备（DS4/方向盘/飞行摇杆）

ANT+ 骑行台

GUI 完善

代码整理


实际完成：


Virtual DS4 输出设备 ✅

ANT+ 骑行台输入源 ✅

输出设备管理（可多个并存）✅

GUI 完善（对称布局/双向映射/映射列）✅

代码整理 ✅


---

# 2. Virtual DS4 输出设备


## 说明


新增 DualShock 协议兼容虚拟手柄输出。


## 能力


ds4.left_x / left_y / right_x / right_y - 摇杆


ds4.left_trigger / right_trigger - 扳机


ds4.button_cross / circle / square / triangle


ds4.button_shoulder_left / right


ds4.button_options / share


ds4.button_thumb_left / right


## 实现


output/virtual_ds4.py（继承 VGamepadDevice 基类）


---

# 3. ANT+ 骑行台


## 说明


新增 ANT+ 骑行设备输入源（需 USB ANT+ 适配器）。


## 支持


FitnessEquipment (FE-C) - 功率/速度/踏频/阻力


PowerMeter - 功率计


BikeSpeedCadence - 速度/踏频


## 能力（与 BLE FTMS 统一）


cycling.power / cadence / speed / resistance


## 实现


devices/ant_device.py（openant 库）


---

# 4. 输出设备管理


## 理念


输出设备可多个并存，用户管理。


## config/outputs.json


{ "outputs": [ { "id": "virtual_x360", "type": "xinput", "name": "..." } ] }


## 实现


output/manager.py（OutputDeviceManager）


加载/添加/移除/实例化


## GUI


输出设备面板（树形，展示每个设备的功能）


添加/移除输出设备按钮


---

# 5. GUI 完善


## 对称布局


左侧：输入设备树


右侧：输出设备树


## 双向映射


双击左侧输入能力 → 正向映射（选输出功能）


双击右侧输出功能 → 反向映射（选输入能力）


## 映射列


设备树第二列显示映射值：


输入：xbox.a → button_a


输出：right_x ← motion.pitch


未映射显示空


## 其他


XInput 连接/断开按钮


蓝牙已配对设备扫描


中英文切换


---

# 6. 代码整理


## 删除死代码


devices/serial_device.py（被 serial_connection 取代）


core/calibration.py（空壳）


capabilities_old/（废弃）


tools/pad_widget.py（GUI 未接入）


根目录空文件


## 修复死配置


Transform Layer 的 config/transforms.json 之前从未加载


现在 main.py 调用 transform_layer.load()


hold/tap/invert 规则真正生效


## 性能优化


EventBus 加 debug 开关（默认关闭）


清理热路径 print（每值更新/每数据帧/每次映射）


## 消除重复


cnx_cli.py 复用 tools/config_io


## 架构拆分


main.py（436行）→ app.py（装配+接线）+ main.py（入口）


## 代码去重


output/vgamepad_base.py 公共基类


virtual_xinput.py（435→约90行）


virtual_ds4.py（165→约50行）


---

# 7. 新增/修改文件


## 新增


app.py - 应用装配（CapabilityNexusApp）


output/vgamepad_base.py - vgamepad 公共基类


output/virtual_ds4.py - DS4 输出


output/manager.py - 输出设备管理器


devices/ant_device.py - ANT+ 骑行台


config/outputs.json - 输出设备配置


## 修改


main.py - 轻量入口


tools/cnx_gui.py - 对称布局/双向映射/映射列


tools/cnx_cli.py - 复用 config_io


core/event_bus.py - debug 开关


mapping/mapper.py - 清理热路径 print


output/virtual_xinput.py - 继承基类


protocols/serial_protocol.py - 清理热路径 print


---

# 8. 当前状态总结


版本：

V1.5.0


状态：


更多输出设备完成（DS4）

ANT+ 骑行台完成

输出设备管理完成

GUI 完善完成

代码整理完成


下一里程碑：


V1.6.0


虚拟方向盘/飞行摇杆输出

高级逻辑表（长按时长/双击/组合键）

GUI 实时输入显示

设备库投稿流程
