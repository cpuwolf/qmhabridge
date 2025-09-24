# QMHABridge

一个智能的 Python 程序，通过 ZMQ 订阅按键事件，并自动控制 Home Assistant 中的智能设备。

## 概述

QMHABridge 是一个桥接程序，用于连接奎克质造（QuickmadeSim）设备的按键事件与 Home Assistant 智能家居系统。程序监听 ZMQ 消息队列中的按键事件，并根据预定义的按键映射自动控制相应的智能设备。

### 支持的设备
- **按键消息来源**：
  - qmdev 7.1 及以上版本
  - qmdevsimconnect 5.1 及以上版本

## 功能特性

- 🔌 **ZMQ 消息订阅**：实时监听按键事件消息队列
- 🏠 **智能设备控制**：支持灯光和空调设备的自动控制
- 🎯 **精确按键映射**：支持多个按键事件（灯光控制、空调控制）
- 🛡️ **错误处理**：完善的异常处理和日志记录
- 🔄 **优雅退出**：支持信号处理和资源清理
- ⚙️ **灵活配置**：通过环境变量进行配置管理

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

1. qmdev 7.1及以上版本
2. qmdevsimconnect 5.1及以上版本

### 2. 配置环境变量

创建 `.env` 文件并配置以下参数：

```env
# Home Assistant 配置
HA_BASE_URL=http://homeassistant.local:8123
HA_TOKEN=你的长效访问令牌

# 智能设备实体 ID
HA_LIGHT_ENTITY_ID=light.living_room
HA_AC_ENTITY_ID=climate.living_room_ac

# ZMQ 订阅配置
ZMQ_SUB_ENDPOINT=tcp://127.0.0.1:5556
```

**获取 Home Assistant 令牌：**
1. 登录 Home Assistant 前端
2. 点击用户资料 → 创建长效访问令牌
3. 复制生成的令牌到 `.env` 文件

### 3. 运行程序

```bash
python -m src.main
```

## 工作原理

1. **ZMQ 订阅**：程序作为 ZMQ SUB 客户端连接到指定的端点
2. **消息解析**：接收并解析特定格式的按键事件消息
3. **灯光控制**：根据按键状态调用 Home Assistant REST API
   - 按键释放时：打开灯光
   - 按键按下时：关闭灯光

## 消息格式

程序接收的 ZMQ 消息格式：
- **消息 ID**：`0x07324D6E`（ZMQQ_KEYEVENT_ID）
- **负载结构**：`qid`（4字节）+ `key`（4字节）+ `isrelease`（4字节）
- **字节序**：小端序（little-endian）

## 按键映射

程序支持以下按键事件映射：

| 设备 ID | 按键码 | 功能 | 设备类型 | 操作 |
|---------|--------|------|----------|------|
| `9` | `0x13` | DOME LT | 灯光 | 按键释放→开灯，按键按下→关灯 |
| `9` | `0x22` | PACK 1 | 空调 | 按键释放→制冷模式，按键按下→关闭空调 |

### 按键状态说明
- `isrelease = 1`：按键释放（松开）
- `isrelease = 0`：按键按下

## 配置说明

| 参数 | 说明 | 示例 | 必需 |
|------|------|------|------|
| `HA_BASE_URL` | Home Assistant 服务器地址 | `http://127.0.0.1:8123` | ✅ |
| `HA_TOKEN` | HA 长效访问令牌 | 从 HA 前端获取 | ✅ |
| `HA_LIGHT_ENTITY_ID` | 灯光设备实体 ID | `light.bedroom` | ✅ |
| `HA_AC_ENTITY_ID` | 空调设备实体 ID | `climate.living_room_ac` | ✅ |
| `ZMQ_SUB_ENDPOINT` | ZMQ 订阅端点 | `tcp://127.0.0.1:5556` | ✅ |

## 技术栈

- **Python 3.10+**
- **PyZMQ**：ZeroMQ Python 绑定
- **Requests**：HTTP 客户端
- **python-dotenv**：环境变量管理


## 故障排除

### 常见问题

**1. 程序无法连接到 ZMQ**
```
检查 ZMQ_SUB_ENDPOINT 配置是否正确
确认 qmdev 或 qmdevsimconnect 服务正在运行
```

**2. Home Assistant 设备控制失败**
```
检查 HA_BASE_URL 和 HA_TOKEN 是否正确
确认设备实体 ID 在 HA 中存在
查看程序日志获取详细错误信息
```

**3. 按键事件未被处理**
```
确认按键映射表中的设备 ID 和按键码
检查 ZMQ 消息格式是否符合预期
```

## 退出程序

使用 `Ctrl+C` 优雅退出，程序会自动清理 ZMQ 资源。


