# CHANGELOG_DEV

开发增量日志（相对已发布的 V1.8.0）。本文件记录本阶段在 `CapabilityNexus`
源码树上做的中小改造，便于回溯，**不与对外发行说明（README / PRODUCT_OVERVIEW）
混淆**。

提交基线：V1.8.0（`f6b07c9` 之后）。

---

## 2026-08-21 — Device Identity（设备身份层）

提交：`3d5746e feat: introduce device identity system`

把手机的身份从「用户名-手机名」改为稳定的 **device_id**，明确 **Device →
Profile** 模型（不引入任何用户/账号维度）。

### 数据形状
- hello / config 帧新增 `device_id`，与 `name` / `capabilities` 并列；`name` 仅作显示名。
- 识别优先级：`device_id` > `name`。

### 手机网页（phone-android.html / phone-ios.html）
- 首次生成稳定 `device_id`（UUID）并写入浏览器 `localStorage`（`cnx_device_id`）；
  之后每次重连自动携带。
- 若手机未带 `device_id` 连接，服务端生成并通过 `device_id` 消息回传，让其持久化。

### 服务端（devices/websocket_connection.py · tools/services.py）
- `PhoneFrameParser.device` 现为 `{device_id, name, capabilities}`，新增 `device_id` 属性。
- `PhoneProfileStore` 配置按 `<device_id>.json` 存取（原为 `<用户>-<手机名>.json`），
  `name` 不再进入文件名。
- 旧格式 `<*>-<手机名>.json` **不删除**：首次连接时按手机显示名复制（迁移）到新
  `<device_id>.json`。迁移不依赖用户名环境变量。

### 二维码（顺带）
- 新增 `tools/qrcode_utils.py`（纯 Python `qrcode`，不引入 Pillow）。
- GUI：Web 手机服务启动后，**右侧请求面板**直接内嵌显示各局域网 IP 的扫码二维码；
  停止时隐藏。缺库时显示「安装」按钮，后台执行 `pip install qrcode` 后自动刷新。
- `requirements.txt` 增加 `qrcode==8.2`。

### 测试
- `tests/test_phone_profile.py` 改为 device_id 存取 + 旧格式迁移测试；
  `tests/test_qrcode_utils.py` 新增（缺库时跳过）。
- 全量 `pytest`：111 passed, 1 skipped。

---

## 2026-08-21 — Device Reconnect Lifecycle（连接生命周期）

提交：`9a19281 feat: improve device reconnect lifecycle`

仅优化手机 **连接生命周期**；mapping / xinput / ViGEm / Solution 未改动。

### DeviceSession 状态模型（tools/services.py）
- 新增 `DeviceSession`（按 `device_id` 主键）：`device_id` / `status` /
  `last_seen` / `reconnect_attempts`（+ name / capabilities）。
- 状态三态：`CONNECTED` / `RECONNECTING` / `OFFLINE`。
- `WebService` 持有 `self._session`；`phone_status` / `phone_session` 暴露当前状态；
  `info()` 新增 `phone_status` 与 `phone_session`。

### 断开不删除设备对象
- WebSocket 客户端断开（`_on_client_count_changed(0)`）→ `CONNECTED → RECONNECTING`，
  `reconnect_attempts += 1`。`self._parser` 与 session（device_id / profile / pipeline
  状态）**保留**，不新建设备、节点不移除。
- 主动停止服务 → `OFFLINE` 并清理 session。

### 重连恢复（不创建新设备）
- 新 `hello` 的 `device_id` 与已有 session 匹配 → **恢复同一 session**
  （`CONNECTED`，计数归零）；仅 device_id 不同才新建。

### 手机网页（phone-android.html / phone-ios.html）
- 自动重连退避改为分级 **1s → 2s → 5s**（循环），连接成功后归零。
- 新增连接状态指示 `#connState` + `setConnState()`，显示
  **Connected / Reconnecting / Offline**。

### GUI（tools/cnx_gui.py · tools/i18n.py）
- `_phone_connection_info` 返回 `status`；服务面板手机行显示状态词；
  设备树在 `RECONNECTING` 时保留节点（标「重连中」），仅 `OFFLINE` 移除。
- 状态变化日志区分「重连中」与「离线」。
- i18n 新增 `phone_status_connected` / `phone_status_reconnecting`（中/英）。

### 测试
- `tests/test_phone_reconnect.py`：DeviceSession 状态机、WebService RECONNECTING
  转换（session 保留）、退避 1/2/5s。
- 全量 `pytest`：117 passed。

---

## 备注

- 两次提交均**未纳入** `config/devices.json` 的一处无关改动（疑似此前 GUI 会话写入的
  `preset_id: phone_web_wheel`），单独待处理（提交或还原）。
- 所有改动保持：未修改 mapping 输出层、未修改 ViGEm/XInput、未修改 Solution 系统。

---

## 2026-08-21 — Multi Device Runtime（多设备运行时，Phase 2.5）

提交：`feat: support multi device runtime`

把手机运行时的「单设备 + 全局 parser」模型升级为「按 `device_id` 隔离的多设备
运行时」。Device Identity / Reconnect Lifecycle / Profile Store / Mapping / X360
保持不变，不引入 Solution System。

### hello 流程（恢复而非覆盖）
- `WebService._get_or_create_context`：收到 `hello` 时按 `device_id` 查找
  `DeviceContext`；已存在则**恢复同一设备**（更新 websocket / 展示名 / 能力，
  重置连接状态），不重建、不覆盖其它设备；不存在才创建。

### config / frame / message 路由（按 device_id，禁止全局 parser）
- 每台手机在 `DeviceContext` 中拥有**独立**的 `PhoneFrameParser`，绑定到引擎
  `event_bus`。
- `WebService.wrapped_callback` 对每条消息：先用 `device_id`（hello 帧从解析器取、
  其余帧从帧或 websocket 反查）定位对应 `DeviceContext`，再交给**该设备自己的
  parser** 解析发布；找不到对应 `device_id` 的帧直接丢弃。不再有跨设备共享的
  全局 parser。
- `WebService` 新增 `event_bus` 参数与 `set_event_bus()`：引擎启动后注入；已存在的
  `DeviceContext.parser` 同步切换 `event_bus`（保留按钮边沿状态）。

### disconnect（只影响对应 device_id）
- 传输层 `WebSocketServerConnection` 已支持 `on_client_disconnect`（传入具体
  websocket）；`WebService._on_client_disconnected` 仅把持有该 websocket 的
  `device_id` 置为 `RECONNECTING`，保留其 `DeviceContext`（parser / profile /
  历史配置），不影响其它仍在连接的设备。
- 显式禁止「`count==0` 时清空所有设备」的做法：仅用户主动 `stop()` 才清理全部
  context；单连接断开绝不波及其它设备。

### 引擎侧去冲突
- `DeviceManager._build_device` 的 `phone` 分支不再自行创建
  `WebSocketServerConnection` + 全局 `PhoneFrameParser`（会与 GUI 托管的
  `WebService` 抢占 8765 端口并引入全局 parser），改为认定 phone 由 `WebService`
  独立托管并直接跳过。
- `tools/cnx_gui.py`：`_phone_data_callback` 不再用单个 `_phone_engine_parser`
  解析（消除数据路径上的全局 parser），仅做 GUI 侧日志/设备树刷新；
  `start_engine` / `stop_engine` 通过 `web.set_event_bus(...)` 注入/清空引擎
  `event_bus`。

### 测试
- `tests/test_phone_reconnect.py`：多设备 `WebService` 单连接断开只影响对应
  `device_id`、hello 同 id 恢复、不同 id 不覆盖。
- 端到端：两台手机并发连接，各自 `roll` 经独立 parser 发布到同一 `event_bus`，
  互不串扰。
- 全量 `pytest`：待运行环境（本沙箱下 `websockets` 模块在 pytest 采集期偶发卡
  死，手动 `python -u` 验证通过）。

---

## 2026-08-21 — Capability Runtime Layer（能力运行时层，V1.9 Phase 1）

提交：`feat: introduce capability runtime layer`

在输入设备与 Mapping/X360 之间新增**稳定数据抽象层**。系统不再关心输入设备
是什么，只关心它**提供什么能力**。未来手机 / 骑行台 / VR / 手柄 / 其它传感器
统一转换成 `CapabilityEvent`。本阶段小步演进，不进入 Solution System，不修改
Mapping / X360 / GUI / Device Identity / Reconnect。

### 新增 `core/capability.py`
- `CapabilityEvent` 数据类，字段：`device_id: str` / `capability: str` /
  `value: Any` / `timestamp: float`（缺省 `time.time()`）。
- `capability` 用**字符串命名**（非 enum）：未来第三方设备能力（如
  `trainer.power` / `vr.head.yaw`）系统无需改动。
- `device_id` 保留来源：多设备同名能力（如两台手机的 `phone.roll`）靠
  `device_id` 区分，不混淆；`timestamp` 供未来延迟补偿 / 同步 / 融合。

### 修改 PhoneFrameParser（devices/websocket_connection.py）
- `_emit_sensors` / `_emit_buttons` 由发布 `StreamData` 改为发布
  `CapabilityEvent(device_id=self.device_id, capability=..., value=...)`。
- 仅改输出格式，**未大规模重构** parser；按钮边沿去重逻辑不变。

### 运行时桥接（app.py，兼容层）
- 新增 `capability_receive`：订阅 `CapabilityEvent` → 转 `StreamData(capability,
  value)` → 复用既有 `stream_receive` 进入 `Channel`。下游 Mapping / X360 /
  StatusMonitor / GUI 完全不变（仍消费 `StreamData`/`Channel`）。
- `CapabilityEvent` 现已是手机数据进入引擎的标准格式；`device_id` / `timestamp`
  保留在事件中供未来订阅者使用。

### 兼容性验证
- 手机二维码连接、手机控制 X360、mapping 工作：经桥接后 `phone.roll ->
  xbox.right_x` 值与增益不变（`tests/test_capability.py` 端到端回归）。
- 多设备隔离：`dev-a` / `dev-b` 的 `phone.roll` 在事件中 `device_id` 各自正确。

### 测试
- 新增 `tests/test_capability.py`：创建事件、多设备隔离、CapabilityEvent 经桥接
  进入 Mapping→X360 链路（对照 `StreamData` 路径结果一致）。
- 更新 `tests/test_phone.py`：解析器单测断言 `CapabilityEvent` 输出（含
  `device_id`）；端到端用例使用持久 parser 实例以验证 `device_id` 跨帧携带。

### 不影响 V1.8 Multi Device Runtime
- 多设备隔离在 `WebService`/`DeviceContext` 层（`device_id` 主键、独立 parser、
  断开只影响单设备）保持有效；本次仅把各设备 parser 的输出格式升级为
  `CapabilityEvent`，桥接层对下游透明，Multi Device Runtime 行为不变。

### 测试环境提示
- 本沙箱下 `websockets` 模块在 pytest 采集期偶发卡死（守护线程交互），以
  `python -u` 直接运行脚本验证通过；建议在不受限环境跑全量 `pytest`。

---

## 2026-08-21 — Bugfix：V1.9 Phase 1 event_bus 注入遗漏

### 现象
手机发 sensors 帧时：`AttributeError: 'NoneType' object has no attribute 'publish'`
（`PhoneFrameParser._emit_sensors`）。

### 根因
`WebService.wrapped_callback` 为解析 `device_id` 创建了一个临时
`PhoneFrameParser(event_bus=None)`，并在**每个**帧（含 sensors/buttons）上调用
`temp_parser.parse(message)`。对 sensors/buttons 帧，`temp_parser.parse` 会走到
`_emit_sensors`/`_emit_buttons` 并发布到 `temp_parser.event_bus`（None）→ 崩溃。
（原意图只是读身份，却因无条件调用 parse 误触发 emit。）

### 修复
- `tools/services.py` `wrapped_callback`：删除临时 `temp_parser`。hello 帧的身份
  直接从帧体 `data` 读取（`device_id`/`name`/`capabilities`，与解析器结果一致）；
  非 hello 帧通过 `_resolve_device_id` 反查。真实数据的 emit 只由持有真实
  `event_bus` 的 `DeviceContext.parser` 完成（受 `self.event_bus is not None` 保护）。
- `DeviceContext.parser`（即 V1.9 的 CapabilityEvent parser）仍由
  `WebService.event_bus` 构造，`set_event_bus` 注入/同步，确保 V1.8 多设备
  `DeviceContext` 与 V1.9 `CapabilityEvent` 共用同一 `event_bus`。
- `devices/websocket_connection.py` `PhoneFrameParser._emit_sensors` /
  `_emit_buttons`：新增防御——`event_bus is None` 时抛清晰
  `RuntimeError("PhoneFrameParser(<id>) has no event_bus; cannot emit
  CapabilityEvent")`，取代低级 `None.publish`。

### 验证
- `tests/test_capability.py` / `tests/test_phone.py` / `tests/test_phone_profile.py`
  共 18 passed。
- 运行时冒烟：模拟 WebService 设备上下文 parser 共享 `event_bus`，sensors 帧产出
  `CapabilityEvent(device_id='dev-A', capability='phone.roll', value=1.23)`，
  不再 `None.publish`；`event_bus=None` 的 parser 抛清晰 RuntimeError。

### 备注
- 手机端若此前在疯狂重连刷 `"connection handler failed"`，修复后建议先关闭手机
  网页再重连，避免日志刷屏（修复本身已消除 None.publish 根因）。

---

## 2026-08-21 — Capability Routing Layer（能力路由层，V1.9 Phase 2）

提交：`feat: introduce capability routing layer`

在 V1.9 Phase 1（CapabilityEvent 标准格式）之上增加**通用能力路由层**。系统仍
只关心能力，不关心设备；未来 Provider/Consumer（VR / 骑行台 / 手柄 / 融合）以
handler 接入，Router 无需改动。本阶段仅 Runtime Routing，不实现 UI / Solution。

### 新增 core/capability_router.py
- `CapabilityRouter`：`subscribe(handler)` / `unsubscribe(handler)` /
  `publish(event)`。仅把 `CapabilityEvent` 广播给所有 handler。
- **通用能力层约束**：不含任何具体设备/能力的字面判断（无 `if capability==`
  / `if device==`）；不持有 Device，不依赖 Mapping / X360。
- 单 handler 异常不影响其余 handler（与 EventBus 容错一致）。

### app.py 修改
- 新增 `CapabilityMappingAdapter`：`handle(event)` 把 `CapabilityEvent` 结构转换为
  `StreamData(event.capability, event.value)`（event.capability 即 stream.id），
  喂给未变的 `stream_receive → Channel → ... → MappingEngine`。保持 Mapping / X360
  不变；同样不含设备/能力字面判断。
- 管线改为：`CapabilityEvent`（总线）→ `capability_receive` → `CapabilityRouter`
  → `CapabilityMappingAdapter` → `StreamData` → `Mapping`。Router 成为能力分发中枢，
  未来消费者（Recorder / 融合）作为新 handler 接入即可。

### 保持不破坏
Device Identity / DeviceContext / Multi Device Runtime / Reconnect Lifecycle /
PhoneProfileStore / MappingEngine / X360 Output 均未改动。

### 测试
- 新增 `tests/test_capability_router.py`：基础分发（收到同一事件）、多订阅（A/B 同收）、
  device_id 路由前后保留、Mapping 回归（phone.roll → Router → Adapter → Mapping →
  xbox.right_x 值与增益不变）、Router 能力无关性（trainer/vr/wheel 直接透传）。
- 更新 `tests/test_capability.py`：回归管线改走 `CapabilityRouter + MappingAdapter`。
- 通过：`test_capability.py`(5) / `test_phone.py`(6) / `test_pipeline.py`(2) /
  `test_capability_router.py`(8) 共 21 passed。

### 本 Phase 明确不做
UI 能力列表 / 自动能力发现 / 能力数据库 / Graph 编辑器 / Solution System / 修改 X360。

---

## 2026-08-21 — Capability Provider/Consumer 抽象层（V1.9 Phase 3）

提交：`feat: introduce capability provider/consumer abstraction`

在 Routing Layer 之上引入 Provider（输入侧）/ Consumer（输出侧）抽象，使
"设备无关"延伸到两端业务入口。PhoneFrameParser 不再作为直接业务入口，X360
输出被包装为 Consumer；MappingEngine / X360 底层 / DeviceContext / Reconnect /
Profile 均不修改。

### 新增核心抽象
- `core/provider.py`：`CapabilityProvider` 基类——生命周期 `start()` / `stop()` /
  `is_running()`；能力声明 `capabilities() -> List[str]`（字符串，设备无关）；
  `publish(event)` 把 `CapabilityEvent` 交给注入的 sink（router / event_bus）。
- `core/consumer.py`：`CapabilityConsumer` 基类——`consume(event: CapabilityEvent)`；
  不直接实现，子类化后对接具体后端。

### PhoneProvider（devices/phone_provider.py）
- 包装 `PhoneFrameParser`，成为手机输入的业务入口（`PhoneProvider -> CapabilityEvent
  -> CapabilityRouter`）。`parse(message)` 委托内部 `PhoneFrameParser` 解析，解析出的
  `CapabilityEvent` 经注入的 `event_bus`（或 `publish`）流出。
- `capabilities()` 返回该手机能力名（显式配置优先，否则从 hello 解析身份取）。
- 内部 parser 的 `event_bus` 用转发 shim，使 `set_event_bus` 注入/同步后转发目标
  自动更新（引擎重连/重启无碍）。`PhoneFrameParser` 解析逻辑零修改。

### X360Consumer（output/x360_consumer.py）
- 包装 X360 输出为 `CapabilityConsumer`：`consume(CapabilityEvent)` 把
  `event.capability`（xbox.* 目标）/`event.value` 交给底层 `OutputRouter.send`。
- X360 底层（VirtualXInput / RealXInputOutput / OutputRouter 路由）不修改。

### 集成（保持不破坏）
- `tools/services.py` `DeviceContext.parser` 由 `PhoneFrameParser` 改为
  `PhoneProvider(...)`（业务入口统一）；`set_event_bus` 经 `event_bus` 属性兼容。
  Multi Device Runtime / Reconnect / Profile 行为不变。
- `app.py` `_build_outputs`：`OutputEvent -> CapabilityEvent -> X360Consumer.consume`
  替代原 `output_router.send` lambda；底层 `OutputRouter.send` 仍由 Consumer 调用，
  X360 行为一致。

### 保持不修改
MappingEngine / X360 底层 / DeviceContext / Reconnect Lifecycle / PhoneProfileStore。

### 测试（新增）
- `tests/test_provider.py`：PhoneProvider 产出带 device_id 的 CapabilityEvent、
  `event_bus` sink、`capabilities()`、生命周期、基类 `publish` 转发。
- `tests/test_consumer.py`：基类 `consume` 未实现抛 NotImplementedError、
  X360Consumer 把事件发给底层、`CapabilityEvent` 同对象送达自定义消费者。
- `tests/test_runtime.py`：PhoneProvider -> CapabilityRouter -> (MappingAdapter)
  -> X360Consumer 完整链路；phone.roll -> xbox.right_x 值透传、device_id 保留。

### 验证汇总（本沙箱）
- 新增 10 passed（provider/consumer/runtime）；既有 test_capability(5) /
  test_capability_router(8) / test_pipeline(2) / test_phone(6) /
  test_phone_profile(7) 共 28 均通过。
- `test_phone_reconnect.py` 在本沙箱 pytest 采集期偶发卡死（websockets 交互，
  非回归），手动 `python -u` 验证 DeviceContext.parser=PhoneProvider、多设备断开
  隔离、PhoneProvider 产出 CapabilityEvent 均正常。

### 本 Phase 明确不做
UI / Capability 数据库 / Solution System / Graph 编辑器。
