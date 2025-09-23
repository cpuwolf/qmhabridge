from __future__ import annotations

import logging
import signal
import sys
from typing import Optional

import zmq

# 兼容作为模块运行与脚本直接运行两种方式
try:
    from .config import load_settings
    from .ha_client import HomeAssistantClient
except ImportError:  # 当以 `python src/main.py` 运行时生效
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import load_settings  # type: ignore
    from ha_client import HomeAssistantClient  # type: ignore


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main() -> int:
    configure_logging()
    settings = load_settings()

    logging.info("启动 ZMQ 订阅：endpoint=%s, topic=%s", settings.zmq_sub_endpoint, settings.zmq_topic)

    ha = HomeAssistantClient(settings.ha_base_url, settings.ha_token)

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(settings.zmq_sub_endpoint)
    socket.setsockopt_string(zmq.SUBSCRIBE, "")#settings.zmq_topic)

    interrupted: bool = False

    def handle_sigint(signum, frame):  # type: ignore[no-redef]
        nonlocal interrupted
        interrupted = True
        logging.info("收到中断信号，准备退出...")

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    try:
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        while not interrupted:
            events = dict(poller.poll(timeout=1000))  # 1s 轮询，便于优雅退出
            if socket in events and events[socket] == zmq.POLLIN:
                try:
                    topic = socket.recv()
                    payload = socket.recv()
                except Exception as ex:
                    logging.exception("接收消息失败: %s", ex)
                    continue

                logging.info("收到消息：topic=%s payload=%s", topic, payload)

                if topic == settings.zmq_topic:
                    try:
                        ha.turn_on_light(settings.ha_light_entity_id)
                        logging.info("已请求 HA 打开灯光：%s", settings.ha_light_entity_id)
                    except Exception as ex:
                        logging.exception("调用 HA 失败: %s", ex)

    finally:
        try:
            socket.close(0)
        finally:
            context.term()
        logging.info("已关闭 ZMQ 资源。")

    return 0


if __name__ == "__main__":
    sys.exit(main())


