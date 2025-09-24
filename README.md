# QMHABridge

一个简单的 Python 程序，通过 ZMQ 订阅按键事件，并自动控制 Home Assistant 中的灯光。

# 按键消息来自
1. qmdev 7.1
2. qmdevsimconnect 5.1

## 功能

- 订阅 ZMQ 消息队列中的按键事件
- 解析特定的按键事件（奎克质造设备id=9, key=0x13）
- 根据按键状态（按下/释放）控制 Home Assistant 灯光
- 支持优雅退出和错误处理

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
HA_BASE_URL=http://homeassistant.local:8123
HA_TOKEN=你的长效访问令牌
HA_LIGHT_ENTITY_ID=light.living_room
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
- 消息 ID：`0x07324D6E`（ZMQQ_KEYEVENT_ID）
- 负载结构：`qid`（4字节）+ `key`（4字节）+ `isrelease`（4字节）
- 当前只处理 `qid=9` 且 `key=0x13` 的事件

## 配置说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `HA_BASE_URL` | Home Assistant 地址 | `http://127.0.0.1:8123` |
| `HA_TOKEN` | HA 访问令牌 | 从 HA 前端获取 |
| `HA_LIGHT_ENTITY_ID` | 灯光实体 ID | `light.bedroom` |
| `ZMQ_SUB_ENDPOINT` | ZMQ 订阅端点 | `tcp://127.0.0.1:5556` |

## 技术栈

- **Python 3.10+**
- **PyZMQ**：ZeroMQ Python 绑定
- **Requests**：HTTP 客户端
- **python-dotenv**：环境变量管理

## 退出程序

使用 `Ctrl+C` 优雅退出，程序会自动清理 ZMQ 资源。


