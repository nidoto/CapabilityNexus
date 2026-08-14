# CapabilityNexus 开发日志

版本：

V1.6.0


日期：

2026


---

# 1. 版本目标


V1.6.0 目标：


虚拟方向盘/飞行摇杆输出

高级逻辑表

GUI 实时输入显示

设备库投稿流程


实际完成：


实时输入/输出监控 ✅

高级逻辑表 ✅

GUI 流程优化 ✅

设备一致性修复 ✅


---

# 2. 实时输入/输出监控


## 理念


GUI 显示设备的实时状态：

操作手柄/传感器时看到数值响应。


## 实现


core/status_monitor.py（StatusMonitor）


订阅 StreamData（输入）和 OutputEvent（输出）


维护实时状态快照（线程安全）


## GUI


输入设备树下方：输入实时监控窗口


输出设备树下方：输出实时监控窗口


只显示有输入的通道（静止的 0 值不显示）


按钮显示 pressed/released，轴显示数值


## 引擎控制


GUI 菜单：启动引擎 / 停止引擎


打开客户端自动启动引擎


---

# 3. 高级逻辑表


## 理念


扩展 TransformLayer 的用户逻辑变换。


## 新增变换


long_press  - 长按触发（duration 秒后松开触发）


double_tap  - 连按两次（interval 秒内）触发


hold_repeat - 按住时按间隔重复触发


## 配置示例


{ "source": "xbox.a", "type": "long_press", "target": "xbox.b",
  "params": { "duration": 3.0 } }


{ "source": "xbox.x", "type": "double_tap", "target": "xbox.y",
  "params": { "interval": 0.4 } }


---

# 4. GUI 流程优化


## 移除从设备库安装


菜单 Devices 移除"从设备库安装"。


## 连接即查库


添加设备：选连接方式 → 点"连接"→ 立即检索 GitHub 硬件库


命中 → 自动下载能力包 + 设置 package → 添加设备 → 关闭窗口


底部按钮从"保存"改为"连接"。


---

# 5. 设备一致性修复


## 问题


自动连接的 XInput 设备（product 类型）输出数据，

但设备树不显示（config 无记录），监控数值与设备树不一致。


## 修复


自动识别的成品设备自动登记到 config（标记 auto_connected）


设备树正确显示自动连接的设备 + 能力


去重（同 driver+index 不重复登记）


---

# 6. 代码整理


## 删除死代码


tools/cnx_gui.py 的 install_from_library 方法（菜单项已移除）


---

# 7. 新增/修改文件


## 新增


core/status_monitor.py - 实时状态监视器


## 修改


tools/cnx_gui.py - 监控窗口/引擎控制/连接即查库/设备树


devices/xinput_device.py - 每轮询发布状态


devices/device_manager.py - 自动连接登记到 config


mapping/transform.py - 高级变换（long_press/double_tap/hold_repeat）


config/transforms.json - 高级变换示例


tools/i18n.py - 新界面文案


---

# 8. 当前状态总结


版本：

V1.6.0


状态：


实时监控完成

高级逻辑表完成

GUI 流程优化完成

设备一致性修复完成


下一里程碑：


V1.7.0


虚拟方向盘/飞行摇杆输出

设备库投稿流程

GUI 录制映射
