from __future__ import annotations

import logging
import signal
import sys
import time
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


def create_zmq_connection(settings) -> tuple[zmq.Context, zmq.Socket]:
    """创建ZMQ连接"""
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(settings.zmq_sub_endpoint)
    socket.setsockopt_string(zmq.SUBSCRIBE, "")
    return context, socket


def close_zmq_connection(context: zmq.Context, socket: zmq.Socket) -> None:
    """关闭ZMQ连接"""
    try:
        socket.close(0)
    finally:
        context.term()
        
def process_pack_message(payload_bytes: list[bytes], ha: HomeAssistantClient, settings) -> None:
    # 按照 C 结构体解码 payload_bytes
    onoff = False
    if len(payload_bytes) < 1:
        logging.warning("PackEventData 长度不足 1 字节，忽略。len=%d", len(payload_bytes))
        return
    try:
        onoff = struct.unpack('?', payload_bytes)[0]
        payload_preview = f"pack onoff={bool(onoff)}"
        logging.info("收到 PackEvent，内容=%s", payload_preview)
    except Exception as ex:
        payload_preview = payload_bytes.hex()
        logging.warning("解码 PackEventData 失败: %s", ex)
        return

    # 触发 HA 开灯
    try:
        if onoff:
            ha.turn_on_ac(settings.ha_ac_entity_id)
            logging.info("已请求 HA 打开空调：%s", settings.ha_ac_entity_id)
        else:
            ha.turn_off_ac(settings.ha_ac_entity_id)
            logging.info("已请求 HA 关闭空调：%s", settings.ha_ac_entity_id)
    except Exception as ex:
        logging.exception("调用 HA 失败: %s", ex)

def process_message(frames: list[bytes], ha: HomeAssistantClient, settings) -> None:
    """处理接收到的消息"""
    if not frames:
        return

    header_buf = frames[0]
    if len(header_buf) < 8:
        logging.warning("收到的首帧长度不足 8 字节，忽略。len=%d", len(header_buf))
        return

    msg_id, payload_len = struct.unpack('<ii', header_buf[:8])
    
    ZMQQHeartBeat_ID = 0x07324d6d
    ZMQQ_KEYEVENT_ID = 0x07324D6E
    ZMQQ_PACKEVENT_ID = 0x07324D6F
    
    if msg_id == ZMQQHeartBeat_ID:
        logging.debug("收到心跳")
        return
    elif msg_id == ZMQQ_PACKEVENT_ID:
        logging.debug("空调消息 ID: 0x%08X", msg_id)
    elif msg_id != ZMQQ_KEYEVENT_ID:
        logging.warning("忽略未知消息 ID: 0x%08X", msg_id)
        return

    # 拼接 payload（可能部分在首帧 8 字节之后，剩余在后续帧）
    remaining = header_buf[8:]
    if len(remaining) >= payload_len:
        payload_bytes = remaining[:payload_len]
    else:
        concat_rest = remaining + b''.join(frames[1:])
        if len(concat_rest) < payload_len:
            logging.warning("负载长度不足，期望=%d 实际=%d，忽略。", payload_len, len(concat_rest))
            return
        payload_bytes = concat_rest[:payload_len]
    
    if msg_id == ZMQQ_PACKEVENT_ID:
        process_pack_message(payload_bytes, ha, settings)
        return

    # 按照 C 结构体解码 payload_bytes
    qid = 0
    key = 0
    isrelease = False
    if len(payload_bytes) < 12:
        logging.warning("KeyEventData 长度不足 12 字节，忽略。len=%d", len(payload_bytes))
        return
    try:
        qid, key, isrelease = struct.unpack('<iii', payload_bytes[:12])
        payload_preview = f"qid=0x{qid:02X}, key=0x{key:03X}, isrelease={bool(isrelease)}"
        logging.info("收到 KeyEvent，长度=%d，内容=%s", payload_len, payload_preview)
    except Exception as ex:
        payload_preview = payload_bytes.hex()
        logging.warning("解码 KeyEventData 失败: %s", ex)
        return

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
            return
            if isrelease:
                ha.turn_on_ac(settings.ha_ac_entity_id)
                logging.info("已请求 HA 打开空调：%s", settings.ha_ac_entity_id)
            else:
                ha.turn_off_ac(settings.ha_ac_entity_id)
                logging.info("已请求 HA 关闭空调：%s", settings.ha_ac_entity_id)
    except Exception as ex:
        logging.exception("调用 HA 失败: %s", ex)


def main() -> int:
    configure_logging()
    settings = load_settings()

    logging.info("启动 ZMQ 订阅：endpoint=%s", settings.zmq_sub_endpoint)

    ha = HomeAssistantClient(settings.ha_base_url, settings.ha_token)

    interrupted: bool = False

    def handle_sigint(signum, frame):  # type: ignore[no-redef]
        nonlocal interrupted
        interrupted = True
        logging.info("收到中断信号，准备退出...")

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    # 心跳检测相关变量
    last_heartbeat_time = time.time()
    heartbeat_timeout = 6.0  # 6秒超时
    context = None
    socket = None

    try:
        while not interrupted:
            # 创建或重新创建ZMQ连接
            if context is None or socket is None:
                if context is not None:
                    close_zmq_connection(context, socket)
                logging.info("创建ZMQ连接...")
                context, socket = create_zmq_connection(settings)
                #last_heartbeat_time = time.time()  # 重置心跳时间

            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)

            poll_timeout = 1000  # 转换为毫秒

            events = dict(poller.poll(timeout=poll_timeout))
            
            if socket in events and events[socket] == zmq.POLLIN:
                try:
                    # 收集同一条消息的所有帧
                    frames = [socket.recv()]
                    while socket.getsockopt(zmq.RCVMORE):
                        frames.append(socket.recv())

                    # 检查是否是心跳消息
                    if frames and len(frames[0]) >= 8:
                        msg_id, _ = struct.unpack('<ii', frames[0][:8])
                        ZMQQHeartBeat_ID = 0x07324d6d
                        if msg_id == ZMQQHeartBeat_ID:
                            last_heartbeat_time = time.time()
                            logging.debug("收到心跳，重置计时器")
                            continue

                    # 处理其他消息
                    process_message(frames, ha, settings)
                    
                except Exception as ex:
                    logging.exception("接收消息失败: %s", ex)
                    # 发生错误时重新创建连接
                    close_zmq_connection(context, socket)
                    context = None
                    socket = None
                    continue
            else:
                # 检查心跳超时
                if time.time() - last_heartbeat_time > heartbeat_timeout:
                    logging.warning("心跳超时！超过%.1f秒未收到心跳，重新建立ZMQ连接", heartbeat_timeout)
                    close_zmq_connection(context, socket)
                    context = None
                    socket = None
                    last_heartbeat_time = time.time()

    finally:
        if context is not None and socket is not None:
            close_zmq_connection(context, socket)
        logging.info("已关闭 ZMQ 资源。")

    return 0


if __name__ == "__main__":
    sys.exit(main())


