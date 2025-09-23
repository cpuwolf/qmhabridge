from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    ha_base_url: str
    ha_token: str
    ha_light_entity_id: str
    zmq_sub_endpoint: str
    zmq_topic: str


def load_settings() -> Settings:
    """Load settings from environment variables and .env file.

    Raises:
        ValueError: If any required variable is missing.
    """
    load_dotenv()

    ha_base_url = os.getenv("HA_BASE_URL")
    ha_token = os.getenv("HA_TOKEN")
    ha_light_entity_id = os.getenv("HA_LIGHT_ENTITY_ID")
    zmq_sub_endpoint = os.getenv("ZMQ_SUB_ENDPOINT")
    zmq_topic = os.getenv("ZMQ_TOPIC", "aircraftinfo")

    missing: list[str] = []
    if not ha_base_url:
        missing.append("HA_BASE_URL")
    if not ha_token:
        missing.append("HA_TOKEN")
    if not ha_light_entity_id:
        missing.append("HA_LIGHT_ENTITY_ID")
    if not zmq_sub_endpoint:
        missing.append("ZMQ_SUB_ENDPOINT")
    if not zmq_topic:
        missing.append("ZMQ_TOPIC")

    if missing:
        raise ValueError(
            "Missing required environment variables: " + ", ".join(missing)
        )
        
    print(zmq_topic)
    print(type(zmq_topic))

    return Settings(
        ha_base_url=ha_base_url,
        ha_token=ha_token,
        ha_light_entity_id=ha_light_entity_id,
        zmq_sub_endpoint=zmq_sub_endpoint,
        zmq_topic=str(zmq_topic),
    )


