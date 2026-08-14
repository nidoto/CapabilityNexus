# CapabilityNexus

## 中文说明

### 产品核心

```text
任意设备 -> 任意功能 -> CapabilityNexus -> 任意功能 -> 任意设备
```

CapabilityNexus 是现实输入能力的抽象、处理、映射和路由平台。

设备提供数据，应用程序使用功能，CapabilityNexus 负责连接两者之间的能力关系。

### 产品定位

CapabilityNexus 是开源的输入输出中间层，不是 Xbox 模拟器、游戏 Mod，也不替代硬件厂商驱动。

### 核心能力

- 多种现实设备接入和组合
- 能力注册与硬件解耦
- 输入处理、映射和逻辑变换
- XInput 兼容控制器、键盘、鼠标等标准兼容输出
- 双向反馈和震动请求捕获
- ESP32 闭源算法与开源客户端分离
- 运行时设备、输入和输出监控

### 快速开始

1. 安装 Python 3.11 或更新版本。
2. 安装必要的运行时依赖和驱动。
3. 双击 `start.cmd`。
4. 从设备树右键菜单添加输入设备。
5. 双击能力节点配置映射。
6. 在应用程序中使用 XInput 兼容控制器输出。

### 文档

- [产品说明](docs/PRODUCT_OVERVIEW.md)
- [安装指南](docs/INSTALLATION.md)
- [系统架构](docs/ARCHITECTURE.md)
- [开发日志](docs/DEVELOPMENT_LOG_V1.7.0.md)
- [第三方声明](THIRD_PARTY_NOTICES.md)

## English

### Product Core

```text
Any Device -> Any Capability -> CapabilityNexus -> Any Function -> Any Device
```

CapabilityNexus is an open platform for abstracting, processing, mapping and
routing real-world input capabilities.

Devices provide data, applications consume functions, and CapabilityNexus
connects the capability relationship between them.

### Product Positioning

CapabilityNexus is open-source input/output middleware. It is not an Xbox
emulator, a game modification or a replacement for vendor hardware drivers.

### Core Capabilities

- Connect and combine multiple physical input sources
- Decouple capabilities from hardware brands
- Process, map and transform input capabilities
- Provide XInput-compatible, keyboard and mouse outputs
- Capture bidirectional feedback and rumble requests
- Keep proprietary ESP32 algorithms inside closed firmware
- Monitor devices, inputs and outputs at runtime

### Quick Start

1. Install Python 3.11 or newer.
2. Install required runtime dependencies and drivers.
3. Double-click `start.cmd`.
4. Add input devices from the device-tree context menu.
5. Double-click capability nodes to configure mappings.
6. Use the XInput-compatible output in the target application.

### Documentation

- [Product Overview](docs/PRODUCT_OVERVIEW.md)
- [Installation](docs/INSTALLATION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Development Log](docs/DEVELOPMENT_LOG_V1.7.0.md)
- [Third-party Notices](THIRD_PARTY_NOTICES.md)
