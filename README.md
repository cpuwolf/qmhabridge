## 项目简介

使用 Python 作为 ZMQ SUB 角色订阅“按键事件”，在收到消息后通过本地 Home Assistant (HA) 的 REST API 打开指定灯光。

## 运行环境

- Python 3.10+
- 操作系统：Windows 10/11（其他平台也可）

## 安装与运行

1) 克隆或下载本项目源码。

2) 创建并激活虚拟环境（Windows CMD）：

```bat
python -m venv .venv
.venv\\Scripts\\activate
```

3) 安装依赖：

```bat
pip install -r requirements.txt
```

4) 配置环境变量：复制 `.env.example` 为 `.env`，并填写实际参数。

```txt
HA_BASE_URL=http://homeassistant.local:8123
HA_TOKEN=你的长效访问令牌
HA_LIGHT_ENTITY_ID=light.living_room
ZMQ_SUB_ENDPOINT=tcp://127.0.0.1:5556
ZMQ_TOPIC=key_event
```

获取 HA 长效访问令牌：登录 HA 前端 → 用户资料 → 创建长效访问令牌。

5) 运行：

```bat
python -m src.main
```

## 消息格式

- ZMQ PUB/SUB：本程序作为 SUB。订阅主题由 `ZMQ_TOPIC` 指定。
- 发送方应以多帧消息发送：第一帧为主题（与 `ZMQ_TOPIC` 相同），第二帧为负载字符串（例如 `pressed`）。
- 本程序在接收到任意负载内容时，会调用 HA 打开灯光；如需基于负载进一步判断，可在 `src/main.py` 中调整逻辑。

## 配置项说明

- `HA_BASE_URL`：Home Assistant 基础地址，如 `http://127.0.0.1:8123`。
- `HA_TOKEN`：HA 长效令牌，作为 `Authorization: Bearer <token>` 使用。
- `HA_LIGHT_ENTITY_ID`：要控制的灯光实体 ID，如 `light.bedroom`。
- `ZMQ_SUB_ENDPOINT`：ZMQ 订阅端点，如 `tcp://127.0.0.1:5556`。
- `ZMQ_TOPIC`：订阅主题过滤，如 `key_event`。

## 日志与退出

- 默认日志等级为 INFO，可在 `src/main.py` 中调整。
- 使用 Ctrl+C 可优雅退出，程序会关闭 ZMQ 资源。

## 依赖许可

依赖以各自许可为准；本项目遵循仓库根目录的 LICENSE。


