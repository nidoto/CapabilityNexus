# CapabilityNexus 开发日志

版本：

V1.4.0


日期：

2026


---

# 1. 版本目标


V1.4.0 目标：


映射表重构（一对多/多对一）

Transform Layer 用户逻辑表

设备库完整支持


实际完成：


映射表重构 ✅

Transform Layer ✅

设备库完整支持 ✅


---

# 2. 映射表重构


## 理念


映射本质是路由表：


一个输入功能的数据可以路由到多个输出功能。


## 新能力


一对多 - 一个输入 → 多个输出


多对一 - 多个输入 → 同一输出（最后更新优先）


设备间映射 - 能力级映射，不限于设备


## 新 profile 格式


"mappings": {

  "motion.pitch": [

    { "target": "right_x", "gain": 1.0 },

    { "target": "key_w", "gain": 0.5 }

  ]

}


## 兼容性


旧格式兼容：


字符串："motion.pitch": "right_x"


dict：{ "target": "...", "gain": ... }


list：多个 target


## 实现


mapping/mapper.py - 支持多 target + 合并


CLI/GUI - 支持追加目标（一对多）


---

# 3. Transform Layer


## 理念


用户在映射前插入逻辑变换：


按 A 键 3 秒 → 触发 B 键

连按 / 双击 / 条件触发


## 位置


ProcessedChannel → [TransformLayer] → MappingEngine


## 内置变换


hold  - 按住 source，输出 target 持续


tap   - source 按下瞬间，输出 target 脉冲一次


invert - 反转值（1 <-> 0）


## 配置


config/transforms.json


"transforms": [

  { "source": "xbox.lb", "type": "hold", "target": "xbox.rb" },

  { "source": "xbox.back", "type": "tap", "target": "xbox.start" }

]


## 关键设计


防无限循环（transformed 标记）


匹配规则的能力完全拦截，无规则透传


---

# 4. 设备库完整支持


## search


按名称/ID 搜索设备库。


## install


下载能力包到 packages/。


## GUI 硬件库检索


添加设备勾选"使用硬件库检索"：


用指纹查设备库 → 命中则自动装包 + 设 package


## CLI library-search


命令行搜索设备库。


---

# 5. 新增/修改文件


## 新增


mapping/transform.py - Transform Layer


config/transforms.json - 变换规则配置


## 修改


mapping/mapper.py - 映射表重构（一对多）


core/processed_channel.py - transformed 标记


main.py - TransformLayer 接入


tools/cnx_cli.py - library-search


tools/cnx_gui.py - 追加映射 + 硬件库检索


tools/config_io.py - mapping_desc 支持 list


devices/device_library.py - search/install


---

# 6. 设计决策


## 6.1 映射合并策略


多对一：最后更新优先。


## 6.2 Transform 拦截


匹配规则的能力完全拦截（不输出原始值），

由变换规则决定输出什么。


---

# 7. 当前状态总结


版本：

V1.4.0


状态：


映射表重构完成（一对多/多对一）

Transform Layer 完成

设备库完整支持完成


下一里程碑：


V1.5.0


更多输出设备（DS4/方向盘/飞行摇杆）

ANT+ 骑行台

高级逻辑表（长按时长/双击/组合键）

GUI 增强（实时输入显示/录制映射）
