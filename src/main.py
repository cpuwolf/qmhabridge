from __future__ import annotations

import logging
import signal
import sys
from typing import Optional

import zmq
import struct

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

    logging.info("启动 ZMQ 订阅：endpoint=%s", settings.zmq_sub_endpoint)

    ha = HomeAssistantClient(settings.ha_base_url, settings.ha_token)

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(settings.zmq_sub_endpoint)
    socket.setsockopt_string(zmq.SUBSCRIBE, "")

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

        ZMQQ_KEYEVENT_ID = 0x07324D6E

        while not interrupted:
            events = dict(poller.poll(timeout=1000))  # 1s 轮询，便于优雅退出
            if socket in events and events[socket] == zmq.POLLIN:
                try:
                    # 收集同一条消息的所有帧
                    frames = [socket.recv()]
                    while socket.getsockopt(zmq.RCVMORE):
                        frames.append(socket.recv())

                    if not frames:
                        continue

                    header_buf = frames[0]
                    if len(header_buf) < 8:
                        logging.warning("收到的首帧长度不足 8 字节，忽略。len=%d", len(header_buf))
                        continue

                    msg_id, payload_len = struct.unpack('<ii', header_buf[:8])
                    if msg_id != ZMQQ_KEYEVENT_ID:
                        logging.debug("忽略未知消息 ID: 0x%08X", msg_id)
                        continue

                    # 拼接 payload（可能部分在首帧 8 字节之后，剩余在后续帧）
                    remaining = header_buf[8:]
                    if len(remaining) >= payload_len:
                        payload_bytes = remaining[:payload_len]
                    else:
                        concat_rest = remaining + b''.join(frames[1:])
                        if len(concat_rest) < payload_len:
                            logging.warning("负载长度不足，期望=%d 实际=%d，忽略。", payload_len, len(concat_rest))
                            continue
                        payload_bytes = concat_rest[:payload_len]

                    # 按照 C 结构体解码 payload_bytes
                    qid = 0
                    key = 0
                    isrelease = False
                    if len(payload_bytes) < 9:
                        logging.warning("KeyEventData 长度不足 9 字节，忽略。len=%d", len(payload_bytes))
                        continue
                    try:
                        payload_preview = f"qid=0x{qid:02X}, key=0x{key:03X}, isrelease={bool(isrelease)}"
                        logging.info("收到 KeyEvent，长度=%d，内容=%s", payload_len, payload_preview)
                        
                        qid, key, isrelease = struct.unpack('<iii', payload_bytes[:12])
                    except Exception as ex:
                        payload_preview = payload_bytes.hex()
                        logging.warning("解码 KeyEventData 失败: %s", ex)
                    

                    # 触发 HA 开灯
                    try:
                        if qid == 9 and key == 0x13: #DOME LT
                            if isrelease:
                                ha.turn_on_light(settings.ha_light_entity_id)
                                logging.info("已请求 HA 打开灯光：%s", settings.ha_light_entity_id)
                            else:
                                ha.turn_off_light(settings.ha_light_entity_id)
                                logging.info("已请求 HA 关闭灯光：%s", settings.ha_light_entity_id)
                        if qid == 9 and key == 0x22: #PACK 1
                            if isrelease:
                                ha.turn_on_ac(settings.ha_ac_entity_id)
                                logging.info("已请求 HA 打开空调：%s", settings.ha_ac_entity_id)
                            else:
                                ha.turn_off_ac(settings.ha_ac_entity_id)
                                logging.info("已请求 HA 关闭空调：%s", settings.ha_ac_entity_id)
                    except Exception as ex:
                        logging.exception("调用 HA 失败: %s", ex)
                except Exception as ex:
                    logging.exception("接收消息失败: %s", ex)

    finally:
        try:
            socket.close(0)
        finally:
            context.term()
        logging.info("已关闭 ZMQ 资源。")

    return 0


if __name__ == "__main__":
    sys.exit(main())


